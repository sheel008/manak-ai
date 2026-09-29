"""Lightweight ONNX embedding service for MANAK-AI.

Uses the same all-MiniLM-L6-v2 embedding model as the original
SentenceTransformer implementation, but runs inference with ONNX Runtime
to reduce memory usage on low-RAM deployments.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


# backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# backend/models/all-MiniLM-L6-v2/
MODEL_DIR = BACKEND_DIR / "models" / "all-MiniLM-L6-v2"

MODEL_FILE = MODEL_DIR / "model_int8.onnx"
TOKENIZER_FILE = MODEL_DIR / "tokenizer.json"

EMBEDDING_DIM = 384
MAX_LENGTH = 256

_tokenizer = None
_session = None


def get_model():
    """Load the tokenizer and ONNX model once and reuse them."""
    global _tokenizer, _session

    if _tokenizer is None:
        if not TOKENIZER_FILE.exists():
            raise FileNotFoundError(
                f"Tokenizer not found: {TOKENIZER_FILE}"
            )

        _tokenizer = Tokenizer.from_file(str(TOKENIZER_FILE))
        _tokenizer.enable_truncation(max_length=MAX_LENGTH)
        _tokenizer.enable_padding()

    if _session is None:
        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"ONNX model not found: {MODEL_FILE}"
            )

        options = ort.SessionOptions()

        # Keep CPU usage/memory controlled on Render Free.
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        _session = ort.InferenceSession(
            str(MODEL_FILE),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

        print("✓ ONNX embedding model loaded")
        print(f"✓ Model: {MODEL_FILE}")
        print(f"✓ Embedding dimension: {EMBEDDING_DIM}")

    return _tokenizer, _session


def _mean_pool(last_hidden_state, attention_mask):
    """Mean-pool token embeddings while ignoring padding tokens."""
    mask = attention_mask.astype(np.float32)
    expanded_mask = np.expand_dims(mask, axis=-1)

    masked_embeddings = last_hidden_state * expanded_mask
    summed = np.sum(masked_embeddings, axis=1)

    counts = np.clip(
        np.sum(expanded_mask, axis=1),
        a_min=1e-9,
        a_max=None,
    )

    return summed / counts


def _normalize(vectors):
    """L2-normalize vectors to match normalize_embeddings=True."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.clip(norms, a_min=1e-12, a_max=None)

    return vectors / norms


def embed_texts(texts):
    """Embed a list of strings and return normalized float vectors."""
    if not texts:
        return []

    tokenizer, session = get_model()

    encoded = tokenizer.encode_batch(
        [str(text) for text in texts]
    )

    input_ids = np.asarray(
        [item.ids for item in encoded],
        dtype=np.int64,
    )

    attention_mask = np.asarray(
        [item.attention_mask for item in encoded],
        dtype=np.int64,
    )

    token_type_ids = np.asarray(
        [item.type_ids for item in encoded],
        dtype=np.int64,
    )

    # Only provide inputs that the ONNX model actually expects.
    available_inputs = {
        item.name for item in session.get_inputs()
    }

    model_inputs = {}

    if "input_ids" in available_inputs:
        model_inputs["input_ids"] = input_ids

    if "attention_mask" in available_inputs:
        model_inputs["attention_mask"] = attention_mask

    if "token_type_ids" in available_inputs:
        model_inputs["token_type_ids"] = token_type_ids

    outputs = session.run(None, model_inputs)

    last_hidden_state = outputs[0]

    vectors = _mean_pool(
        last_hidden_state,
        attention_mask,
    )

    vectors = _normalize(vectors)

    if vectors.shape[1] != EMBEDDING_DIM:
        raise RuntimeError(
            f"Unexpected embedding dimension: "
            f"{vectors.shape[1]} "
            f"(expected {EMBEDDING_DIM})"
        )

    return vectors.astype(np.float32).tolist()


@lru_cache(maxsize=1024)
def _cached_query(query: str):
    """Cache repeated query embeddings."""
    return tuple(embed_texts([query])[0])


def embed_query(text: str):
    """Embed a single query string."""
    return list(_cached_query(str(text)))
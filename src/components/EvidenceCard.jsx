import React, { useState } from 'react';
import { Quote, ChevronDown, ChevronUp } from 'lucide-react';
import { useLang } from '../context/LangContext';

export default function EvidenceCard({ evidence = [] }) {
  const { t } = useLang();
  const [expanded, setExpanded] = useState(false);

  if (!evidence || evidence.length === 0) return null;

  const item = evidence[0];
  const rawExcerpt = (item.excerpt || '').trim().replace(/^["']|["']$/g, '');
  if (!rawExcerpt) return null;

  const isLong = rawExcerpt.length > 250;
  const displayText = !expanded && isLong ? `${rawExcerpt.slice(0, 250)}...` : rawExcerpt;

  return (
    <div className="mt-3 rounded-lg border border-[#DDD9D0] bg-[#FAFAF8] p-3.5 border-l-4 border-l-[#2F6F5E]">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 text-[#2F6F5E]">
          <Quote size={14} className="rotate-180" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C5A55]">
            {t('chat.evidenceTitle')} {item.standard ? `(${item.standard})` : ''}
          </span>
        </div>
        <span className="text-[10px] text-[#8A8580] bg-white px-1.5 py-0.5 rounded border border-[#DDD9D0]">
          {t('chat.groundTruth')}
        </span>
      </div>

      <blockquote className="text-xs text-[#16294D] italic leading-relaxed font-sans bg-white p-2.5 rounded border border-[#E4E1DA]">
        &ldquo;{displayText}&rdquo;
      </blockquote>

      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-[#2155A3] hover:underline cursor-pointer"
        >
          {expanded ? (
            <>
              <span>{t('chat.showLess')}</span>
              <ChevronUp size={12} />
            </>
          ) : (
            <>
              <span>{t('chat.expandFull')} ({rawExcerpt.length} chars)</span>
              <ChevronDown size={12} />
            </>
          )}
        </button>
      )}
    </div>
  );
}

import React from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, BookmarkCheck, ArrowUpRight, Award, Layers } from 'lucide-react';
import clsx from 'clsx';
import { useLang } from '../context/LangContext';

export default function RecommendationCard({ recommendation, onSave, isSaved = false }) {
  const { t } = useLang();
  if (!recommendation) return null;

  const { is_number, title, confidence = 0, category = 'General', summary, department, sector, is_qco_mandatory, qco_required, why_recommended } = recommendation;
  const isQco = is_qco_mandatory || qco_required;

  // Confidence color badges: 90+ Green, 70-89 Yellow, Below 70 Orange
  const getConfidenceBadge = (score) => {
    if (score >= 90) {
      return {
        label: `${score}% ${t('results.match')}`,
        badgeClass: 'bg-[#E4F2EE] text-[#1F5C4D] border-[#A8D5C9]',
        barClass: 'bg-[#2F6F5E]',
      };
    }
    if (score >= 70) {
      return {
        label: `${score}% ${t('results.match')}`,
        badgeClass: 'bg-[#FDF2DC] text-[#8A5E0E] border-[#EDD087]',
        barClass: 'bg-[#B8862B]',
      };
    }
    return {
      label: `${score}% ${t('results.match')}`,
      badgeClass: 'bg-[#FFF0E6] text-[#B85D19] border-[#FAD2B8]',
      barClass: 'bg-[#B85D19]',
    };
  };

  const conf = getConfidenceBadge(confidence);

  return (
    <div className="mt-3 rounded-lg border border-[#DDD9D0] bg-white p-4 shadow-sm hover:border-[#16294D] transition-colors">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-xs font-bold bg-[#16294D] text-white px-2.5 py-1 rounded shadow-2xs">
            {is_number}
          </span>
          {department && (
            <span className="text-[10px] font-semibold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] px-2 py-0.5 rounded">
              {department}
            </span>
          )}
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#4B4845] bg-[#F4F3EF] border border-[#DDD9D0] px-2 py-0.5 rounded">
            <Layers size={11} className="opacity-70" />
            {category}
          </span>
          {isQco && (
            <span className="text-[10px] font-bold text-[#8C2B22] bg-[#FAEBE9] border border-[#E8AFAA] px-2 py-0.5 rounded">
              QCO Mandatory
            </span>
          )}
        </div>

        <span
          className={clsx(
            'inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded border',
            conf.badgeClass
          )}
        >
          <Award size={12} />
          {conf.label}
        </span>
      </div>

      {/* Confidence progress indicator */}
      <div className="w-full bg-[#EDEBE5] h-1.5 rounded-full overflow-hidden mb-3">
        <div
          className={clsx('h-full transition-all duration-500', conf.barClass)}
          style={{ width: `${Math.min(100, Math.max(5, confidence))}%` }}
        />
      </div>

      {/* Title */}
      <h3 className="text-sm font-bold text-[#16294D] leading-snug mb-1.5">
        {title}
      </h3>

      {/* Summary */}
      {summary && (
        <p className="text-xs text-[#5C5A55] leading-relaxed mb-2.5 line-clamp-3">
          {summary}
        </p>
      )}

      {/* Why Recommended Explainability Note */}
      {why_recommended && (
        <div className="p-2 mb-3 rounded bg-[#FAFAF8] border border-[#DDD9D0] text-[11px] text-[#4B4845]">
          <strong className="text-[#16294D]">Recommendation Basis: </strong>
          {why_recommended}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between gap-2 pt-2.5 border-t border-[#EDEBE5]">
        <button
          type="button"
          onClick={() => onSave && onSave(is_number)}
          className={clsx(
            'inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded border transition-colors cursor-pointer',
            isSaved
              ? 'bg-[#E4F2EE] text-[#1F5C4D] border-[#A8D5C9]'
              : 'bg-white text-[#4B4845] border-[#DDD9D0] hover:bg-[#F4F3EF] hover:text-[#16294D]'
          )}
        >
          {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
          <span>{isSaved ? t('chat.savedToLibrary') : t('chat.saveToLibrary')}</span>
        </button>

        <Link
          to={`/standard/${encodeURIComponent(is_number)}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-white bg-[#16294D] hover:bg-[#1E3761] px-3 py-1.5 rounded shadow-2xs transition-colors"
        >
          <span>{t('chat.viewSpecification')}</span>
          <ArrowUpRight size={13} />
        </Link>
      </div>
    </div>
  );
}

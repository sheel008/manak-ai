import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ExternalLink } from 'lucide-react';
import { useLang } from '../context/LangContext';

export default function RelatedStandardsCard({ standards = [] }) {
  const { t } = useLang();
  if (!standards || standards.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-[#DDD9D0] bg-white p-3.5 shadow-2xs">
      <div className="flex items-center gap-1.5 mb-2.5">
        <BookOpen size={14} className="text-[#16294D]" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C5A55]">
          {t('chat.normativeHeading')}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {standards.map((isNum, idx) => (
          <Link
            key={idx}
            to={`/standard/${encodeURIComponent(isNum)}`}
            className="group flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-[#FAFAF8] border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F0EEE9] transition-all text-left"
          >
            <span className="font-mono text-xs font-semibold text-[#16294D] group-hover:text-[#1E3761]">
              {isNum}
            </span>
            <ExternalLink size={12} className="text-[#8A8580] group-hover:text-[#16294D] flex-shrink-0 transition-transform group-hover:translate-x-0.5" />
          </Link>
        ))}
      </div>
    </div>
  );
}

import React from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';
import { useLang } from '../context/LangContext';

export default function SuggestedQuestions({ questions = [], onSelectQuestion }) {
  const { t } = useLang();
  if (!questions || questions.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-[#DDD9D0]">
      <div className="flex items-center gap-1.5 mb-2">
        <HelpCircle size={13} className="text-[#16294D]" aria-hidden="true" focusable="false" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C5A55]">
          {t('chat.suggestedFollowUp')}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuestion && onSelectQuestion(q)}
            className="inline-flex items-center gap-1.5 text-xs text-[#16294D] bg-[#F4F3EF] hover:bg-[#E4EDF9] hover:text-[#1A4490] border border-[#DDD9D0] hover:border-[#A8C2E8] px-2.5 py-1.5 rounded-full transition-all text-left shadow-2xs group cursor-pointer"
          >
            <span>{q}</span>
            <ArrowRight size={11} className="text-[#8A8580] group-hover:text-[#1A4490] group-hover:translate-x-0.5 transition-transform" aria-hidden="true" focusable="false" />
          </button>
        ))}
      </div>
    </div>
  );
}

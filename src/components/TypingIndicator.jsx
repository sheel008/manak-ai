import React from 'react';
import { Bot, Loader2 } from 'lucide-react';
import { useLang } from '../context/LangContext';

export default function TypingIndicator() {
  const { t } = useLang();
  return (
    <div className="flex max-w-[85%] mr-auto items-start gap-2.5">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-[#2F6F5E] text-white shadow-2xs mt-0.5">
        <Bot size={15} aria-hidden="true" focusable="false" />
      </div>
      <div className="px-4 py-2.5 rounded-lg bg-white border border-[#DDD9D0] text-[#111111] shadow-2xs flex items-center gap-2.5">
        <Loader2 size={14} className="animate-spin text-[#2F6F5E]" aria-hidden="true" focusable="false" />
        <span className="text-xs text-[#4B4845] font-medium">{t('chat.evaluating')}</span>
      </div>
    </div>
  );
}

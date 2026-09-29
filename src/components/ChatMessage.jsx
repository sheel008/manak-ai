import React from 'react';
import { User, Bot, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import RecommendationCard from './RecommendationCard';
import CertificationCard from './CertificationCard';
import EvidenceCard from './EvidenceCard';
import RelatedStandardsCard from './RelatedStandardsCard';
import SuggestedQuestions from './SuggestedQuestions';

export default function ChatMessage({
  message,
  onSelectQuestion,
  onSaveStandard,
  savedStandards = new Set(),
}) {
  if (!message) return null;

  const isUser = message.role === 'user';

  // Basic Markdown-like renderer for structured text
  const renderFormattedContent = (content = '') => {
    if (!content) return null;

    const lines = content.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();

      // Heading 3
      if (trimmed.startsWith('### ')) {
        return (
          <h4 key={idx} className="text-sm font-bold text-[#16294D] mt-3.5 mb-1.5 first:mt-0 pb-1 border-b border-[#EDEBE5]">
            {trimmed.replace(/^###\s*/, '')}
          </h4>
        );
      }
      // Heading 4 / Subheading
      if (trimmed.startsWith('#### ')) {
        return (
          <h5 key={idx} className="text-xs font-bold text-[#16294D] mt-2 mb-1">
            {trimmed.replace(/^####\s*/, '')}
          </h5>
        );
      }
      // Bullet items
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.replace(/^[-*]\s*/, '');
        return (
          <div key={idx} className="flex items-start gap-1.5 ml-2 mb-1 text-[13px] leading-relaxed">
            <span className="text-[#2F6F5E] font-bold">•</span>
            <span>{renderInlineMarkdown(itemText)}</span>
          </div>
        );
      }
      // Numbered items
      if (/^\d+\.\s/.test(trimmed)) {
        const itemText = trimmed.replace(/^\d+\.\s*/, '');
        const match = trimmed.match(/^(\d+)\./);
        const num = match ? match[1] : '•';
        return (
          <div key={idx} className="flex items-start gap-1.5 ml-2 mb-1 text-[13px] leading-relaxed">
            <span className="text-[#16294D] font-bold text-xs">{num}.</span>
            <span>{renderInlineMarkdown(itemText)}</span>
          </div>
        );
      }
      // Blockquotes
      if (trimmed.startsWith('> ')) {
        const quoteText = trimmed.replace(/^>\s*/, '');
        return (
          <blockquote key={idx} className="my-2 pl-3 border-l-2 border-[#2F6F5E] text-xs italic text-[#4B4845] bg-[#FAFAF8] py-1">
            {quoteText}
          </blockquote>
        );
      }
      // Empty line spacing
      if (!trimmed) {
        return <div key={idx} className="h-1.5" />;
      }
      // Regular paragraph
      return (
        <p key={idx} className="mb-1.5 text-[13px] leading-relaxed last:mb-0">
          {renderInlineMarkdown(line)}
        </p>
      );
    });
  };

  const renderInlineMarkdown = (text = '') => {
    // Splits **bold** and `code`
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-[#16294D]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="font-mono text-xs bg-[#EDEBE5] px-1 py-0.5 rounded text-[#16294D]">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  if (isUser) {
    return (
      <div className="flex max-w-[85%] ml-auto items-start gap-2.5">
        <div className="px-4 py-2.5 rounded-lg bg-[#16294D] text-white shadow-2xs">
          <p className="text-[13px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center bg-[#16294D] text-white shadow-2xs mt-0.5">
          <User size={14} />
        </div>
      </div>
    );
  }

  // Assistant Message
  const hasRecommendations = message.recommendations && message.recommendations.length > 0;
  const topRec = hasRecommendations ? message.recommendations[0] : null;
  const isSaved = topRec ? savedStandards.has(topRec.is_number) : false;

  return (
    <div className="flex max-w-[95%] md:max-w-[90%] mr-auto items-start gap-2.5">
      <div className="flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center bg-[#2F6F5E] text-white shadow-2xs mt-0.5">
        <Bot size={15} />
      </div>

      <div className="flex-1 bg-white border border-[#DDD9D0] text-[#111111] rounded-lg p-4 md:p-5 shadow-sm">
        {/* Error notice if present */}
        {message.error && (
          <div className="flex items-center gap-2 mb-3 p-2.5 rounded-md bg-[#FAEBE9] border border-[#E8AFAA] text-[#8C2B22] text-xs">
            <AlertTriangle size={14} className="flex-shrink-0" />
            <span>{message.error}</span>
          </div>
        )}


        {/* Formatted Grounded Text Response */}
        <div className="prose prose-sm max-w-none text-[#1A1A1A]">
          {renderFormattedContent(message.content || message.answer)}
        </div>

        {/* Recommendation Card */}
        {topRec && (
          <RecommendationCard
            recommendation={topRec}
            onSave={onSaveStandard}
            isSaved={isSaved}
          />
        )}

        {/* Certification Status Card */}
        {message.qco && (
          <CertificationCard qco={message.qco} />
        )}

        {/* Source Evidence Card */}
        {message.evidence && message.evidence.length > 0 && (
          <EvidenceCard evidence={message.evidence} />
        )}

        {/* Related Standards Card */}
        {message.related_standards && message.related_standards.length > 0 && (
          <RelatedStandardsCard standards={message.related_standards} />
        )}

        {/* Follow-up Suggested Questions Chips */}
        {message.follow_up && message.follow_up.length > 0 && (
          <SuggestedQuestions
            questions={message.follow_up}
            onSelectQuestion={onSelectQuestion}
          />
        )}
      </div>
    </div>
  );
}

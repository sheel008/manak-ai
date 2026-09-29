import { Calendar, History, Check } from 'lucide-react'
import Badge from './Badge'
import clsx from 'clsx'
import { useLang } from '../context/LangContext'

export default function AmendmentTimeline({
  version = null,
  lastAmended = null,
  amendmentHistory = [],
  className,
}) {
  const { t } = useLang()
  const historyList = Array.isArray(amendmentHistory) ? amendmentHistory : []

  // Sort newest first by parsed date
  const sortedHistory = [...historyList].sort((a, b) => {
    const dateA = a.date ? new Date(a.date).getTime() : 0
    const dateB = b.date ? new Date(b.date).getTime() : 0
    return dateB - dateA
  })

  return (
    <div className={clsx('bg-white rounded-md border border-[#E4E1DA] p-5 shadow-card', className)}>
      {/* Header with Version & Last Amended */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 mb-4 border-b border-[#EDEBE5]">
        <div>
          <p className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider mb-1 flex items-center gap-1.5">
            <History size={13} className="text-[#2155A3]" /> {t('amendments.title')}
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-[#5C5A55]">
              {t('amendments.currentVersion')}: <strong className="text-[#1A1A1A] font-medium">{version || t('amendments.firstEdition')}</strong>
            </span>
            <span className="text-[#DDD9D0]">|</span>
            <span className="text-sm text-[#5C5A55] flex items-center gap-1">
              <Calendar size={13} className="text-[#8A8580]" />
              {t('amendments.lastAmended')}: <strong className="text-[#1A1A1A] font-medium">{lastAmended || t('amendments.noneRecorded')}</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {historyList.length > 0 ? (
            <Badge variant="indigo" size="md">
              {historyList.length} {t('amendments.amendmentsPublished')}
            </Badge>
          ) : (
            <Badge variant="neutral" size="md">
              {t('amendments.baselineEdition')}
            </Badge>
          )}
        </div>
      </div>

      {/* Timeline entries */}
      {sortedHistory.length > 0 ? (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#E4E1DA]">
          {sortedHistory.map((item, idx) => (
            <div key={idx} className="relative">
              <div className="absolute -left-6 top-1 w-4 h-4 rounded-full bg-[#E4EDF9] border-2 border-[#2155A3] flex items-center justify-center">
                <Check size={8} className="text-[#2155A3]" />
              </div>
              <div className="text-xs">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-semibold text-[#16294D]">{item.amendment_number || `${t('amendments.amendmentNum')} ${idx + 1}`}</span>
                  {item.date && (
                    <span className="text-[#8A8580]">({item.date})</span>
                  )}
                </div>
                <p className="text-[#5C5A55] leading-relaxed">{item.description || 'Regulatory clause amendment.'}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-[#8A8580] italic">
          {t('amendments.baselineEdition')}
        </p>
      )}
    </div>
  )
}

import { ShieldCheck, ShieldAlert, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import Badge from './Badge'
import clsx from 'clsx'
import { useLang } from '../context/LangContext'

/**
 * Computes human-readable relative enforcement timeframe aligning with the 30-day dashboard window.
 */
export function getEnforcementTimeline(dateStr, t = (k) => k) {
  if (!dateStr) return null

  // Treat date as YYYY-MM-DD
  const parts = dateStr.split('-').map(Number)
  if (parts.length < 3 || isNaN(parts[0])) return null

  const targetDate = new Date(parts[0], parts[1] - 1, parts[2])
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  const diffTime = targetDate.getTime() - today.getTime()
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24))

  const formattedDate = targetDate.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  if (diffDays < 0) {
    return {
      isEnforced: true,
      isUpcoming30d: false,
      isUrgent: false,
      badgeVariant: 'success',
      badgeLabel: t('certification.activeMandate'),
      headline: t('certification.activelyEnforced'),
      relativeText: `${t('certification.enforcedSince')} ${formattedDate}`,
      formattedDate,
      diffDays,
    }
  } else if (diffDays === 0) {
    return {
      isEnforced: true,
      isUpcoming30d: true,
      isUrgent: true,
      badgeVariant: 'error',
      badgeLabel: t('certification.effectiveToday'),
      headline: t('certification.effectiveImmediately'),
      relativeText: `${t('certification.effectiveImmediately')} (${formattedDate})`,
      formattedDate,
      diffDays: 0,
    }
  } else if (diffDays <= 15) {
    return {
      isEnforced: false,
      isUpcoming30d: true,
      isUrgent: true,
      badgeVariant: 'error',
      badgeLabel: t('certification.urgentDeadline'),
      headline: `${t('certification.mandatoryIn')} ${diffDays} ${diffDays === 1 ? t('certification.day') : t('certification.days')}`,
      relativeText: `${t('certification.deadlineDate')}: ${formattedDate} (${t('certification.mandatoryIn')} ${diffDays} ${diffDays === 1 ? t('certification.day') : t('certification.days')})`,
      formattedDate,
      diffDays,
    }
  } else if (diffDays <= 30) {
    return {
      isEnforced: false,
      isUpcoming30d: true,
      isUrgent: false,
      badgeVariant: 'warning',
      badgeLabel: t('certification.upcoming30d'),
      headline: `${t('certification.mandatoryIn')} ${diffDays} ${t('certification.days')}`,
      relativeText: `${t('certification.deadlineDate')}: ${formattedDate} (${diffDays} ${t('certification.days')})`,
      formattedDate,
      diffDays,
    }
  } else {
    const months = Math.max(1, Math.round(diffDays / 30.4))
    return {
      isEnforced: false,
      isUpcoming30d: false,
      isUrgent: false,
      badgeVariant: 'info',
      badgeLabel: 'Gazette',
      headline: `${t('certification.mandatoryIn')} ~${months} mo`,
      relativeText: `${formattedDate} (~${months} mo)`,
      formattedDate,
      diffDays,
    }
  }
}

export default function CertificationStatus({
  mode = 'standard',
  isQcoMandatory = false,
  enforcementDate = null,
  scheme = null,
  certificationBody = 'Bureau of Indian Standards (BIS)',
  applicableIsNumber = null,
  productName = null,
  aliases = [],
  compact = false,
  className,
}) {
  const { t } = useLang()
  const isMandatory = Boolean(isQcoMandatory)
  const timeline = enforcementDate ? getEnforcementTimeline(enforcementDate, t) : null

  // Mode: "product_rule" (QCO Checker dedicated lookup)
  if (mode === 'product_rule') {
    return (
      <div className={clsx('rounded-md border p-4 bg-white', className, isMandatory ? 'border-[#EDD087] bg-[#FDFCF7]' : 'border-[#E4E1DA]')}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            {isMandatory ? (
              <div className="w-8 h-8 rounded-full bg-[#FDF2DC] flex items-center justify-center text-[#8A5E0E]">
                <ShieldAlert size={18} />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-[#E4F2EE] flex items-center justify-center text-[#1F5C4D]">
                <ShieldCheck size={18} />
              </div>
            )}
            <div>
              <p className="text-xs font-semibold text-[#8A8580] uppercase tracking-wider">
                {t('qco.regulatoryOrder')}
              </p>
              <h4 className="text-base font-bold text-[#1A1A1A]">
                {productName || 'Queried Product'}
              </h4>
            </div>
          </div>
          {isMandatory ? (
            <Badge variant="warning">{t('qco.mandatoryRequired')}</Badge>
          ) : (
            <Badge variant="success">{t('qco.voluntaryNotice')}</Badge>
          )}
        </div>

        <div className="text-xs text-[#5C5A55] leading-relaxed mb-3">
          {isMandatory ? (
            <p>
              {t('qco.mandatoryCovered')}
            </p>
          ) : (
            <p>
              {t('qco.voluntaryCovered')}
            </p>
          )}
        </div>

        {isMandatory && (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-3 border-t border-[#EDEBE5] text-xs">
            {applicableIsNumber && (
              <div>
                <dt className="text-[#8A8580]">{t('qco.applicableStandard')}</dt>
                <dd className="font-mono-bis font-semibold text-[#2155A3]">{applicableIsNumber}</dd>
              </div>
            )}
            {timeline && (
              <div>
                <dt className="text-[#8A8580]">{t('qco.enforcementDate')}</dt>
                <dd className="font-medium text-[#1A1A1A] flex items-center gap-1.5 mt-0.5">
                  <Clock size={12} className={timeline.isUrgent ? 'text-[#8C2B22]' : 'text-[#8A5E0E]'} />
                  <span>{timeline.relativeText}</span>
                  {timeline.isUpcoming30d && (
                    <Badge variant={timeline.badgeVariant} size="sm">
                      {timeline.badgeLabel}
                    </Badge>
                  )}
                </dd>
              </div>
            )}
            {aliases?.length > 0 && (
              <div className="sm:col-span-2">
                <dt className="text-[#8A8580]">Aliases</dt>
                <dd className="text-[#4B4845] mt-0.5">{aliases.join(', ')}</dd>
              </div>
            )}
          </dl>
        )}
      </div>
    )
  }

  // Mode: "standard"
  if (compact) {
    return (
      <div className={clsx('flex flex-wrap items-center gap-2 text-xs', className)}>
        {isMandatory ? (
          <>
            <Badge variant="warning">{t('results.mandatoryCert')}</Badge>
            {timeline && (
              <span className={clsx(
                'inline-flex items-center gap-1 font-medium',
                timeline.isUrgent ? 'text-[#8C2B22]' : 'text-[#8A5E0E]'
              )}>
                <Clock size={11} />
                {timeline.relativeText}
              </span>
            )}
          </>
        ) : (
          <Badge variant="neutral">{t('standardDetail.noMandatoryCert')}</Badge>
        )}
      </div>
    )
  }

  return (
    <div className={clsx('rounded-md border p-4 bg-white', className, isMandatory ? 'border-[#EDD087] bg-[#FDFCF7]' : 'border-[#E4E1DA]')}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          {isMandatory ? (
            <AlertCircle size={18} className="text-[#8A5E0E] shrink-0" />
          ) : (
            <CheckCircle2 size={18} className="text-[#1F5C4D] shrink-0" />
          )}
          <div>
            <p className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider">
              {t('standardDetail.qcoStatus')}
            </p>
            <h4 className="text-sm font-bold text-[#1A1A1A]">
              {isMandatory ? t('results.mandatoryCert') : t('certification.voluntaryScheme')}
            </h4>
          </div>
        </div>
        {isMandatory ? (
          <Badge variant="warning">{t('common.mandatory')}</Badge>
        ) : (
          <Badge variant="neutral">{t('common.optional')}</Badge>
        )}
      </div>

      <p className="text-xs text-[#5C5A55] leading-relaxed mb-3">
        {isMandatory
          ? t('qco.mandatoryCovered')
          : t('certification.voluntaryDesc')}
      </p>

      {isMandatory && (
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-3 border-t border-[#EDEBE5] text-xs">
          <div>
            <dt className="text-[#8A8580]">{t('standardDetail.certBody')}</dt>
            <dd className="font-medium text-[#1A1A1A]">{certificationBody}</dd>
          </div>
          <div>
            <dt className="text-[#8A8580]">Scheme</dt>
            <dd className="font-medium text-[#1A1A1A]">{scheme || 'ISI Mark / CRS'}</dd>
          </div>
          {timeline && (
            <div className="sm:col-span-2">
              <dt className="text-[#8A8580]">{t('qco.enforcementDate')}</dt>
              <dd className="font-medium text-[#1A1A1A] flex items-center gap-2 mt-0.5 flex-wrap">
                <span className={timeline.isUrgent ? 'text-[#8C2B22] font-semibold' : 'text-[#1A1A1A]'}>
                  {timeline.relativeText}
                </span>
                {timeline.isUpcoming30d && (
                  <Badge variant={timeline.badgeVariant} size="sm">
                    {timeline.badgeLabel}
                  </Badge>
                )}
              </dd>
            </div>
          )}
        </dl>
      )}
    </div>
  )
}

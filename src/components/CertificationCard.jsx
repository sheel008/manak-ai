import React from 'react';
import { ShieldCheck, ShieldAlert, Calendar, FileText } from 'lucide-react';
import clsx from 'clsx';
import { useLang } from '../context/LangContext';

export default function CertificationCard({ qco = {} }) {
  const { t } = useLang();
  if (!qco) return null;

  const isMandatory = Boolean(qco.mandatory);
  const enforcementDate = qco.enforcement_date;
  const rule = qco.rule || (isMandatory ? 'Mandatory QCO in force.' : 'Voluntary / Standard BIS Product Certification.');

  return (
    <div
      className={clsx(
        'mt-3 rounded-lg border p-3.5 transition-colors',
        isMandatory
          ? 'bg-[#E4F2EE] border-[#A8D5C9] text-[#1F5C4D]'
          : 'bg-[#F4F3EF] border-[#DDD9D0] text-[#4B4845]'
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          {isMandatory ? (
            <div className="p-1 rounded bg-[#2F6F5E] text-white">
              <ShieldCheck size={16} aria-hidden="true" focusable="false" />
            </div>
          ) : (
            <div className="p-1 rounded bg-[#8A8580] text-white">
              <ShieldAlert size={16} aria-hidden="true" focusable="false" />
            </div>
          )}
          <span className="font-semibold text-xs uppercase tracking-wide">
            {isMandatory ? t('chat.mandatoryQco') : t('chat.voluntaryBis')}
          </span>
        </div>

        <span
          className={clsx(
            'text-[11px] font-bold px-2 py-0.5 rounded border uppercase',
            isMandatory
              ? 'bg-white text-[#1F5C4D] border-[#A8D5C9]'
              : 'bg-white text-[#4B4845] border-[#DDD9D0]'
          )}
        >
          {isMandatory ? t('chat.isiCompulsory') : t('chat.isiOptional')}
        </span>
      </div>

      <div className="text-xs space-y-1.5 mt-2">
        <div className="flex items-start gap-1.5">
          <FileText size={13} className="mt-0.5 flex-shrink-0 opacity-70" aria-hidden="true" focusable="false" />
          <span className="leading-relaxed">
            <strong>{t('chat.applicableRule')}</strong> {rule}
          </span>
        </div>

        {enforcementDate && (
          <div className="flex items-center gap-1.5">
            <Calendar size={13} className="opacity-70 flex-shrink-0" aria-hidden="true" focusable="false" />
            <span>
              <strong>{t('chat.enforcementDate')}</strong> {enforcementDate}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

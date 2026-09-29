import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, GitMerge, ExternalLink } from 'lucide-react'
import Badge from './Badge'
import clsx from 'clsx'
import { useLang } from '../context/LangContext'

const RELATION_CATEGORIES = [
  { key: 'SAFETY_RELATED', label: 'Safety & Protection Standards' },
  { key: 'TESTING_RELATED', label: 'Testing & Determination Methods' },
  { key: 'INSTALLATION_RELATED', label: 'Installation & Codes of Practice' },
  { key: 'TERMINOLOGY_RELATED', label: 'Terminology & Glossary Standards' },
  { key: 'GENERAL_RELATED', label: 'Co-Cited Standards' },
]

export default function RelatedStandardsList({
  normativeReferences = [],
  relatedStandards = [],
  showNormative = true,
  showRelated = true,
  className,
}) {
  const { t } = useLang()
  const normRefs = Array.isArray(normativeReferences) ? normativeReferences : []
  const relStds = Array.isArray(relatedStandards) ? relatedStandards : []

  return (
    <div className={clsx('space-y-6', className)}>
      {/* ── SECTION 1: DIRECT NORMATIVE REFERENCES ── */}
      {showNormative && (
        <div className="bg-white rounded-md border border-[#E4E1DA] p-5 shadow-card">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <p className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen size={13} className="text-[#2155A3]" /> {t('related.mandatoryCitations')}
              </p>
              <h4 className="text-sm font-bold text-[#1A1A1A]">
                {t('related.directNormative')}
              </h4>
            </div>
            <Badge variant="info" size="sm">
              {normRefs.length} {t('related.directCitationBadge')}
            </Badge>
          </div>
          <p className="text-xs text-[#5C5A55] mb-3">
            {t('related.directCitationDesc')}
          </p>

          {normRefs.length > 0 ? (
            <div className="space-y-2">
              {normRefs.map((ref, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded bg-[#FAFAF8] border border-[#E4E1DA] text-xs hover:border-[#16294D] transition-colors">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="font-mono-bis text-[#2155A3] font-bold shrink-0 bg-[#E4EDF9] px-2 py-0.5 rounded">
                      {ref.is_number}
                    </span>
                    <span className="text-[#1A1A1A] font-medium truncate" title={ref.title || 'Referenced Standard'}>
                      {ref.title || 'Referenced Standard'}
                    </span>
                  </div>
                  <Link
                    to={`/standard/${encodeURIComponent(ref.is_number)}`}
                    className="text-[#2155A3] hover:underline flex items-center gap-1 shrink-0 ml-2"
                  >
                    <span>{t('dashboard.viewStandard')}</span> <ArrowRight size={11} />
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4 bg-[#FAFAF8] rounded border border-dashed border-[#DDD9D0] text-xs text-[#8A8580]">
              {t('related.noDirect')}
            </div>
          )}
        </div>
      )}

      {/* ── SECTION 2: CO-CITED / RELATED STANDARDS (SQL COMPUTED) ── */}
      {showRelated && (
        <div className="bg-white rounded-md border border-[#E4E1DA] p-5 shadow-card">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <p className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider flex items-center gap-1.5">
                <GitMerge size={13} className="text-[#2F6F5E]" /> {t('related.companionStandards')}
              </p>
              <h4 className="text-sm font-bold text-[#1A1A1A]">
                {t('results.relatedStds')}
              </h4>
            </div>
            <Badge variant="success" size="sm">
              {relStds.length} {t('related.coOccurringBadge')}
            </Badge>
          </div>
          <p className="text-xs text-[#5C5A55] mb-3">
            {t('related.companionDesc')}
          </p>

          {relStds.length > 0 ? (
            <div className="space-y-4">
              {RELATION_CATEGORIES.map(category => {
                const items = relStds.filter(r => (r.relation_type || 'GENERAL_RELATED') === category.key)
                if (items.length === 0) return null

                return (
                  <div key={category.key}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold text-[#4B4845] uppercase tracking-wider">
                        {category.label}
                      </span>
                      <span className="text-[10px] text-[#8A8580]">
                        {items.length}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-2">
                      {items.map((rs, i) => (
                        <div key={i} className="flex flex-col p-2.5 rounded bg-[#FAFAF8] border border-[#E4E1DA] text-xs hover:border-[#16294D] transition-colors">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono-bis text-[#2155A3] font-bold">
                              {rs.is_number}
                            </span>
                            <Link
                              to={`/standard/${encodeURIComponent(rs.is_number)}`}
                              className="text-[#2155A3] hover:underline flex items-center gap-1 shrink-0 text-[11px]"
                            >
                              <span>{t('dashboard.viewStandard')}</span> <ExternalLink size={10} />
                            </Link>
                          </div>
                          <p className="text-[#1A1A1A] font-medium line-clamp-2" title={rs.title}>
                            {rs.title || 'Indian Standard Specification'}
                          </p>
                          {rs.shared_references && rs.shared_references.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-[#EDEBE5] text-[10px] text-[#8A8580]">
                              <span>Shared:</span>
                              {rs.shared_references.map((sr, idx) => (
                                <span key={idx} className="font-mono-bis bg-[#EDEBE5] text-[#4B4845] px-1 rounded">
                                  {sr}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-4 bg-[#FAFAF8] rounded border border-dashed border-[#DDD9D0] text-xs text-[#8A8580]">
              {t('related.noCompanion')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

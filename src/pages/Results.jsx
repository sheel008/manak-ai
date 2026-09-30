import { useState, useEffect } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { ChevronDown, ChevronUp, Search, Check, X, Flag, ArrowRight, Loader2, AlertTriangle } from 'lucide-react'
import Layout from '../components/Layout'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import Toast from '../components/Toast'
import Breadcrumb from '../components/Breadcrumb'
import clsx from 'clsx'
import api from '../services/api'
import { useLang } from '../context/LangContext'
import CertificationStatus from '../components/CertificationStatus'
import AmendmentTimeline from '../components/AmendmentTimeline'
import RelatedStandardsList from '../components/RelatedStandardsList'

function SubScoreBar({ label, score }) {
  const width = Math.max(0, Math.min(100, score || 0))
  const colorClass = width >= 60 ? 'bg-[#2F6F5E]' : width >= 40 ? 'bg-[#B8862B]' : 'bg-[#C8C4BB]'
  return (
    <div className="flex items-center gap-2 sm:gap-3 text-xs mb-1.5">
      <div className="w-20 sm:w-28 text-[#5C5A55] truncate shrink-0">{label}</div>
      <div className="flex-1 h-1.5 bg-[#E4E1DA] rounded-full overflow-hidden">
        <div className={`h-full ${colorClass}`} style={{ width: `${width}%` }} />
      </div>
      <div className="w-8 sm:w-9 text-right font-medium text-[#1A1A1A] shrink-0">{Math.round(width)}%</div>
    </div>
  )
}

function ReviewControls({ requestId, isNumber, onReviewed }) {
  const [decision, setDecision] = useState(null)
  const [sending, setSending] = useState(false)
  const { t } = useLang()

  const submit = async (d) => {
    setSending(true)
    setDecision(d)
    try {
      await api.submitReview(requestId, isNumber, d)
      onReviewed?.(d)
    } catch (err) {
      console.error(err)
      setDecision(null)
    } finally {
      setSending(false)
    }
  }

  const btn = (value, label, icon, activeCls) => (
    <button
      onClick={() => submit(value)}
      disabled={sending || (decision && decision !== value)}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded text-xs font-semibold border transition-colors focus:outline-none cursor-pointer',
        decision === value
          ? activeCls
          : 'bg-white border-[#E4E1DA] text-[#4B4845] hover:border-[#16294D]'
      )}
    >
      {icon}{label}
    </button>
  )

  return (
    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
      {btn('accept', t('results.accept'), <Check size={13} />, 'bg-[#E6F2EF] border-[#2F6F5E] text-[#2F6F5E]')}
      {btn('reject', t('results.reject'), <X size={13} />, 'bg-[#FBE9E7] border-[#A6362C] text-[#A6362C]')}
      {btn('flag', t('results.flag'), <Flag size={13} />, 'bg-[#FDF3E0] border-[#B8862B] text-[#B8862B]')}
      {decision && <span className="text-[11px] text-[#2F6F5E] font-medium">{t('common.recorded')}</span>}
    </div>
  )
}

function ResultCard({ result, requestId, onReviewed }) {
  const [expanded, setExpanded] = useState(false)
  const { t } = useLang()
  const reviewData = result.certification || {}

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left px-3.5 sm:px-5 py-3 sm:py-4 focus:outline-none focus:ring-2 focus:ring-[#16294D] focus:ring-inset cursor-pointer"
        aria-expanded={expanded}
      >
        <div className="flex items-start justify-between gap-2.5 sm:gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap mb-1.5">
              <span className="font-mono-bis text-xs sm:text-sm font-semibold text-[#16294D] bg-[#EDEBE5] px-2 py-0.5 rounded">{result.is_number}</span>
              <span className={clsx(
                'inline-flex items-center px-2 py-0.5 rounded text-[11px] sm:text-xs font-semibold',
                (result.confidence ?? result.relevance_score) >= 60 ? 'text-[#2F6F5E] bg-[#E6F2EF] border border-[#A2D4C5]'
                  : (result.confidence ?? result.relevance_score) >= 40 ? 'text-[#B8862B] bg-[#FDF3E0] border border-[#E8D2A0]'
                  : 'text-[#5C5A55] bg-[#F0EEE9] border border-[#DDD9D0]'
              )}>
                {Math.round(result.confidence ?? result.relevance_score ?? 0)}% {t('results.match')}
              </span>
              {result.department && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] sm:text-xs font-medium bg-[#E4EDF9] text-[#16294D] border border-[#A8C2E8]">
                  {result.department}
                </span>
              )}
              {result.category && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] sm:text-xs font-medium bg-[#F0EEE9] text-[#4B4845] border border-[#DDD9D0]">
                  {result.category}
                </span>
              )}
              {result.is_qco_mandatory
                ? <Badge variant="warning">{t('results.mandatoryCert')}</Badge>
                : <Badge variant="neutral">{t('standardDetail.noMandatoryCert')}</Badge>
              }
            </div>
            <p className="text-sm sm:text-base font-medium text-[#1A1A1A] mb-1">{result.title}</p>
            <p className="text-xs sm:text-sm text-[#5C5A55] line-clamp-2">{result.scope}</p>
          </div>
          <div className="shrink-0 text-[#5C5A55] mt-1">
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[#E4E1DA] px-3.5 sm:px-5 py-3.5 sm:py-4 bg-[#FAFAF8]">
          {/* Why Recommended Section */}
          {result.why_recommended && (
            <div className="mb-4 bg-[#F2F8F6] border border-[#BDE3D5] p-3.5 rounded-md text-xs text-[#1D5443]">
              <div className="font-semibold text-xs text-[#164335] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Check size={13} className="text-[#2F6F5E]" /> Why Recommended
              </div>
              <p className="leading-relaxed">{result.why_recommended}</p>
            </div>
          )}

          {/* Explanation + sub scores */}
          <div className="mb-4 bg-white p-4 rounded-md border border-[#E4E1DA] shadow-sm">
            <p className="text-sm text-[#4B4845] leading-relaxed mb-3">{result.explanation}</p>
            <p className="text-[11px] font-semibold text-[#5C5A55] uppercase mb-2">{t('results.scoringBreakdown')}</p>
            <SubScoreBar label={t('results.semanticSim')} score={result.similarity_score ?? 0} />
            <SubScoreBar label={t('results.keywordOverlap')} score={result.keyword_score ?? 0} />
            <SubScoreBar label={t('results.specMatch')} score={result.specification_score ?? 0} />
            {result.department_score !== undefined && result.department_score > 0 && (
              <SubScoreBar label="Department Match" score={result.department_score} />
            )}
          </div>


          {/* Evidence */}
          {result.evidence && (
            <div className="mb-4 bg-white p-4 rounded-md border border-[#E4E1DA] shadow-sm">
              <p className="text-[11px] font-semibold text-[#5C5A55] uppercase tracking-wider mb-2 flex items-center gap-2">
                <Search size={13} className="text-[#2B5C8A]" /> {t('results.evidence')}
              </p>
              {result.evidence.source_excerpt && (
                <blockquote className="border-l-2 border-[#16294D] pl-3 italic text-sm text-[#4B4845] mb-2">
                  "{result.evidence.source_excerpt}"
                </blockquote>
              )}
              {result.evidence.matched_specifications?.length > 0 && (
                <div className="mb-2">
                  <p className="text-[11px] text-[#5C5A55] mb-1 font-medium">{t('results.matchedSpecs')}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.evidence.matched_specifications.map((m, i) => {
                      const text = typeof m === 'string'
                        ? m
                        : (m.query && m.matched ? `${m.query} → ${m.matched}` : m.value || m.stored || m.query || JSON.stringify(m))
                      return (
                        <span key={i} className="inline-flex px-2 py-0.5 bg-[#E6F2EF] text-[#2F6F5E] rounded text-xs font-medium">
                          {text}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )}
              {result.evidence.overlapping_keywords?.length > 0 && (
                <div>
                  <p className="text-[11px] text-[#5C5A55] mb-1 font-medium">{t('results.overlapKw')}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.evidence.overlapping_keywords.map((k, i) => (
                      <span key={i} className="inline-flex px-2 py-0.5 bg-[#EDEBE5] text-[#4B4845] rounded text-xs">
                        {k}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Version info and amendment timeline */}
          <AmendmentTimeline
            version={result.version_info?.version}
            lastAmended={result.version_info?.last_amended}
            amendmentHistory={result.version_info?.amendment_history}
            className="mb-4"
          />

          {/* Normative references (citations) and Related standards (co-citations) */}
          <RelatedStandardsList
            normativeReferences={result.normative_references}
            relatedStandards={result.related_standards}
            className="mb-4"
          />

          {/* Certification / QCO Status */}
          <CertificationStatus
            mode="standard"
            isQcoMandatory={result.is_qco_mandatory ?? reviewData.is_qco_mandatory}
            enforcementDate={result.qco_enforcement_date || reviewData.enforcement_date}
            scheme={reviewData.scheme}
            className="mb-4"
          />

          {/* Actions + review */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#E4E1DA]">
            <div className="flex gap-2 flex-wrap">
              <Link to={`/standard/${encodeURIComponent(result.is_number)}`}>
                <Button variant="primary" size="sm">{t('results.openFullStd')}</Button>
              </Link>
            </div>
            <ReviewControls requestId={requestId} isNumber={result.is_number} onReviewed={onReviewed} />
          </div>
        </div>
      )}
    </Card>
  )
}

export default function ResultsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useLang()
  const query = location.state?.query || ''
  const response = location.state?.response || null
  const isReopen = location.state?.reopen || false

  const [results, setResults] = useState(response?.results || [])
  const [requestId, setRequestId] = useState(response?.request_id || '')
  const [abstained, setAbstained] = useState(Boolean(response?.abstained))
  const [abstentionReason, setAbstentionReason] = useState(response?.abstention_reason || null)
  const [threshold, setThreshold] = useState(response?.threshold || 40)
  const [loading, setLoading] = useState(!response)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    if (!response && query) {
      setLoading(true)
      api.search(query, null, isReopen)
        .then(data => {
          setResults(data.results || [])
          setRequestId(data.request_id || '')
          setAbstained(Boolean(data.abstained))
          setAbstentionReason(data.abstention_reason)
          setThreshold(data.threshold || 40)
          setLoading(false)
        })
        .catch(err => {
          console.error(err)
          setError(err.message || 'Failed to fetch search results.')
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [query, response, isReopen])

  const handleReview = async () => {
    setToast({ message: t('results.reviewRecorded'), type: 'success' })
    window.setTimeout(() => setToast(null), 2500)
  }

  if (loading) {
    return (
      <Layout title={t('results.title')}>
        <div className="flex items-center justify-center h-64">
          <Loader2 size={32} className="animate-spin text-[#16294D]" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout breadcrumb={
      <Breadcrumb items={[
        { label: t('navigation.search'), href: '/search' },
        { label: t('results.title') },
      ]} />
    }>
      {/* Query chip */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <span className="text-xs text-[#5C5A55]">{t('results.resultsFor')}</span>
        <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-[#E4E1DA] rounded-[6px] text-sm font-medium text-[#1A1A1A]">
          <Search size={13} className="text-[#5C5A55]" />
          {query}
        </span>
        {requestId && (
          <span className="text-[11px] font-mono-bis text-[#8A8580]">ref: {requestId}</span>
        )}
        <Button variant="ghost" size="sm" onClick={() => navigate('/search')}>{t('results.newSearch')}</Button>
      </div>

      {/* Network / server error */}
      {error && (
        <Card className="p-6 mb-6 border-l-4 border-l-[#A6362C] bg-[#FBE9E7]">
          <p className="text-sm font-semibold text-[#A6362C] mb-1">Search Error</p>
          <p className="text-sm text-[#4B4845]">{error}</p>
          <div className="mt-4">
            <Button variant="secondary" size="sm" onClick={() => navigate('/search')}>{t('results.tryAnotherSearch')}</Button>
          </div>
        </Card>
      )}

      {/* Honest Abstention Display */}
      {abstained && (
        <Card className="p-8 text-center mb-6 border-l-4 border-l-[#B8862B] bg-white shadow-card">
          <div className="w-14 h-14 rounded-full bg-[#FDF3E0] flex items-center justify-center mx-auto mb-4 border border-[#B8862B]/20">
            <AlertTriangle size={26} className="text-[#B8862B]" />
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FDF3E0] text-[#B8862B] text-xs font-semibold uppercase tracking-wider mb-3">
            {t('results.noMatchFound')}
          </div>
          <h3 className="text-xl font-bold text-[#1A1A1A] mb-2">{t('results.noMatchFound')}</h3>
          <p className="text-sm text-[#4B4845] max-w-xl mx-auto leading-relaxed mb-4">
            {abstentionReason || t('results.noMatchDesc')}
          </p>
          {threshold && (
            <p className="text-xs text-[#8A8580] font-mono-bis mb-4">
              Threshold: {threshold}%
            </p>
          )}
          <div className="flex justify-center gap-3 mt-4">
            <Button variant="primary" size="md" onClick={() => navigate('/search')}>{t('results.tryAnotherSearch')}</Button>
            <Button variant="secondary" size="md" onClick={() => navigate('/chat')}>{t('navigation.askManak')}</Button>
          </div>
        </Card>
      )}

      {!abstained && !error && (
        <>
          <p className="text-sm text-[#5C5A55] mb-4">
            {results.length} {results.length === 1 ? t('results.standardFound') : t('results.standardsFound')}
          </p>
          {results.length === 0 ? (
            <EmptyState
              icon={Search}
              title={t('results.noMatchFound')}
              description={t('results.noMatchDesc')}
              actionLabel={t('results.tryAnotherSearch')}
              onAction={() => navigate('/search')}
            />
          ) : (
            <div className="space-y-3">
              {results.map(r => (
                <ResultCard key={r.is_number} result={r} requestId={requestId} onReviewed={handleReview} />
              ))}
            </div>
          )}
        </>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

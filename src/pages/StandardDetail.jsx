import { useParams } from 'react-router-dom'
import { BookmarkPlus, Copy, Download, Loader2 } from 'lucide-react'
import Layout from '../components/Layout'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import Breadcrumb from '../components/Breadcrumb'
import Toast from '../components/Toast'
import { useState, useEffect } from 'react'
import api from '../services/api'
import { useLang } from '../context/LangContext'
import CertificationStatus from '../components/CertificationStatus'
import AmendmentTimeline from '../components/AmendmentTimeline'
import RelatedStandardsList from '../components/RelatedStandardsList'

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-[#5C5A55] uppercase tracking-wider mb-3">{title}</h3>
      {children}
    </div>
  )
}

export default function StandardDetail() {
  const params = useParams()
  const id = params['*'] || params.id || ''  // handles both /standard/* and /standard/:id
  const { t } = useLang()
  const [std, setStd] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.getStandard(id)
      .then(data => {
        setStd(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError(err.message || 'Failed to load standard details.')
        setLoading(false)
      })
  }, [id])

  const handleCopy = () => {
    if (!std) return
    const text = `${std.is_number} — ${std.title} (${std.version || 'Current'})`
    navigator.clipboard?.writeText(text)
    setToast({ message: t('standardDetail.copied'), type: 'success' })
  }

  const handleSave = async () => {
    if (!std) return
    try {
      await api.saveStandard(std.is_number)
      setToast({ message: `${std.is_number} ${t('standardDetail.saved')}`, type: 'success' })
    } catch (err) {
      if (err.status === 409 || err.message?.includes('Already saved')) {
        setToast({ message: `${std.is_number} ${t('standardDetail.saved')}`, type: 'info' })
      } else {
        const text = `${std.is_number} — ${std.title}`
        navigator.clipboard?.writeText(text)
        setToast({ message: `${std.is_number} ${t('standardDetail.copied')}`, type: 'success' })
      }
    }
  }

  const handleExport = async () => {
    if (!std) return
    try {
      const blob = await api.exportStandard(std.is_number)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${std.is_number.replace(/[\s\/:]/g, '_')}_reference.txt`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
      setToast({ message: 'Failed to export standard reference block.', type: 'error' })
    }
  }

  const handleGemPush = async () => {
    if (!std) return
    try {
      const blob = await api.exportGemPayload(std.is_number)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${std.is_number.replace(/[\s\/:]/g, '_')}_gem_payload.json`
      a.click()
      window.URL.revokeObjectURL(url)
      setToast({ message: 'GeM procurement payload generated successfully.', type: 'success' })
    } catch (err) {
      console.error(err)
      setToast({ message: 'Failed to generate GeM payload.', type: 'error' })
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 size={32} className="animate-spin text-[#16294D]" />
        </div>
      </Layout>
    )
  }

  if (error || !std) {
    return (
      <Layout>
        <div className="p-8 text-center text-[#A6362C]">
          <p className="font-semibold text-base mb-1">{t('results.noMatchFound')}</p>
          <p className="text-sm text-[#5C5A55]">{error || t('results.noMatchDesc')}</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout breadcrumb={
      <Breadcrumb items={[
        { label: t('navigation.search'), href: '/search' },
        { label: t('results.title'), href: '/results' },
        { label: std.is_number },
      ]} />
    }>
      <div className="max-w-4xl">
        {/* Header */}
        <Card className="p-5 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="font-mono-bis text-sm text-[#2B5C8A] mb-1 font-bold">{std.is_number}</p>
              <h2 className="text-xl font-bold text-[#1A1A1A] mb-2">{std.title}</h2>
              <div className="flex flex-wrap items-center gap-2 text-sm text-[#5C5A55]">
                <span>{t('standardDetail.version')}: <span className="font-medium text-[#1A1A1A]">{std.version || 'Current'}</span></span>
                <span className="text-[#E4E1DA]">|</span>
                <span>{t('common.category')}: <span className="font-medium text-[#1A1A1A]">{std.category}</span></span>
                {std.last_amended && (
                  <>
                    <span className="text-[#E4E1DA]">|</span>
                    <span>{t('standardDetail.lastUpdated')}: <span className="font-medium text-[#1A1A1A]">{std.last_amended}</span></span>
                  </>
                )}
                {std.sub_category && (
                  <>
                    <span className="text-[#E4E1DA]">|</span>
                    <Badge variant="neutral">{std.sub_category}</Badge>
                  </>
                )}
              </div>
            </div>
            <div className="flex gap-2 shrink-0 flex-wrap justify-end">
              <Button variant="secondary" size="sm" onClick={handleGemPush} className="border-[#2F6F5E] text-[#2F6F5E] cursor-pointer">
                {t('standardDetail.gemPush')}
              </Button>
              <Button variant="secondary" size="sm" onClick={handleExport} className="cursor-pointer">
                <Download size={14} /> {t('standardDetail.exportRef')}
              </Button>
              <Button variant="secondary" size="sm" onClick={handleCopy} className="cursor-pointer">
                <Copy size={14} /> {t('standardDetail.copyRef')}
              </Button>
              <Button variant="primary" size="sm" onClick={handleSave} className="cursor-pointer">
                <BookmarkPlus size={14} /> {t('standardDetail.save')}
              </Button>
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content — 2 cols */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-5">
              <Section title={t('standardDetail.scope')}>
                <p className="text-sm text-[#1A1A1A] leading-relaxed">{std.scope || 'No scope description recorded.'}</p>
              </Section>
            </Card>

            {/* Specifications */}
            {std.specifications && Object.keys(std.specifications).length > 0 && (
              <Card className="p-5">
                <Section title={t('search.describeProduct')}>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                    {Object.entries(std.specifications).map(([k, v]) => (
                      <div key={k} className="bg-[#FAFAF8] p-2.5 rounded border border-[#E4E1DA]">
                        <p className="text-xs text-[#5C5A55] font-medium capitalize mb-0.5">{k.replace(/_/g, ' ')}</p>
                        <p className="font-medium text-[#1A1A1A]">{String(v)}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              </Card>
            )}

            {/* Normative References (Direct) & Related Standards (Co-citations) */}
            <RelatedStandardsList
              normativeReferences={std.normative_references_resolved}
              relatedStandards={std.related_standards}
            />

            {/* Amendments timeline */}
            <AmendmentTimeline
              version={std.version}
              lastAmended={std.last_amended}
              amendmentHistory={std.amendment_history}
            />
          </div>

          {/* Sidebar — 1 col */}
          <div className="space-y-6">
            {/* QCO Regulatory Status */}
            <CertificationStatus
              mode="standard"
              isQcoMandatory={std.is_qco_mandatory}
              enforcementDate={std.qco_enforcement_date}
              scheme={std.is_qco_mandatory ? 'Compulsory Registration Scheme (CRS)' : null}
            />

            {/* Summary Metadata card */}
            <Card className="p-4">
              <p className="text-xs font-semibold text-[#8A8580] uppercase tracking-wider mb-3">
                {t('standardDetail.title')}
              </p>
              <dl className="space-y-2.5 text-xs">
                <div>
                  <dt className="text-[#5C5A55]">Standard Identifier</dt>
                  <dd className="font-mono-bis font-semibold text-[#2155A3] mt-0.5">{std.is_number}</dd>
                </div>
                <div>
                  <dt className="text-[#5C5A55]">{t('standardDetail.certBody')}</dt>
                  <dd className="font-medium text-[#1A1A1A] mt-0.5">{t('common.bisGovLabel')}</dd>
                </div>
                <div>
                  <dt className="text-[#5C5A55]">{t('standardDetail.department')}</dt>
                  <dd className="font-medium text-[#1A1A1A] mt-0.5">{std.category}</dd>
                </div>
                <div>
                  <dt className="text-[#5C5A55]">{t('related.directNormative')}</dt>
                  <dd className="font-medium text-[#1A1A1A] mt-0.5">{std.normative_references_resolved?.length || 0} referenced</dd>
                </div>
                <div>
                  <dt className="text-[#5C5A55]">{t('related.companionStandards')}</dt>
                  <dd className="font-medium text-[#1A1A1A] mt-0.5">{std.related_standards?.length || 0} related</dd>
                </div>
              </dl>
            </Card>
          </div>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

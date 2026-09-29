import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldCheck, ShieldAlert, Search, Loader2, ArrowUpRight,
  Calendar, FileText, AlertCircle, Info
} from 'lucide-react'
import Layout from '../components/Layout'
import Card from '../components/Card'
import { useLang } from '../context/LangContext'
import api from '../services/api'

export default function QCOChecker() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [sampleProducts] = useState([
    'LED Street Light',
    'OPC Cement',
    'Pressure Cooker',
    'Seat Belt',
    'TMT Steel Bar',
    'Water Thinned Emulsion Paint',
    'PVC Pipe',
    'Fire Extinguisher',
  ])
  const { t } = useLang()

  const handleCheck = async (productToSearch) => {
    const target = (productToSearch || query).trim()
    if (!target) return
    setLoading(true)
    setSearched(false)
    try {
      const data = await api.checkQCO(target)
      setResult(data)
    } catch (err) {
      console.error(err)
      setResult({ found: false, message: err.message || 'Error checking product certification status.' })
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  return (
    <Layout title={t('qco.title')}>
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#111111] tracking-tight">
              {t('qco.heading')}
            </h1>
            <span className="text-[11px] font-semibold text-[#1F5C4D] bg-[#E4F2EE] border border-[#A8D5C9] px-2 py-0.5 rounded">
              {t('qco.badge')}
            </span>
          </div>
          <p className="text-sm text-[#4B4845]">
            {t('qco.subtitle')}
          </p>
        </div>

        {/* Search Input Box */}
        <div className="mb-6">
          <div className="relative flex items-center bg-white border border-[#DDD9D0] rounded-lg shadow-sm focus-within:border-[#16294D] focus-within:ring-2 focus-within:ring-[#16294D]/15 transition-all">
            <Search size={18} className="ml-4 text-[#8A8580] shrink-0 pointer-events-none" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCheck()
                }
              }}
              placeholder={t('qco.placeholder')}
              className="w-full h-[52px] pl-3 pr-28 text-sm text-[#111111] bg-transparent focus:outline-none placeholder-[#8A8580]"
              aria-label={t('qco.heading')}
              autoFocus
            />
            <div className="pr-2">
              <button
                type="button"
                onClick={() => handleCheck()}
                disabled={!query.trim() || loading}
                className="h-[38px] px-4 text-xs font-semibold bg-[#16294D] hover:bg-[#1E3761] text-white rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-2xs cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>{t('qco.checking')}</span>
                  </>
                ) : (
                  <span>{t('qco.checkBtn')}</span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Verified Result Card */}
        {searched && (
          <div className="mb-6 animate-dropdown">
            {result && result.found ? (
              <div className="rounded-lg border border-[#DDD9D0] bg-white shadow-sm overflow-hidden">
                {/* Result Top Banner */}
                <div
                  className={`p-4 border-b flex flex-wrap items-center justify-between gap-3 ${
                    result.is_qco_mandatory
                      ? 'bg-[#E4F2EE] border-[#A8D5C9] text-[#1F5C4D]'
                      : 'bg-[#F4F3EF] border-[#DDD9D0] text-[#4B4845]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {result.is_qco_mandatory ? (
                      <div className="p-1 rounded bg-[#2F6F5E] text-white">
                        <ShieldCheck size={20} />
                      </div>
                    ) : (
                      <div className="p-1 rounded bg-[#8A8580] text-white">
                        <ShieldAlert size={20} />
                      </div>
                    )}
                    <div>
                      <h2 className="text-sm font-bold uppercase tracking-wide">
                        {result.is_qco_mandatory
                          ? t('qco.mandatoryRequired')
                          : t('qco.voluntaryNotice')}
                      </h2>
                      <p className="text-xs opacity-85">
                        {result.is_qco_mandatory
                          ? t('qco.mandatoryCovered')
                          : t('qco.voluntaryCovered')}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[11px] font-bold px-2.5 py-1 rounded border uppercase ${
                      result.is_qco_mandatory
                        ? 'bg-white text-[#1F5C4D] border-[#A8D5C9]'
                        : 'bg-white text-[#4B4845] border-[#DDD9D0]'
                    }`}
                  >
                    {result.is_qco_mandatory ? t('common.mandatory') : t('common.optional')}
                  </span>
                </div>

                {/* Details Section */}
                <div className="p-5 space-y-4">
                  {/* Product & Standard */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <span className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider block mb-1">
                        {t('qco.product')}
                      </span>
                      <p className="text-sm font-bold text-[#111111]">{result.product_name}</p>
                      {result.aliases && result.aliases.length > 0 && (
                        <p className="text-xs text-[#5C5A55] mt-0.5">
                          {result.aliases.slice(0, 3).join(', ')}
                        </p>
                      )}
                    </div>

                    <div>
                      <span className="text-[11px] font-semibold text-[#8A8580] uppercase tracking-wider block mb-1">
                        {t('qco.applicableStandard')}
                      </span>
                      {result.applicable_is_number ? (
                        <Link
                          to={`/standard/${encodeURIComponent(result.applicable_is_number)}`}
                          className="inline-flex items-center gap-1.5 font-mono text-xs font-bold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] hover:border-[#16294D] px-2.5 py-1 rounded transition-colors"
                        >
                          <span>{result.applicable_is_number}</span>
                          <ArrowUpRight size={13} />
                        </Link>
                      ) : (
                        <span className="text-xs text-[#5C5A55]">{t('qco.regulatoryOrder')}</span>
                      )}
                    </div>
                  </div>

                  {/* Enforcement & Regulatory Rule */}
                  <div className="pt-3 border-t border-[#EDEBE5] grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="font-semibold text-[#8A8580] uppercase tracking-wider block mb-1">
                        {t('qco.enforcementDate')}
                      </span>
                      <div className="flex items-center gap-1.5 text-[#111111] font-medium">
                        <Calendar size={14} className="text-[#5C5A55]" />
                        <span>{result.enforcement_date || t('qco.activeEnforced')}</span>
                      </div>
                    </div>

                    <div>
                      <span className="font-semibold text-[#8A8580] uppercase tracking-wider block mb-1">
                        {t('qco.qcoRef')}
                      </span>
                      <div className="flex items-center gap-1.5 text-[#111111] font-medium">
                        <FileText size={14} className="text-[#5C5A55]" />
                        <span>BIS Product Certification Scheme (Scheme-I / ISI)</span>
                      </div>
                    </div>
                  </div>

                  {/* Gazette Verification Caption */}
                  <div className="mt-4 pt-3 border-t border-[#EDEBE5] flex items-start gap-2 text-xs text-[#5C5A55] bg-[#FAFAF8] p-3 rounded border border-[#DDD9D0]">
                    <Info size={15} className="text-[#2155A3] shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-[#111111]">{t('qco.gazetteRef')}: </span>
                      {t('qco.disclaimer')}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <Card className="p-5 border-[#DDD9D0] bg-white">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[#F0EEE9] flex items-center justify-center shrink-0 text-[#5C5A55]">
                    <AlertCircle size={20} />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-[#111111] mb-1">{t('qco.noMatchTitle')}</h3>
                    <p className="text-xs text-[#5C5A55] leading-relaxed mb-3">
                      {result?.message || t('qco.noMatchDesc')}
                    </p>
                    <Link
                      to={`/search?q=${encodeURIComponent(query)}`}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#16294D] bg-[#F4F3EF] hover:bg-[#E4EDF9] border border-[#DDD9D0] px-3 py-1.5 rounded transition-colors"
                    >
                      <span>{t('search.title')} &ldquo;{query}&rdquo;</span>
                      <ArrowUpRight size={13} />
                    </Link>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Sample Products */}
        <div className="rounded-lg border border-[#DDD9D0] bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold text-[#5C5A55] uppercase tracking-wider">
              {t('qco.sampleProducts')}
            </span>
            <span className="text-[11px] text-[#8A8580]">{t('common.details')}</span>
          </div>

          <div className="flex flex-wrap gap-2">
            {sampleProducts.map((p, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setQuery(p)
                  handleCheck(p)
                }}
                className="px-3 py-1.5 text-xs bg-[#FAFAF8] border border-[#DDD9D0] rounded-md text-[#111111] hover:border-[#16294D] hover:bg-[#F0EEE9] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer"
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-4 text-center">
          <span className="text-[11px] text-[#8A8580]">
            {t('qco.disclaimer')}
          </span>
        </div>
      </div>
    </Layout>
  )
}

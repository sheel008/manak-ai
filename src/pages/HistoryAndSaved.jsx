import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Clock, Bookmark, Trash2, ExternalLink, Loader2, Search,
  ArrowUpRight
} from 'lucide-react'
import Layout from '../components/Layout'
import Card from '../components/Card'
import Badge from '../components/Badge'
import Button from '../components/Button'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import Toast from '../components/Toast'
import { useLang } from '../context/LangContext'
import api from '../services/api'

export default function HistoryAndSaved() {
  const navigate = useNavigate()
  const { t } = useLang()
  const [tab, setTab] = useState('history')
  const [history, setHistory] = useState([])
  const [saved, setSaved] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterText, setFilterText] = useState('')
  const [confirmId, setConfirmId] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    Promise.all([
      api.getHistory(),
      api.getSaved(),
    ])
    .then(([h, s]) => {
      setHistory(Array.isArray(h) ? h : [])
      setSaved(Array.isArray(s) ? s : [])
      setLoading(false)
    })
    .catch(err => {
      console.error(err)
      setToast({ message: err.message || 'Failed to load history or saved standards.', type: 'error' })
      setLoading(false)
    })
  }, [])

  const handleRemove = async (is_number) => {
    try {
      await api.deleteSaved(is_number)
      setSaved(s => s.filter(i => i.is_number !== is_number))
      setConfirmId(null)
      setToast({ message: 'Standard removed from bookmarks.', type: 'info' })
    } catch (err) {
      console.error(err)
      setToast({ message: err.message || 'Failed to remove standard.', type: 'error' })
    }
  }

  const toRemove = saved.find(s => s.is_number === confirmId)

  // Filter history or saved standards by search filter text
  const filteredHistory = history.filter(h => {
    if (!filterText.trim()) return true
    const term = filterText.toLowerCase()
    return (
      (h.query && h.query.toLowerCase().includes(term)) ||
      (h.top_result_is_number && h.top_result_is_number.toLowerCase().includes(term)) ||
      (h.department && h.department.toLowerCase().includes(term))
    )
  })

  const filteredSaved = saved.filter(s => {
    if (!filterText.trim()) return true
    const term = filterText.toLowerCase()
    return (
      (s.is_number && s.is_number.toLowerCase().includes(term)) ||
      (s.title && s.title.toLowerCase().includes(term)) ||
      (s.category && s.category.toLowerCase().includes(term))
    )
  })

  if (loading) {
    return (
      <Layout title={t('history.title')}>
        <div className="flex items-center justify-center h-64">
          <Loader2 size={32} className="animate-spin text-[#16294D]" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout title={t('history.title')}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#111111] tracking-tight">
              {t('history.title')}
            </h1>
            <p className="text-xs sm:text-sm text-[#4B4845]">
              {t('history.subtitle')}
            </p>
          </div>
        </div>

        {/* Tabs & Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b border-[#DDD9D0] mb-4 sm:mb-6 pb-2">
          {/* Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {[
              { id: 'history', label: t('history.searchHistoryTab'), count: history.length, icon: Clock },
              { id: 'saved', label: t('history.savedStandardsTab'), count: saved.length, icon: Bookmark },
            ].map(tabItem => (
              <button
                key={tabItem.id}
                onClick={() => { setTab(tabItem.id); setFilterText(''); }}
                className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 -mb-[10px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer whitespace-nowrap
                  ${tab === tabItem.id
                    ? 'border-[#16294D] text-[#16294D] bg-white rounded-t'
                    : 'border-transparent text-[#5C5A55] hover:text-[#111111]'}`}
                aria-selected={tab === tabItem.id}
              >
                <tabItem.icon size={14} className="shrink-0" />
                <span>{tabItem.label}</span>
                <span className="text-[10px] sm:text-[11px] font-bold bg-[#EDEBE5] text-[#4B4845] px-1.5 py-0.2 rounded-full">
                  {tabItem.count}
                </span>
              </button>
            ))}
          </div>

          {/* Quick Filter Input */}
          <div className="relative w-full sm:w-auto">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8580]" />
            <input
              type="text"
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              placeholder={t('history.filterPlaceholder')}
              className="w-full sm:w-64 pl-8 pr-3 py-1.5 text-xs border border-[#DDD9D0] rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-[#16294D] focus:border-[#16294D] placeholder-[#8A8580]"
            />
          </div>
        </div>

        {/* Tab 1: Audit Search History Table */}
        {tab === 'history' ? (
          filteredHistory.length === 0 ? (
            <EmptyState
              icon={Clock}
              title={filterText ? t('results.noMatchFound') : t('history.noHistory')}
              description={filterText ? `${t('results.noMatchDesc')}` : t('history.noHistoryDesc')}
              actionLabel={t('history.searchStandardsBtn')}
              onAction={() => navigate('/search')}
            />
          ) : (
            <Card className="overflow-hidden border-[#DDD9D0] bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left" aria-label="Search audit trail">
                  <thead>
                    <tr className="border-b border-[#DDD9D0] bg-[#FAFAF8] text-[#5C5A55] uppercase text-[10px] tracking-wider font-semibold">
                      <th className="px-4 py-3">{t('history.queryCol')}</th>
                      <th className="px-4 py-3 whitespace-nowrap">{t('history.dateCol')}</th>
                      <th className="px-4 py-3">{t('history.standardCol')}</th>
                      <th className="px-4 py-3 text-center">{t('results.match')}</th>
                      <th className="px-4 py-3 text-right">{t('history.actionsCol')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDEBE5]">
                    {filteredHistory.map(h => (
                      <tr key={h.id} className="hover:bg-[#F4F3EF] transition-colors duration-150">
                        <td className="px-4 py-3 font-semibold text-[#111111] max-w-xs sm:max-w-sm">
                          <span className="line-clamp-2 leading-relaxed">{h.query}</span>
                        </td>
                        <td className="px-4 py-3 text-text-xs font-mono text-[#5C5A55] whitespace-nowrap">
                          {h.timestamp ? new Date(h.timestamp).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric'
                          }) : 'Recent'}
                        </td>
                        <td className="px-4 py-3">
                          {h.top_result_is_number ? (
                            <Link
                              to={`/standard/${encodeURIComponent(h.top_result_is_number)}`}
                              className="inline-flex items-center gap-1 font-mono text-[11px] font-bold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] hover:border-[#16294D] px-2 py-0.5 rounded transition-colors"
                            >
                              <span>{h.top_result_is_number}</span>
                              <ArrowUpRight size={10} />
                            </Link>
                          ) : (
                            <span className="text-[#8A8580] italic">No direct match</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-block px-2 py-0.5 rounded bg-[#FAFAF8] border border-[#DDD9D0] font-mono text-[11px] text-[#4B4845]">
                            {h.result_count ?? 1}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => navigate('/results', { state: { query: h.query, reopen: true } })}
                            className="text-xs h-7 px-2.5 cursor-pointer"
                          >
                            <ExternalLink size={12} />
                            <span>{t('history.reopen')}</span>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )
        ) : (
          /* Tab 2: Saved Standards Cards */
          filteredSaved.length === 0 ? (
            <EmptyState
              icon={Bookmark}
              title={filterText ? t('results.noMatchFound') : t('history.noSaved')}
              description={filterText ? t('results.noMatchDesc') : t('history.noSavedDesc')}
              actionLabel={t('history.searchStandardsBtn')}
              onAction={() => navigate('/search')}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredSaved.map(s => (
                <Card
                  key={s.id || s.is_number}
                  className="p-5 border-[#DDD9D0] bg-white hover:border-[#16294D] transition-colors duration-150 flex flex-col justify-between shadow-2xs"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="font-mono text-xs font-bold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] px-2.5 py-1 rounded">
                        {s.is_number}
                      </span>
                      {s.is_qco_mandatory && (
                        <Badge variant="warning" size="sm">{t('qco.mandatoryRequired')}</Badge>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-[#111111] mb-1.5 leading-snug">
                      {s.title}
                    </h3>
                    <p className="text-xs text-[#5C5A55] mb-4">
                      {s.category || 'General Engineering'}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[#EDEBE5] text-xs">
                    <span className="text-[#8A8580] text-[11px]">
                      {s.saved_date ? `${t('common.date')}: ${s.saved_date}` : ''}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setConfirmId(s.is_number)}
                        className="p-1.5 rounded text-[#8A8580] hover:text-[#A6362C] hover:bg-[#FAEBE9] transition-colors cursor-pointer"
                        title={t('history.remove')}
                      >
                        <Trash2 size={14} />
                      </button>
                      <Link
                        to={`/standard/${encodeURIComponent(s.is_number)}`}
                        className="inline-flex items-center gap-1 font-semibold text-[#16294D] hover:text-[#1E3761] bg-[#F4F3EF] hover:bg-[#E4EDF9] px-2.5 py-1 rounded transition-colors"
                      >
                        <span>{t('dashboard.viewStandard')}</span>
                        <ArrowUpRight size={12} />
                      </Link>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )
        )}

        <div className="mt-6 text-center text-xs text-[#8A8580]">
          <p>{t('history.auditTrailNote')}</p>
        </div>
      </div>

      {confirmId && (
        <ConfirmDialog
          title={t('history.confirmRemoveTitle')}
          message={`${t('history.confirmRemoveMsg')} (${toRemove?.is_number || confirmId})`}
          onConfirm={() => handleRemove(confirmId)}
          onCancel={() => setConfirmId(null)}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

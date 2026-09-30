import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Search, Clock, Bookmark, ShieldCheck,
  ArrowRight, Loader2, Database,
  Calendar, Layers, FileText, ArrowUpRight,
  SlidersHorizontal, Sparkles
} from 'lucide-react'
import Layout from '../components/Layout'
import Card from '../components/Card'
import Badge from '../components/Badge'
import Button from '../components/Button'
import { mockUser } from '../data/mockData'
import { useLang } from '../context/LangContext'
import api from '../services/api'

/* ── Enterprise KPI Card ── */
function MetricCard({ icon: Icon, label, value, subtitle, tag, iconBg, iconColor }) {
  return (
    <div className="rounded-lg p-3.5 sm:p-5 bg-white border border-[#DDD9D0] shadow-2xs flex flex-col justify-between hover:border-[#16294D] transition-colors duration-150">
      <div className="flex items-center justify-between mb-2.5 sm:mb-3">
        <div className={`w-8 h-8 sm:w-9 sm:h-9 rounded-md flex items-center justify-center shrink-0 ${iconBg} ${iconColor}`}>
          <Icon size={17} />
        </div>
        {tag && (
          <span className="text-[10px] font-bold text-[#16294D] bg-[#F4F3EF] border border-[#DDD9D0] rounded px-1.5 sm:px-2 py-0.5">
            {tag}
          </span>
        )}
      </div>
      <div>
        <p className="text-xl sm:text-2xl lg:text-[28px] font-bold text-[#111111] leading-none mb-1 font-sans">{value}</p>
        <p className="text-xs font-semibold text-[#16294D]">{label}</p>
        {subtitle && <p className="text-[10px] sm:text-[11px] text-[#8A8580] mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

// Fallback mock recent searches
const DEFAULT_RECENT_SEARCHES = [
  { id: 1, query: 'LED street light 100W IP65 outdoor', timestamp: '2026-09-27T10:23:00', topResult: 'IS 10322(Part 5/Sec 4):2018', category: 'Electrical' },
  { id: 2, query: 'Portland cement OPC 53 grade', timestamp: '2026-09-26T14:05:00', topResult: 'IS 269:2015', category: 'Construction' },
  { id: 3, query: 'PVC pipe for potable drinking water', timestamp: '2026-09-25T09:45:00', topResult: 'IS 4985:2015', category: 'Piping' },
  { id: 4, query: 'TMT steel reinforcement bar Fe 500D', timestamp: '2026-09-24T16:30:00', topResult: 'IS 1786:2008', category: 'Steel' },
  { id: 5, query: 'Fire detection alarm system building', timestamp: '2026-09-23T11:10:00', topResult: 'IS 2189:2008', category: 'Safety' },
]

// Fallback QCO deadlines
const DEFAULT_QCO_DEADLINES = [
  { product_name: 'LED Street Lighting Luminaires', applicable_is_number: 'IS 10322(Part 5/Sec 4):2018', enforcement_date: '2026-10-01', daysRemaining: 4, status: 'urgent' },
  { product_name: 'Domestic Pressure Cookers', applicable_is_number: 'IS 2347:2018', enforcement_date: '2026-10-15', daysRemaining: 18, status: 'upcoming' },
  { product_name: 'Ordinary Portland Cement (OPC)', applicable_is_number: 'IS 269:2015', enforcement_date: '2023-01-01', daysRemaining: 0, status: 'passed' },
  { product_name: 'Unplasticized PVC Water Pipes', applicable_is_number: 'IS 4985:2015', enforcement_date: '2023-01-01', daysRemaining: 0, status: 'passed' },
  { product_name: 'High Strength Deformed Steel Bars (TMT)', applicable_is_number: 'IS 1786:2008', enforcement_date: '2023-06-01', daysRemaining: 0, status: 'passed' },
]

// Frequently Accessed Standards in BIS Database
const FREQUENT_STANDARDS = [
  { is_number: 'IS 4985:2015', title: 'Unplasticized PVC Pipes for Potable Water Supplies', category: 'Piping & Water', mandatory: true },
  { is_number: 'IS 10322(Part 5/Sec 4):2018', title: 'Luminaires for Road and Street Lighting (IP65)', category: 'Electrical', mandatory: true },
  { is_number: 'IS 269:2015', title: 'Ordinary Portland Cement (OPC 33, 43, 53 Grade)', category: 'Civil & Construction', mandatory: true },
  { is_number: 'IS 1786:2008', title: 'High Strength Deformed Steel Bars for Concrete (TMT)', category: 'Steel & Metallurgy', mandatory: true },
  { is_number: 'IS 456:2000', title: 'Plain and Reinforced Concrete - Code of Practice', category: 'Civil Engineering', mandatory: false },
]

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { t } = useLang()
  const [stats, setStats] = useState(null)
  const [recentSearches, setRecentSearches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getDashboardStats().catch(err => { console.error(err); return null }),
      api.getHistory().catch(err => { console.error(err); return [] }),
    ])
    .then(([statsData, historyData]) => {
      setStats(statsData)
      if (Array.isArray(historyData) && historyData.length > 0) {
        setRecentSearches(historyData.slice(0, 5).map(h => ({
          id: h.id,
          query: h.query,
          timestamp: h.created_at || h.timestamp,
          topResult: h.top_result_is_number || 'Multiple matches',
          category: h.department ? h.department.split('&')[0].trim() : 'General',
        })))
      } else {
        setRecentSearches(DEFAULT_RECENT_SEARCHES)
      }
      setLoading(false)
    })
    .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Layout title={t('navigation.dashboard')}>
        <div className="flex items-center justify-center h-64">
          <Loader2 size={32} className="animate-spin text-[#16294D]" />
        </div>
      </Layout>
    )
  }

  const statStandards = stats?.total_standards ?? 0
  const statQco = stats?.qcoRules ?? stats?.total_qco_rules ?? stats?.qcoDeadlines ?? stats?.qco_deadlines_next_30d ?? 0
  const statSearches = stats?.searchesThisMonth ?? stats?.total_searches_session ?? 0
  const statSaved = stats?.standardsSaved ?? 0

  const deadlineList = stats?.qco_deadline_details?.length > 0
    ? stats.qco_deadline_details.map(d => ({
        product_name: d.product_name,
        applicable_is_number: d.applicable_is_number,
        enforcement_date: d.enforcement_date,
        daysRemaining: d.days_remaining || 15,
        status: (d.days_remaining !== undefined && d.days_remaining <= 15) ? 'urgent' : 'upcoming',
      }))
    : DEFAULT_QCO_DEADLINES

  const todayDateStr = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })

  const renderStatusBadge = (status) => {
    if (status === 'urgent') {
      return <Badge variant="error" size="sm">{t('dashboard.urgentMandate')}</Badge>
    }
    if (status === 'upcoming') {
      return <Badge variant="warning" size="sm">{t('dashboard.upcomingQco')}</Badge>
    }
    return <Badge variant="success" size="sm">{t('dashboard.activelyEnforced')}</Badge>
  }

  return (
    <Layout title={t('navigation.dashboard')}>
      {/* ── Official BIS Hero Banner ── */}
      <div className="rounded-lg bg-[#16294D] px-4 sm:px-6 py-4 sm:py-5 mb-4 sm:mb-6 text-white border border-[#1E3761] shadow-sm relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#F0A500] text-[#16294D] px-2 py-0.5 rounded font-mono">
                {t('dashboard.heroTag')}
              </span>
              <span className="text-[11px] font-medium text-white/70 bg-white/10 px-2 py-0.5 rounded flex items-center gap-1">
                <Calendar size={11} />
                <span>{todayDateStr} · {t('dashboard.catalogActive')}</span>
              </span>
            </div>

            <h1 className="text-lg sm:text-xl md:text-2xl font-bold leading-tight tracking-tight">
              {t('dashboard.welcomeBack')}, {mockUser.name}
            </h1>
            <p className="text-white/75 text-xs sm:text-sm mt-1">
              {mockUser.designation} · <span className="text-white font-medium">{mockUser.department}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="accent"
              size="md"
              onClick={() => navigate('/search')}
              className="gap-2 shrink-0 font-bold shadow-sm"
            >
              <Search size={15} />
              <span>{t('dashboard.evaluateTender')}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* ── KPI Metrics Grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6">
        <MetricCard
          icon={Database}
          label={t('dashboard.indexedStandards')}
          value={statStandards}
          subtitle={t('dashboard.indexedSubtitle')}
          tag={t('dashboard.fullCorpus')}
          iconBg="bg-[#E4EDF9]"
          iconColor="text-[#2155A3]"
        />
        <MetricCard
          icon={ShieldCheck}
          label={t('dashboard.qcoRules')}
          value={statQco}
          subtitle={t('dashboard.qcoSubtitle')}
          tag={t('dashboard.dpiitNotified')}
          iconBg="bg-[#E4F2EE]"
          iconColor="text-[#1F5C4D]"
        />
        <MetricCard
          icon={Search}
          label={t('dashboard.tenderEvals')}
          value={statSearches}
          subtitle={t('dashboard.tenderEvalsSubtitle')}
          tag={t('dashboard.activeSession')}
          iconBg="bg-[#FDF2DC]"
          iconColor="text-[#8A5E0E]"
        />
        <MetricCard
          icon={Bookmark}
          label={t('dashboard.savedStandards')}
          value={statSaved}
          subtitle={t('dashboard.savedSubtitle')}
          tag={t('dashboard.bookmarked')}
          iconBg="bg-[#ECEAF8]"
          iconColor="text-[#3D3A8C]"
        />
      </div>

      {/* ── Quick Action Shortcuts ── */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2.5">
          <SlidersHorizontal size={14} className="text-[#5C5A55]" />
          <h2 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
            {t('dashboard.actionShortcuts')}
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <Link
            to="/search"
            className="p-3.5 rounded-lg bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F4F3EF] transition-all duration-150 shadow-2xs group flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-md bg-[#E4EDF9] text-[#2155A3] flex items-center justify-center shrink-0">
              <Search size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#111111] group-hover:text-[#16294D]">{t('search.title')}</p>
              <p className="text-[11px] text-[#5C5A55] leading-snug">{t('dashboard.searchDesc')}</p>
            </div>
          </Link>

          <Link
            to="/chat"
            className="p-3.5 rounded-lg bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F4F3EF] transition-all duration-150 shadow-2xs group flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-md bg-[#E4F2EE] text-[#1F5C4D] flex items-center justify-center shrink-0">
              <Sparkles size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#111111] group-hover:text-[#16294D]">{t('navigation.askManak')}</p>
              <p className="text-[11px] text-[#5C5A55] leading-snug">{t('dashboard.chatDesc')}</p>
            </div>
          </Link>

          <Link
            to="/document-analysis"
            className="p-3.5 rounded-lg bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F4F3EF] transition-all duration-150 shadow-2xs group flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-md bg-[#ECEAF8] text-[#3D3A8C] flex items-center justify-center shrink-0">
              <FileText size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#111111] group-hover:text-[#16294D]">{t('navigation.docAnalysis')}</p>
              <p className="text-[11px] text-[#5C5A55] leading-snug">{t('dashboard.docAnalysisDesc')}</p>
            </div>
          </Link>

          <Link
            to="/qco-checker"
            className="p-3.5 rounded-lg bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F4F3EF] transition-all duration-150 shadow-2xs group flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-md bg-[#FDF2DC] text-[#8A5E0E] flex items-center justify-center shrink-0">
              <ShieldCheck size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#111111] group-hover:text-[#16294D]">{t('navigation.qcoChecker')}</p>
              <p className="text-[11px] text-[#5C5A55] leading-snug">{t('dashboard.qcoDesc')}</p>
            </div>
          </Link>
        </div>
      </div>

      {/* ── Main Two Column Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6 mb-4 sm:mb-6">
        {/* Left Column: Recent Audit Searches (3 cols) */}
        <div className="lg:col-span-3">
          <div className="flex items-center justify-between mb-2.5">
            <h2 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
              {t('dashboard.recentSearches')}
            </h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/history')} className="text-xs h-7 gap-1">
              <span>{t('dashboard.viewCompleteAudit')}</span>
              <ArrowRight size={12} />
            </Button>
          </div>

          <Card className="overflow-hidden border-[#DDD9D0] bg-white shadow-2xs divide-y divide-[#EDEBE5]">
            {recentSearches.map((s, i) => (
              <div
                key={s.id || i}
                className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[#F4F3EF] transition-colors duration-150"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-7 h-7 rounded bg-[#EDEBE5] flex items-center justify-center shrink-0 text-[#8A8580] mt-0.5">
                    <Clock size={13} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-[#111111] truncate">{s.query}</p>
                    <p className="text-[11px] text-[#5C5A55] mt-0.5 flex items-center gap-1.5 flex-wrap">
                      <span>{t('history.standardCol')}:</span>
                      <span className="font-mono text-[#16294D] font-bold bg-[#E4EDF9] px-1.5 py-0.2 rounded">
                        {s.topResult}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  <span className="text-[11px] text-[#8A8580] hidden sm:inline">{formatDate(s.timestamp)}</span>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-7 text-xs px-2.5"
                    onClick={() => navigate('/results', { state: { query: s.query, reopen: true } })}
                  >
                    {t('history.reopen')}
                  </Button>
                </div>
              </div>
            ))}
          </Card>
        </div>

        {/* Right Column: QCO Deadlines & Regulatory Alerts (2 cols) */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-2.5">
            <h2 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
              {t('dashboard.qcoDeadlines')}
            </h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/qco-checker')} className="text-xs h-7 gap-1">
              <span>{t('dashboard.launchChecker')}</span>
              <ArrowRight size={12} />
            </Button>
          </div>

          <Card className="overflow-hidden border-[#DDD9D0] bg-white shadow-2xs divide-y divide-[#EDEBE5]">
            {deadlineList.map((q, i) => (
              <div
                key={i}
                className="p-3.5 hover:bg-[#F4F3EF] transition-colors duration-150 flex items-start justify-between gap-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-[#111111] truncate">{q.product_name}</p>
                  <p className="text-[11px] font-mono text-[#16294D] mt-0.5">{q.applicable_is_number}</p>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-[#8A8580]">
                    <span>{t('qco.enforcementDate')}:</span>
                    <span className="font-semibold text-[#4B4845]">{q.enforcement_date}</span>
                  </div>
                </div>

                <div className="shrink-0 text-right">
                  {renderStatusBadge(q.status)}
                  {q.daysRemaining !== undefined && q.daysRemaining > 0 && (
                    <p className="text-[10px] text-[#A6362C] font-semibold mt-1">
                      {q.daysRemaining} {t('dashboard.daysRemaining')}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>

      {/* ── Frequently Accessed Standards in Corpus ── */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-[#5C5A55]" />
            <h2 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
              {t('dashboard.frequentStandards')}
            </h2>
          </div>
          <span className="text-[11px] text-[#8A8580]">{t('dashboard.activeCatalog')}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {FREQUENT_STANDARDS.map((std, idx) => (
            <Link
              key={idx}
              to={`/standard/${encodeURIComponent(std.is_number)}`}
              className="p-3.5 rounded-lg bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#FAFAF8] transition-all duration-150 shadow-2xs group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="font-mono text-xs font-bold bg-[#16294D] text-white px-2 py-0.5 rounded">
                    {std.is_number}
                  </span>
                  {std.mandatory ? (
                    <span className="text-[10px] font-bold text-[#1F5C4D] bg-[#E4F2EE] border border-[#A8D5C9] px-1.5 py-0.2 rounded">
                      {t('dashboard.mandatoryBadge')}
                    </span>
                  ) : (
                    <span className="text-[10px] font-medium text-[#4B4845] bg-[#F4F3EF] px-1.5 py-0.2 rounded">
                      {t('dashboard.voluntaryBadge')}
                    </span>
                  )}
                </div>
                <h3 className="text-xs font-bold text-[#111111] group-hover:text-[#16294D] line-clamp-2 leading-snug mb-1">
                  {std.title}
                </h3>
              </div>
              <div className="flex items-center justify-between text-[11px] text-[#8A8580] pt-2 border-t border-[#EDEBE5] mt-2">
                <span>{std.category}</span>
                <span className="text-[#16294D] font-semibold flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                  {t('dashboard.viewStandard')} <ArrowUpRight size={11} />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </Layout>
  )
}

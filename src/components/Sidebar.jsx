import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Search, FileText, ShieldCheck,
  History, Settings, ChevronLeft, ChevronRight, MessageSquare, X
} from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../context/LangContext'

/* ── Inline SVG logo mark ── */
function LogoMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      {/* Hexagon outline */}
      <path
        d="M16 2L28.7 9.5V24.5L16 30L3.3 24.5V9.5L16 2Z"
        fill="#1E3761"
        stroke="#F0A500"
        strokeWidth="1.5"
      />
      {/* MA letters */}
      <text x="6" y="21" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="#F0A500" letterSpacing="-0.5">MA</text>
      {/* Bottom accent line */}
      <line x1="8" y1="24" x2="24" y2="24" stroke="#F0A500" strokeWidth="1" strokeOpacity="0.4" />
    </svg>
  )
}

export default function Sidebar({ mobileOpen = false, onCloseMobile = () => {} }) {
  const [collapsed, setCollapsed] = useState(false)
  const { t } = useLang()

  // Close mobile drawer on Escape key press
  useEffect(() => {
    if (!mobileOpen) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onCloseMobile()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [mobileOpen, onCloseMobile])

  const navItems = [
    { to: '/', label: t('navigation.dashboard'), icon: LayoutDashboard, end: true },
    { to: '/search', label: t('navigation.search'), icon: Search },
    { to: '/chat', label: t('navigation.askManak'), icon: MessageSquare },
    { to: '/document-analysis', label: t('navigation.docAnalysis'), icon: FileText },
    { to: '/qco-checker', label: t('navigation.qcoChecker'), icon: ShieldCheck },
    { to: '/history', label: t('navigation.history'), icon: History },
  ]
  const bottomItems = [
    { to: '/settings', label: t('navigation.settings'), icon: Settings },
  ]

  return (
    <>
      {/* ── Mobile Off-Canvas Drawer (md:hidden) ── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Drawer content */}
          <div className="relative flex flex-col w-[270px] max-w-[85vw] h-full bg-[#16294D] shadow-2xl z-10 animate-drawer">
            {/* Header with Logo and Close Button */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <LogoMark size={32} />
                <div className="min-w-0">
                  <div className="text-[15px] font-semibold text-white leading-tight tracking-tight">MANAK-AI</div>
                  <div className="text-[10px] text-[#F0A500] leading-tight font-medium tracking-wide uppercase truncate">
                    {t('common.portalSubtitle')}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={onCloseMobile}
                className="p-1.5 rounded-md text-white/70 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Close navigation"
              >
                <X size={20} />
              </button>
            </div>

            {/* Navigation items */}
            <nav className="flex-1 py-3 px-2 overflow-y-auto scrollbar-thin" aria-label="Mobile main navigation">
              <div className="px-3 pb-1">
                <span className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.12em]">
                  {t('navigation.navigationSection')}
                </span>
              </div>
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={onCloseMobile}
                  className={({ isActive }) => clsx(
                    'relative flex items-center gap-3 px-3 py-3 rounded-md text-[14px] font-medium transition-colors my-0.5',
                    isActive
                      ? 'text-white bg-white/12 nav-active font-semibold'
                      : 'text-white/70 hover:text-white hover:bg-white/6'
                  )}
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={19} className={clsx('shrink-0', isActive ? 'text-[#F0A500]' : 'text-current')} />
                      <span className="truncate">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}

              <div className="px-3 pt-4 pb-1 mt-2 border-t border-white/8">
                <span className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.12em]">
                  {t('navigation.accountSection')}
                </span>
              </div>
              {bottomItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onCloseMobile}
                  className={({ isActive }) => clsx(
                    'relative flex items-center gap-3 px-3 py-3 rounded-md text-[14px] font-medium transition-colors my-0.5',
                    isActive
                      ? 'text-white bg-white/12 nav-active font-semibold'
                      : 'text-white/70 hover:text-white hover:bg-white/6'
                  )}
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={19} className={clsx('shrink-0', isActive ? 'text-[#F0A500]' : 'text-current')} />
                      <span className="truncate">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>

            {/* Mobile User Identity */}
            <div className="m-3 p-3 rounded-md bg-white/6 border border-white/8">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-[#F0A500] flex items-center justify-center shrink-0">
                  <span className="text-[12px] font-bold text-[#16294D]">RK</span>
                </div>
                <div className="min-w-0">
                  <p className="text-[13px] font-medium text-white truncate">Rajesh Kumar</p>
                  <p className="text-[10px] text-white/50 truncate">Sr. Procurement Officer</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Desktop Sidebar (hidden on mobile, visible on md and up) ── */}
      <aside
        className={clsx(
          'hidden md:flex flex-col shrink-0 h-screen sticky top-0 transition-all duration-200 overflow-hidden',
          'bg-[#16294D]',
          collapsed ? 'w-[60px]' : 'w-[230px]'
        )}
      >

      {/* ── Logo ── */}
      <div className={clsx(
        'flex items-center gap-3 border-b border-white/10',
        collapsed ? 'justify-center px-0 py-4' : 'px-5 py-4'
      )}>
        <LogoMark size={34} />
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-[15px] font-semibold text-white leading-tight tracking-tight">MANAK-AI</div>
            <div className="text-[10px] text-[#F0A500] leading-tight font-medium tracking-wide uppercase truncate">
              {t('common.portalSubtitle')}
            </div>
          </div>
        )}
      </div>

      {/* ── Section label ── */}
      {!collapsed && (
        <div className="px-5 pt-4 pb-1">
          <span className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.12em]">
            {t('navigation.navigationSection')}
          </span>
        </div>
      )}

      {/* ── Nav items ── */}
      <nav className="flex-1 py-2 overflow-y-auto scrollbar-thin" aria-label="Main navigation">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : undefined}
            className={({ isActive }) => clsx(
              'relative flex items-center gap-3 py-2.5 text-[13.5px] font-medium transition-all duration-100',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:ring-inset',
              collapsed ? 'justify-center px-0 mx-1 rounded-md' : 'px-5 mx-0',
              isActive
                ? clsx('text-white nav-active', collapsed ? 'bg-white/12' : 'bg-white/10')
                : 'text-white/60 hover:text-white hover:bg-white/6'
            )}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={18}
                  className={clsx('shrink-0 transition-colors', isActive ? 'text-[#F0A500]' : 'text-current')}
                />
                {!collapsed && <span className="truncate">{label}</span>}
              </>
            )}
          </NavLink>
        ))}

        {!collapsed && (
          <div className="px-5 pt-4 pb-1 mt-2 border-t border-white/8">
            <span className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.12em]">
              {t('navigation.accountSection')}
            </span>
          </div>
        )}
        {collapsed && <div className="mx-3 my-3 border-t border-white/10" />}

        {bottomItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            className={({ isActive }) => clsx(
              'relative flex items-center gap-3 py-2.5 text-[13.5px] font-medium transition-all duration-100',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40',
              collapsed ? 'justify-center px-0 mx-1 rounded-md' : 'px-5 mx-0',
              isActive
                ? clsx('text-white nav-active', collapsed ? 'bg-white/12' : 'bg-white/10')
                : 'text-white/60 hover:text-white hover:bg-white/6'
            )}
          >
            {({ isActive }) => (
              <>
                <Icon size={18} className={clsx('shrink-0', isActive ? 'text-[#F0A500]' : 'text-current')} />
                {!collapsed && <span className="truncate">{label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── User strip ── */}
      {!collapsed && (
        <div className="mx-3 mb-2 p-2.5 rounded-md bg-white/6 border border-white/8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#F0A500] flex items-center justify-center shrink-0">
              <span className="text-[12px] font-bold text-[#16294D]">RK</span>
            </div>
            <div className="min-w-0">
              <p className="text-[13px] font-medium text-white truncate">Rajesh Kumar</p>
              <p className="text-[10px] text-white/50 truncate">Sr. Procurement Officer</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Collapse toggle ── */}
      <button
        type="button"
        onClick={() => setCollapsed(c => !c)}
        className={clsx(
          'flex items-center gap-2 py-3 text-[12px] text-white/50 hover:text-white border-t border-white/10',
          'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white/30 cursor-pointer',
          collapsed ? 'justify-center' : 'px-5'
        )}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={15} /> : <><ChevronLeft size={15} /><span>{t('navigation.collapse')}</span></>}
      </button>
    </aside>
    </>
  )
}

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bell, ChevronDown, LayoutDashboard, History, Settings,
  Globe, Check
} from 'lucide-react'
import { mockUser } from '../data/mockData'
import { useLang, AVAILABLE_LANGUAGES } from '../context/LangContext'

export default function TopBar({ title, breadcrumb }) {
  const { lang, setLang, t } = useLang()
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [isLangOpen, setIsLangOpen] = useState(false)

  const dropdownRef = useRef(null)
  const profileButtonRef = useRef(null)
  const langDropdownRef = useRef(null)
  const langButtonRef = useRef(null)
  const navigate = useNavigate()

  // Close dropdowns on click outside or Escape
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsProfileOpen(false)
      }
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target)) {
        setIsLangOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        if (isProfileOpen) {
          setIsProfileOpen(false)
          profileButtonRef.current?.focus()
        }
        if (isLangOpen) {
          setIsLangOpen(false)
          langButtonRef.current?.focus()
        }
      }
    }

    if (isProfileOpen || isLangOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isProfileOpen, isLangOpen])

  const handleNavigate = (path) => {
    setIsProfileOpen(false)
    navigate(path)
  }

  const handleSelectLang = (code) => {
    setLang(code)
    setIsLangOpen(false)
    langButtonRef.current?.focus()
  }

  // Resolve display title across all 5 languages
  const getDisplayTitle = (rawTitle) => {
    if (!rawTitle) return ''
    const lower = rawTitle.toLowerCase()
    if (lower === 'dashboard') return t('navigation.dashboard')
    if (lower === 'search' || lower === 'search standards') return t('search.title')
    if (lower === 'ask manak-ai' || lower === 'ask manak') return t('navigation.askManak')
    if (lower === 'document analysis' || lower === 'doc analysis') return t('navigation.docAnalysis')
    if (lower === 'qco checker') return t('navigation.qcoChecker')
    if (lower.includes('history') || lower.includes('saved')) return t('navigation.history')
    if (lower.includes('settings')) return t('navigation.settings')
    if (lower.includes('results')) return t('results.title')
    return rawTitle
  }

  const currentLangObj = AVAILABLE_LANGUAGES.find(l => l.code === lang) || AVAILABLE_LANGUAGES[0]

  return (
    <header className="h-[68px] bg-white border-b border-[#E5E7EB] flex items-center justify-between px-6 shrink-0 shadow-xs sticky top-0 z-20">
      {/* ── Left Section: Institutional Page Title & Workspace Label ── */}
      <div className="flex-1 min-w-0 pr-4">
        {breadcrumb ? (
          <div>{breadcrumb}</div>
        ) : (
          <div className="flex flex-col justify-center min-w-0">
            <h2 className="text-base sm:text-lg font-bold text-[#111111] leading-tight tracking-tight truncate">
              {getDisplayTitle(title)}
            </h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#16294D]/60" aria-hidden="true" />
              <p className="text-[11px] font-medium text-[#5C5A55] tracking-wide">
                {t('navigation.workspaceLabel')}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right Section: Language Selector, Notifications, Divider & Officer Profile ── */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {/* Government Portal Accessible Language Selector */}
        <div className="relative" ref={langDropdownRef}>
          <button
            ref={langButtonRef}
            type="button"
            onClick={() => setIsLangOpen(prev => !prev)}
            aria-expanded={isLangOpen}
            aria-haspopup="menu"
            aria-controls="language-menu"
            aria-label={`Language selection. Currently selected: ${currentLangObj.nativeName}`}
            className="h-[36px] px-2.5 sm:px-3 rounded-lg border border-[#DDD9D0] bg-white hover:bg-[#F4F3EF] hover:border-[#16294D] transition-colors flex items-center gap-2 text-xs font-medium text-[#16294D] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer shadow-2xs"
          >
            <Globe size={15} className="text-[#16294D] shrink-0" aria-hidden="true" />
            <span className="font-semibold">{currentLangObj.nativeName}</span>
            <span className="hidden md:inline text-[11px] text-[#8A8580]">({currentLangObj.short})</span>
            <ChevronDown size={13} className={`text-[#8A8580] transition-transform duration-150 ${isLangOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>

          {/* Language Dropdown Menu */}
          {isLangOpen && (
            <div
              id="language-menu"
              role="menu"
              aria-label="Select portal language"
              className="absolute right-0 top-full mt-1.5 w-48 bg-white border border-[#DDD9D0] rounded-lg shadow-elevated py-1.5 z-50 animate-dropdown"
            >
              <div className="px-3 py-1.5 border-b border-[#EDEBE5] mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#8A8580]">
                  {t('settings.preferredLanguage')}
                </span>
              </div>

              {AVAILABLE_LANGUAGES.map((l) => {
                const isSelected = l.code === lang
                return (
                  <button
                    key={l.code}
                    type="button"
                    role="menuitem"
                    onClick={() => handleSelectLang(l.code)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#E4EDF9] text-[#16294D] font-bold'
                        : 'text-[#333333] hover:bg-[#F4F3EF] hover:text-[#111111]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{l.nativeName}</span>
                      <span className="text-[10px] text-[#8A8580] font-normal">({l.englishName})</span>
                    </div>
                    {isSelected && (
                      <Check size={14} className="text-[#16294D] shrink-0" aria-hidden="true" />
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Notification Bell with Badge */}
        <button
          type="button"
          className="relative p-2 rounded-lg text-[#4B4845] hover:text-[#111111] hover:bg-[#F4F3EF] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer"
          aria-label={`3 ${t('navigation.unreadNotifications')}`}
          title={`3 ${t('navigation.unreadNotifications')}`}
        >
          <Bell size={18} />
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#D97706] text-white flex items-center justify-center text-[10px] font-bold leading-none ring-2 ring-white">
            3
          </span>
        </button>

        {/* Vertical Divider (28px height) */}
        <div className="w-px h-7 bg-[#E5E7EB] shrink-0" aria-hidden="true" />

        {/* Officer Profile Section with Dropdown Menu */}
        <div className="relative" ref={dropdownRef}>
          <button
            ref={profileButtonRef}
            type="button"
            onClick={() => setIsProfileOpen(prev => !prev)}
            aria-expanded={isProfileOpen}
            aria-haspopup="menu"
            aria-controls="profile-menu"
            className="flex items-center gap-2.5 sm:gap-3 p-1.5 pr-2 rounded-[10px] hover:bg-[#F4F3EF] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] text-left cursor-pointer group"
            aria-label={`${t('navigation.officerMenu')}: ${mockUser.name}`}
          >
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-[#16294D] border border-[#DDD9D0] flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-[#F0A500] tracking-wider">RK</span>
            </div>

            <div className="hidden sm:block min-w-0">
              <p className="text-xs font-bold text-[#111111] leading-tight truncate">
                {mockUser.name}
              </p>
              <p className="text-[11px] text-[#5C5A55] leading-tight truncate hidden md:block mt-0.5">
                {t('settings.designation')}: {mockUser.designation}
              </p>
            </div>

            <ChevronDown
              size={14}
              className="text-[#8A8580] group-hover:text-[#111111] shrink-0 transition-colors duration-150 ml-0.5"
              aria-hidden="true"
            />
          </button>

          {/* Profile Dropdown Menu */}
          {isProfileOpen && (
            <div
              id="profile-menu"
              role="menu"
              aria-label="User account actions"
              className="absolute right-0 top-full mt-1.5 w-56 bg-white border border-[#DDD9D0] rounded-lg shadow-elevated py-1.5 z-50 animate-dropdown"
            >
              {/* Officer details header */}
              <div className="px-3.5 py-2.5 border-b border-[#E5E7EB] bg-[#FAFAF8] rounded-t-md">
                <p className="text-xs font-bold text-[#111111] truncate">{mockUser.name}</p>
                <p className="text-[11px] text-[#5C5A55] truncate">{mockUser.designation}</p>
                <p className="text-[10px] text-[#8A8580] truncate mt-0.5">{mockUser.department}</p>
              </div>

              {/* Navigation Menu Items */}
              <div className="py-1" role="none">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => handleNavigate('/dashboard')}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-[#16294D] hover:bg-[#F4F3EF] transition-colors duration-150 text-left cursor-pointer focus:outline-none focus-visible:bg-[#F4F3EF]"
                >
                  <LayoutDashboard size={15} className="text-[#5C5A55] shrink-0" />
                  <span>{t('navigation.dashboard')}</span>
                </button>

                <button
                  type="button"
                  role="menuitem"
                  onClick={() => handleNavigate('/history')}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-[#16294D] hover:bg-[#F4F3EF] transition-colors duration-150 text-left cursor-pointer focus:outline-none focus-visible:bg-[#F4F3EF]"
                >
                  <History size={15} className="text-[#5C5A55] shrink-0" />
                  <span>{t('navigation.history')}</span>
                </button>

                <button
                  type="button"
                  role="menuitem"
                  onClick={() => handleNavigate('/settings')}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-[#16294D] hover:bg-[#F4F3EF] transition-colors duration-150 text-left cursor-pointer focus:outline-none focus-visible:bg-[#F4F3EF]"
                >
                  <Settings size={15} className="text-[#5C5A55] shrink-0" />
                  <span>{t('navigation.settings')}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

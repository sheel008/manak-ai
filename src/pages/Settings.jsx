import { useState } from 'react'
import {
  Building2, Bell, Globe, Database,
  CheckCircle2, HardDrive, Type, Eye, Sparkles
} from 'lucide-react'
import Layout from '../components/Layout'
import Card from '../components/Card'
import Button from '../components/Button'
import Toast from '../components/Toast'
import { mockUser } from '../data/mockData'
import { useLang, AVAILABLE_LANGUAGES } from '../context/LangContext'

const DEPARTMENTS = [
  'Ministry of Commerce & Industry',
  'Ministry of Finance',
  'Ministry of Road Transport & Highways',
  'Ministry of Housing & Urban Affairs',
  'Ministry of Power',
  'Ministry of Jal Shakti',
  'Ministry of Defence',
  'Central Public Works Department (CPWD)',
  'National Highways Authority of India (NHAI)',
  'Railways Board',
]

export default function Settings() {
  const { lang, setLang, t, fontSize, setFontSize } = useLang()

  const [form, setForm] = useState(() => {
    try {
      const stored = localStorage.getItem('workspace_settings')
      if (stored) return JSON.parse(stored)
    } catch {}
    return {
      name: mockUser.name,
      department: mockUser.department,
      designation: mockUser.designation,
      email: 'rajesh.kumar@commerce.gov.in',
      responseLang: localStorage.getItem('manak_response_lang') || 'en',
      highContrast: false,
      reducedMotion: false,
      emailNotifications: true,
      qcoAlerts: true,
      amendmentAlerts: true,
    }
  })

  const [toast, setToast] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = () => {
    localStorage.setItem('workspace_settings', JSON.stringify(form))
    localStorage.setItem('manak_response_lang', form.responseLang)
    setToast({ message: t('settings.savedSuccess'), type: 'success' })
  }

  return (
    <Layout title={t('settings.title')}>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-4 sm:mb-6">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold text-[#111111] tracking-tight">
              {t('settings.title')}
            </h1>
            <span className="text-[10px] sm:text-[11px] font-semibold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] px-2 py-0.5 rounded">
              {t('settings.badge')}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#4B4845]">
            {t('settings.subtitle')}
          </p>
        </div>

        {/* 2-Column Enterprise Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Left Column: Officer Identity Card */}
          <div className="lg:col-span-1 space-y-4">
            <Card className="p-4 sm:p-6 border-[#DDD9D0] bg-white shadow-sm text-center">
              {/* Officer Avatar Badge */}
              <div className="w-20 h-20 rounded-full bg-[#16294D] text-[#F0A500] flex items-center justify-center text-2xl font-bold mx-auto mb-3 shadow-md border-2 border-[#DDD9D0]">
                RK
              </div>

              <h2 className="text-base font-bold text-[#111111] leading-snug">{form.name}</h2>
              <p className="text-xs font-semibold text-[#16294D] mt-0.5">{form.designation}</p>
              <p className="text-xs text-[#5C5A55] mt-1">{form.department}</p>

              <div className="mt-4 pt-4 border-t border-[#EDEBE5] space-y-2 text-left">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#8A8580]">{t('settings.authority')}</span>
                  <span className="font-semibold text-[#16294D] bg-[#E4EDF9] px-2 py-0.5 rounded text-[11px]">
                    {t('settings.authorityVal')}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#8A8580]">{t('settings.accessLevel')}</span>
                  <span className="font-semibold text-[#1F5C4D] bg-[#E4F2EE] px-2 py-0.5 rounded text-[11px]">
                    {t('settings.accessLevelVal')}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#8A8580]">{t('common.status')}</span>
                  <span className="font-semibold text-[#1F5C4D] flex items-center gap-1 text-[11px]">
                    <CheckCircle2 size={12} /> {t('settings.statusVal')}
                  </span>
                </div>
              </div>
            </Card>

            {/* BIS System & Registry Facts Card */}
            <Card className="p-4 border-[#DDD9D0] bg-white shadow-2xs text-xs space-y-2.5">
              <div className="flex items-center gap-2 font-bold text-[#16294D] pb-1.5 border-b border-[#EDEBE5]">
                <HardDrive size={15} />
                <span>BIS Knowledge Engine Telemetry</span>
              </div>
              <div className="flex justify-between text-[#5C5A55]">
                <span>Active Corpus:</span>
                <span className="font-semibold text-[#111111]">218 Verified Standards</span>
              </div>
              <div className="flex justify-between text-[#5C5A55]">
                <span>Vector Dimension:</span>
                <span className="font-mono text-[#111111]">768 (pgvector)</span>
              </div>
              <div className="flex justify-between text-[#5C5A55]">
                <span>QCO Rule Sets:</span>
                <span className="font-semibold text-[#111111]">58 Active Orders</span>
              </div>
              <div className="flex justify-between text-[#5C5A55]">
                <span>Supported Locales:</span>
                <span className="font-semibold text-[#16294D]">EN, HI, MR, TA, KN</span>
              </div>
            </Card>
          </div>

          {/* Right Column: Settings Forms */}
          <div className="lg:col-span-2 space-y-5">
            {/* Card 1: Official Credentials */}
            <Card className="p-5 border-[#DDD9D0] bg-white shadow-sm">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-[#EDEBE5]">
                <Building2 size={16} className="text-[#16294D]" />
                <h3 className="text-sm font-bold text-[#111111]">{t('settings.officialDetails')}</h3>
              </div>

              <div className="space-y-3.5">
                <div>
                  <label className="block text-xs font-semibold text-[#111111] mb-1" htmlFor="officer-name">
                    {t('settings.fullName')}
                  </label>
                  <input
                    id="officer-name"
                    type="text"
                    value={form.name}
                    onChange={e => set('name', e.target.value)}
                    className="w-full h-10 px-3 text-xs border border-[#DDD9D0] rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-[#16294D] focus:border-[#16294D]"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  <div>
                    <label className="block text-xs font-semibold text-[#111111] mb-1" htmlFor="dept">
                      {t('settings.department')}
                    </label>
                    <select
                      id="dept"
                      value={form.department}
                      onChange={e => set('department', e.target.value)}
                      className="w-full h-10 px-3 text-xs border border-[#DDD9D0] rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-[#16294D] focus:border-[#16294D]"
                    >
                      {DEPARTMENTS.map(d => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#111111] mb-1" htmlFor="desig">
                      {t('settings.designation')}
                    </label>
                    <input
                      id="desig"
                      type="text"
                      value={form.designation}
                      onChange={e => set('designation', e.target.value)}
                      className="w-full h-10 px-3 text-xs border border-[#DDD9D0] rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-[#16294D] focus:border-[#16294D]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#111111] mb-1" htmlFor="email">
                    {t('settings.email')}
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={e => set('email', e.target.value)}
                    className="w-full h-10 px-3 text-xs border border-[#DDD9D0] rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-[#16294D] focus:border-[#16294D]"
                  />
                </div>
              </div>
            </Card>

            {/* Card 2: Language & Accessibility */}
            <Card className="p-5 border-[#DDD9D0] bg-white shadow-sm">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-[#EDEBE5]">
                <Globe size={16} className="text-[#16294D]" />
                <h3 className="text-sm font-bold text-[#111111]">{t('settings.languageSection')}</h3>
              </div>

              <div className="space-y-4">
                {/* 1. Interface Language Selector */}
                <div>
                  <label className="block text-xs font-semibold text-[#111111] mb-2">
                    {t('settings.preferredLanguage')}
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    {AVAILABLE_LANGUAGES.map((l) => (
                      <button
                        key={l.code}
                        type="button"
                        onClick={() => setLang(l.code)}
                        className={`px-3 py-2 text-xs font-semibold rounded-md border text-center transition-colors cursor-pointer ${
                          lang === l.code
                            ? 'bg-[#16294D] text-white border-[#16294D] shadow-2xs'
                            : 'bg-white text-[#4B4845] border-[#DDD9D0] hover:bg-[#F4F3EF] hover:text-[#111111]'
                        }`}
                      >
                        <span className="block font-medium">{l.nativeName}</span>
                        <span className="text-[10px] opacity-75 font-normal">({l.short})</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 2. AI Response Language */}
                <div className="pt-3 border-t border-[#EDEBE5]">
                  <label className="block text-xs font-semibold text-[#111111] mb-1 flex items-center gap-1.5">
                    <Sparkles size={13} className="text-[#F0A500]" />
                    <span>{t('settings.responseLanguage')}</span>
                  </label>
                  <p className="text-[11px] text-[#5C5A55] mb-2">
                    Select language in which Ask Manak-AI and Document Analysis reports explain standards and QCO rules.
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    {AVAILABLE_LANGUAGES.map((l) => (
                      <button
                        key={l.code}
                        type="button"
                        onClick={() => set('responseLang', l.code)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md border text-center transition-colors cursor-pointer ${
                          form.responseLang === l.code
                            ? 'bg-[#E4F2EE] text-[#1F5C4D] border-[#A8D5C9] font-bold'
                            : 'bg-[#FAFAF8] text-[#5C5A55] border-[#DDD9D0] hover:bg-white'
                        }`}
                      >
                        {l.nativeName}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 3. Font Size selector */}
                <div className="pt-3 border-t border-[#EDEBE5]">
                  <label className="block text-xs font-semibold text-[#111111] mb-1 flex items-center gap-1.5">
                    <Type size={13} className="text-[#16294D]" />
                    <span>{t('settings.fontSize')}</span>
                  </label>
                  <div className="inline-flex rounded-md border border-[#DDD9D0] bg-[#FAFAF8] p-1 gap-1">
                    {[
                      { id: 'standard', label: t('settings.fontStandard') },
                      { id: 'medium', label: t('settings.fontMedium') },
                      { id: 'large', label: t('settings.fontLarge') },
                    ].map(f => (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setFontSize(f.id)}
                        className={`px-3 py-1 text-xs font-semibold rounded transition-colors cursor-pointer ${
                          fontSize === f.id
                            ? 'bg-[#16294D] text-white shadow-2xs'
                            : 'text-[#5C5A55] hover:text-[#111111]'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 4. Accessibility toggles */}
                <div className="pt-3 border-t border-[#EDEBE5] space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-[#111111] flex items-center gap-1.5">
                        <Eye size={13} className="text-[#16294D]" />
                        <span>{t('settings.highContrast')}</span>
                      </p>
                      <p className="text-[11px] text-[#5C5A55]">{t('settings.highContrastDesc')}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={form.highContrast}
                      onChange={e => set('highContrast', e.target.checked)}
                      className="w-4 h-4 rounded text-[#16294D] border-[#DDD9D0] focus:ring-[#16294D] cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-[#111111]">{t('settings.reducedMotion')}</p>
                      <p className="text-[11px] text-[#5C5A55]">{t('settings.reducedMotionDesc')}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={form.reducedMotion}
                      onChange={e => set('reducedMotion', e.target.checked)}
                      className="w-4 h-4 rounded text-[#16294D] border-[#DDD9D0] focus:ring-[#16294D] cursor-pointer"
                    />
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-[#5C5A55]">
                  <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#DDD9D0]">
                    <span className="font-semibold text-[#111111] block mb-0.5">{t('settings.dateConvention')}</span>
                  </div>
                  <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#DDD9D0]">
                    <span className="font-semibold text-[#111111] block mb-0.5">{t('settings.currencyConvention')}</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Card 3: Notification Preferences */}
            <Card className="p-5 border-[#DDD9D0] bg-white shadow-sm">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-[#EDEBE5]">
                <Bell size={16} className="text-[#16294D]" />
                <h3 className="text-sm font-bold text-[#111111]">{t('settings.notificationsSection')}</h3>
              </div>

              <div className="space-y-3.5 divide-y divide-[#EDEBE5]">
                {[
                  {
                    key: 'qcoAlerts',
                    label: t('settings.qcoAlerts'),
                    desc: t('settings.qcoAlertsDesc'),
                  },
                  {
                    key: 'amendAlerts',
                    label: t('settings.amendAlerts'),
                    desc: t('settings.amendAlertsDesc'),
                  },
                  {
                    key: 'emailNotifications',
                    label: t('settings.emailNotif'),
                    desc: t('settings.emailNotifDesc'),
                  },
                ].map((item, idx) => (
                  <div key={item.key} className={`flex items-start justify-between gap-4 ${idx > 0 ? 'pt-3.5' : ''}`}>
                    <div>
                      <p className="text-xs font-semibold text-[#111111]">{item.label}</p>
                      <p className="text-[11px] text-[#5C5A55] leading-relaxed mt-0.5">{item.desc}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={form[item.key]}
                      onChange={e => set(item.key, e.target.checked)}
                      className="w-4 h-4 rounded text-[#16294D] border-[#DDD9D0] focus:ring-[#16294D] mt-0.5 cursor-pointer"
                    />
                  </div>
                ))}
              </div>
            </Card>

            {/* Save Button */}
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="primary" size="md" onClick={handleSave} className="cursor-pointer">
                {t('settings.saveSettings')}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

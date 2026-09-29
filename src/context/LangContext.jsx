import { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'

import enLocale from '../locales/en.json'
import hiLocale from '../locales/hi.json'
import mrLocale from '../locales/mr.json'
import taLocale from '../locales/ta.json'
import knLocale from '../locales/kn.json'

export const AVAILABLE_LANGUAGES = [
  { code: 'en', nativeName: 'English', englishName: 'English', short: 'EN' },
  { code: 'hi', nativeName: 'हिन्दी', englishName: 'Hindi', short: 'HI' },
  { code: 'mr', nativeName: 'मराठी', englishName: 'Marathi', short: 'MR' },
  { code: 'ta', nativeName: 'தமிழ்', englishName: 'Tamil', short: 'TA' },
  { code: 'kn', nativeName: 'ಕನ್ನಡ', englishName: 'Kannada', short: 'KN' },
]

export const LOCALES = {
  en: enLocale,
  hi: hiLocale,
  mr: mrLocale,
  ta: taLocale,
  kn: knLocale,
}

// Flat key aliases for 100% backward-compatibility with v1/v2 callers
const LEGACY_KEY_MAP = {
  // Navigation / Sidebar
  dashboard: 'navigation.dashboard',
  search: 'navigation.search',
  docAnalysis: 'navigation.docAnalysis',
  qcoChecker: 'navigation.qcoChecker',
  history: 'navigation.history',
  settings: 'navigation.settings',
  navigation: 'navigation.navigationSection',
  account: 'navigation.accountSection',
  notifications: 'common.notifications',

  // Dashboard
  welcomeSubtitle: 'common.portalSubtitle',
  welcomeBack: 'dashboard.welcomeBack',
  newSearch: 'search.title',
  searchesMonth: 'dashboard.tenderEvals',
  standardsDb: 'dashboard.indexedStandards',
  qcoDeadlines30: 'dashboard.qcoDeadlines',
  activeQco: 'dashboard.qcoRules',
  recentSearches: 'dashboard.recentSearches',
  qcoDeadlines: 'dashboard.qcoDeadlines',
  viewAll: 'common.viewAll',
  checker: 'navigation.qcoChecker',
  reopen: 'history.reopen',

  // Search page
  searchPageTitle: 'search.title',
  searchHeading: 'search.heading',
  searchSubtitle: 'search.subtitle',
  describeProduct: 'search.describeProduct',
  uploadDocument: 'search.uploadDocument',
  searchPlaceholder: 'search.placeholder',
  searchBtn: 'search.searchBtn',
  matching: 'search.matching',
  tryExample: 'search.tryExample',
  dropHere: 'search.dropHere',
  dropFormats: 'search.dropFormats',
  browseFiles: 'search.browseFiles',
  analyseDoc: 'search.analyseDoc',
  analysing: 'search.analysing',

  // Results page
  resultsFor: 'results.resultsFor',
  newSearchBtn: 'results.newSearch',
  standardsFound: 'results.standardsFound',
  standardFound: 'results.standardFound',
  scoringBreakdown: 'results.scoringBreakdown',
  semanticSim: 'results.semanticSim',
  keywordOverlap: 'results.keywordOverlap',
  specMatch: 'results.specMatch',
  evidence: 'results.evidence',
  matchedSpecs: 'results.matchedSpecs',
  overlapKw: 'results.overlapKw',
  versionAmend: 'results.versionAmend',
  normativeRefs: 'results.normativeRefs',
  relatedStds: 'results.relatedStds',
  certification: 'results.certification',
  openFullStd: 'results.openFullStd',
  accept: 'results.accept',
  reject: 'results.reject',
  flag: 'results.flag',
  noMatchFound: 'results.noMatchFound',
  noMatchDesc: 'results.noMatchDesc',
  tryAnotherSearch: 'results.tryAnotherSearch',

  // QCO Checker
  qcoCheckerTitle: 'qco.title',
  qcoHeading: 'qco.heading',
  qcoSubtitle: 'qco.subtitle',
  qcoPlaceholder: 'qco.placeholder',
  checkBtn: 'qco.checkBtn',
  mandatoryRequired: 'qco.mandatoryRequired',
  mandatoryCoveredUnder: 'qco.mandatoryCovered',
  noMandatoryCert: 'qco.voluntaryNotice',
  noMatchProduct: 'qco.noMatchTitle',
  noMatchProductDesc: 'qco.noMatchDesc',
  product: 'qco.product',
  applicableStandard: 'qco.applicableStandard',
  enforcementDate: 'qco.enforcementDate',
  qcoRef: 'qco.qcoRef',
  sampleProducts: 'qco.sampleProducts',
  qcoDisclaimer: 'qco.disclaimer',

  // Standard Detail
  scope: 'standardDetail.scope',
  testMethods: 'standardDetail.testMethods',
  amendHistory: 'standardDetail.amendHistory',
  qcoStatus: 'standardDetail.qcoStatus',
  intlEquivalent: 'standardDetail.intlEquivalent',
  copyRef: 'standardDetail.copyRef',
  save: 'common.save',
  mandatoryCertification: 'standardDetail.mandatoryCert',
  noMandatoryCertification: 'standardDetail.noMandatoryCert',
  certBody: 'standardDetail.certBody',
  version: 'standardDetail.version',
  lastUpdated: 'standardDetail.lastUpdated',

  // Settings
  settingsTitle: 'settings.title',
  profile: 'settings.officerIdentity',
  fullName: 'settings.fullName',
  department: 'settings.department',
  designation: 'settings.designation',
  languagePref: 'settings.languageSection',
  interfaceLang: 'settings.preferredLanguage',
  notifPref: 'settings.notificationsSection',
  emailNotif: 'settings.emailNotif',
  emailNotifDesc: 'settings.emailNotifDesc',
  qcoAlerts: 'settings.qcoAlerts',
  qcoAlertsDesc: 'settings.qcoAlertsDesc',
  amendAlerts: 'settings.amendAlerts',
  amendAlertsDesc: 'settings.amendAlertsDesc',
  aboutApp: 'common.bisGovLabel',
  saveSettings: 'settings.saveSettings',

  // History
  historyTitle: 'history.title',
  searchHistory: 'history.searchHistoryTab',
  savedStandards: 'history.savedStandardsTab',
  query: 'history.queryCol',
  date: 'history.dateCol',
  topResult: 'history.standardCol',
  results: 'results.title',
  noHistory: 'history.noHistory',
  noHistoryDesc: 'history.noHistoryDesc',
  noSaved: 'history.noSaved',
  noSavedDesc: 'history.noSavedDesc',
  searchStandardsBtn: 'history.searchStandardsBtn',
}

function resolveNestedKey(obj, path) {
  if (!obj || !path) return undefined
  const parts = path.split('.')
  let current = obj
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = current[part]
    } else {
      return undefined
    }
  }
  return typeof current === 'string' ? current : undefined
}

const LangContext = createContext({
  lang: 'en',
  currentLanguage: 'en',
  t: (key) => key,
  setLang: () => {},
  setLanguage: () => {},
  availableLanguages: AVAILABLE_LANGUAGES,
  fontSize: 'standard',
  setFontSize: () => {},
})

export function LangProvider({ children }) {
  // Normalize language code to lowercase: 'en', 'hi', 'mr', 'ta', 'kn'
  const [lang, setLangInternal] = useState(() => {
    try {
      const stored = localStorage.getItem('lang') || 'en'
      const norm = stored.toLowerCase()
      return LOCALES[norm] ? norm : 'en'
    } catch {
      return 'en'
    }
  })

  const [fontSize, setFontSizeState] = useState(() => {
    try {
      return localStorage.getItem('manak_font_size') || 'standard'
    } catch {
      return 'standard'
    }
  })

  const setFontSize = useCallback((size) => {
    setFontSizeState(size)
    try {
      localStorage.setItem('manak_font_size', size)
    } catch {}
  }, [])

  // Sync html lang attribute and font-size class
  useEffect(() => {
    try {
      document.documentElement.lang = lang
      const root = document.documentElement
      root.classList.remove('font-standard', 'font-medium-text', 'font-large-text')
      if (fontSize === 'medium') root.classList.add('font-medium-text')
      else if (fontSize === 'large') root.classList.add('font-large-text')
      else root.classList.add('font-standard')
    } catch {}
  }, [lang, fontSize])

  const setLang = useCallback((newLang) => {
    if (!newLang) return
    const norm = String(newLang).toLowerCase()
    const valid = LOCALES[norm] ? norm : 'en'
    setLangInternal(valid)
    try {
      localStorage.setItem('lang', valid)
    } catch {}
  }, [])

  const t = useCallback((key, params) => {
    if (!key) return ''
    const currentDict = LOCALES[lang] || LOCALES.en
    const fallbackDict = LOCALES.en

    // 1. Direct path lookup in current language
    let text = resolveNestedKey(currentDict, key)

    // 2. Check legacy alias map
    if (!text && LEGACY_KEY_MAP[key]) {
      text = resolveNestedKey(currentDict, LEGACY_KEY_MAP[key])
    }

    // 3. Fallback to English dictionary
    if (!text) {
      text = resolveNestedKey(fallbackDict, key) || (LEGACY_KEY_MAP[key] ? resolveNestedKey(fallbackDict, LEGACY_KEY_MAP[key]) : undefined)
    }

    // 4. Fallback to raw key if not found
    if (text === undefined) {
      text = key
    }

    // 5. Interpolate params if provided: {count}, {name}, etc.
    if (params && typeof params === 'object') {
      return Object.entries(params).reduce((acc, [pKey, pVal]) => {
        return acc.replace(new RegExp(`\\{${pKey}\\}`, 'g'), String(pVal))
      }, text)
    }

    return text
  }, [lang])

  // Uppercase format for backward compatibility where needed (e.g. `lang === 'HI'`)
  const langUpper = useMemo(() => lang.toUpperCase(), [lang])

  const value = useMemo(() => ({
    lang,
    currentLanguage: lang,
    langUpper,
    t,
    setLang,
    setLanguage: setLang,
    availableLanguages: AVAILABLE_LANGUAGES,
    fontSize,
    setFontSize,
  }), [lang, langUpper, t, setLang, fontSize, setFontSize])

  return (
    <LangContext.Provider value={value}>
      {children}
    </LangContext.Provider>
  )
}

export const useLang = () => useContext(LangContext)

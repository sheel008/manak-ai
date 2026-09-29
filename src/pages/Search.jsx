import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search as SearchIcon, Upload, X, FileText, Loader2, Sparkles, ArrowRight, Tag, BookOpen, CheckCircle2, Filter, SlidersHorizontal, ShieldCheck, RotateCcw } from 'lucide-react'
import Layout from '../components/Layout'
import Button from '../components/Button'
import { useLang } from '../context/LangContext'
import Toast from '../components/Toast'
import api from '../services/api'

// Curated procurement autocomplete suggestions based on verified BIS standards
const AUTOCOMPLETE_CATALOG = [
  { text: 'PVC Pipes for Potable Water Supplies', standard: 'IS 4985:2015', category: 'Piping & Water' },
  { text: 'LED Street Light IP65 100W Outdoor Luminaires', standard: 'IS 10322:2018', category: 'Electrical' },
  { text: 'Ordinary Portland Cement OPC 43 and 53 Grade', standard: 'IS 269:2015', category: 'Construction' },
  { text: 'High Strength Deformed Steel Bars TMT Fe 500', standard: 'IS 1786:2008', category: 'Steel' },
  { text: 'Domestic Pressure Cookers Stainless Steel / Aluminium', standard: 'IS 2347:2018', category: 'Consumer' },
  { text: 'Portable Fire Extinguishers Performance Specification', standard: 'IS 15683:2018', category: 'Safety' },
  { text: 'Water Thinned Emulsion Paints Interior / Exterior', standard: 'IS 12062:2021', category: 'Paints' },
  { text: 'PVC Insulated Cables for Working Voltages up to 1100V', standard: 'IS 694:2010', category: 'Electrical' },
  { text: 'Plain and Reinforced Concrete Code of Practice M25', standard: 'IS 456:2000', category: 'Construction' },
  { text: 'Two Wheeler Protective Helmets ISI Mandate', standard: 'IS 16515:2017', category: 'Safety' },
]

const BIS_DEPARTMENTS = [
  { code: '', label: 'All Technical Departments' },
  { code: 'Civil Engineering (CED)', label: 'Civil Engineering (CED)' },
  { code: 'Electrotechnical (ETD)', label: 'Electrotechnical (ETD)' },
  { code: 'Electronics & IT (LITD)', label: 'Electronics & IT (LITD)' },
  { code: 'Mechanical Engineering (MED)', label: 'Mechanical Engineering (MED)' },
  { code: 'Chemical (CHD)', label: 'Chemical (CHD)' },
  { code: 'Food & Agriculture (FAD)', label: 'Food & Agriculture (FAD)' },
  { code: 'Medical Equipment (MHD)', label: 'Medical Equipment (MHD)' },
  { code: 'Transport Engineering (TED)', label: 'Transport Engineering (TED)' },
  { code: 'Textiles (TXD)', label: 'Textiles (TXD)' },
  { code: 'Metallurgical Engineering (MTD)', label: 'Metallurgical Engineering (MTD)' },
  { code: 'Petroleum & Coal (PCD)', label: 'Petroleum & Coal (PCD)' },
  { code: 'Production & General (PGD)', label: 'Production & General (PGD)' },
  { code: 'Water Resources (WRD)', label: 'Water Resources (WRD)' },
  { code: 'Management & Systems (MSD)', label: 'Management & Systems (MSD)' },
]

const BIS_SECTORS = [
  { value: '', label: 'All Industry Sectors' },
  { value: 'Infrastructure & Construction', label: 'Infrastructure & Construction' },
  { value: 'Power & Energy', label: 'Power & Energy' },
  { value: 'Electronics & IT', label: 'Electronics & IT' },
  { value: 'Manufacturing & Machinery', label: 'Manufacturing & Machinery' },
  { value: 'Chemicals & Petrochemicals', label: 'Chemicals & Petrochemicals' },
  { value: 'Food & Agriculture', label: 'Food & Agriculture' },
  { value: 'Healthcare', label: 'Healthcare' },
  { value: 'Automotive', label: 'Automotive' },
  { value: 'Textiles & Apparel', label: 'Textiles & Apparel' },
  { value: 'Heavy Industry', label: 'Heavy Industry' },
  { value: 'Consumer Goods', label: 'Consumer Goods' },
  { value: 'Packaging', label: 'Packaging' },
]

const CATEGORY_EXAMPLES = {
  all: [
    { query: 'LED street light 100W IP65 outdoor', tag: 'Electrical', is: 'IS 10322' },
    { query: 'Portland cement OPC 53 grade', tag: 'Construction', is: 'IS 269' },
    { query: 'Unplasticized PVC pipe for drinking water', tag: 'Piping', is: 'IS 4985' },
    { query: 'TMT steel reinforcement bar Fe 500D', tag: 'Steel', is: 'IS 1786' },
    { query: 'Fire detection and alarm system in building', tag: 'Safety', is: 'IS 2189' },
    { query: 'PVC insulated copper cables 1100V wiring', tag: 'Electrical', is: 'IS 694' },
  ],
  civil: [
    { query: 'Portland cement OPC 53 grade', tag: 'Construction', is: 'IS 269' },
    { query: 'Plain and reinforced concrete design M25', tag: 'Construction', is: 'IS 456' },
    { query: 'Concrete mix proportioning guidelines', tag: 'Construction', is: 'IS 10262' },
  ],
  electrical: [
    { query: 'LED street light 100W IP65 outdoor', tag: 'Electrical', is: 'IS 10322' },
    { query: 'PVC insulated copper cables 1100V wiring', tag: 'Electrical', is: 'IS 694' },
    { query: 'LED modules for general lighting safety', tag: 'Electrical', is: 'IS 16103' },
  ],
  piping: [
    { query: 'Unplasticized PVC pipe for drinking water', tag: 'Piping', is: 'IS 4985' },
    { query: 'CPVC pipes for hot and cold potable water', tag: 'Piping', is: 'IS 15778' },
    { query: 'UPVC pipes for soil and waste discharge inside buildings', tag: 'Piping', is: 'IS 13592' },
  ],
  steel: [
    { query: 'TMT steel reinforcement bar Fe 500D', tag: 'Steel', is: 'IS 1786' },
    { query: 'Hot rolled medium and high tensile structural steel', tag: 'Steel', is: 'IS 2062' },
    { query: 'General construction in steel code of practice', tag: 'Steel', is: 'IS 800' },
  ],
  safety: [
    { query: 'Fire detection and alarm system in building', tag: 'Safety', is: 'IS 2189' },
    { query: 'Portable fire extinguishers performance specification', tag: 'Safety', is: 'IS 15683' },
    { query: 'Two wheeler protective helmets ISI compliance', tag: 'Safety', is: 'IS 16515' },
  ],
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('text')
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [activeCategory, setActiveCategory] = useState('all')
  const [selectedDept, setSelectedDept] = useState('')
  const [selectedSector, setSelectedSector] = useState('')
  const [qcoOnly, setQcoOnly] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const fileRef = useRef(null)
  const searchContainerRef = useRef(null)
  const navigate = useNavigate()
  const { t, lang } = useLang()

  const categories = [
    { id: 'all', label: t('search.allCategories') },
    { id: 'civil', label: t('search.civil') },
    { id: 'electrical', label: t('search.electrical') },
    { id: 'piping', label: t('search.piping') },
    { id: 'steel', label: t('search.steel') },
    { id: 'safety', label: t('search.safety') },
  ]

  const activeFilterCount = (selectedDept ? 1 : 0) + (selectedSector ? 1 : 0) + (qcoOnly ? 1 : 0) + (activeCategory !== 'all' ? 1 : 0)

  const resetFilters = () => {
    setSelectedDept('')
    setSelectedSector('')
    setQcoOnly(false)
    setActiveCategory('all')
  }

  // Filter autocomplete suggestions based on current query
  const suggestions = query.trim().length >= 2
    ? AUTOCOMPLETE_CATALOG.filter(item =>
        item.text.toLowerCase().includes(query.toLowerCase()) ||
        item.standard.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 5)
    : []

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const validateAndSetFile = (f) => {
    if (!f) return
    const validExts = ['.pdf', '.docx', '.txt']
    const name = f.name.toLowerCase()
    const isValid = validExts.some(ext => name.endsWith(ext))
    if (!isValid) {
      setToast({ message: 'Unsupported file format. Please upload a PDF, DOCX, or TXT file.', type: 'error' })
      return
    }
    if (f.size > 15 * 1024 * 1024) {
      setToast({ message: 'File size exceeds maximum limit of 15 MB. Please upload a smaller document.', type: 'error' })
      return
    }
    if (f.size === 0) {
      setToast({ message: 'Selected file is empty (0 bytes). Please upload a valid document.', type: 'error' })
      return
    }
    setFile(f)
  }

  const handleSearch = async (q) => {
    const text = q !== undefined ? q : query
    setShowSuggestions(false)

    if (mode === 'upload') {
      if (!file) {
        setToast({ message: 'Please select a document file (.pdf, .docx, .txt) to upload.', type: 'warning' })
        return
      }
    } else {
      if (!text || !text.trim()) {
        setToast({ message: 'Please enter a product description or specification to search.', type: 'warning' })
        return
      }
    }

    setLoading(true)
    try {
      if (mode === 'upload' && file) {
        const data = await api.searchDocument(file, selectedDept || null)
        navigate('/results', { state: { query: file.name, response: data } })
      } else {
        const extra = {}
        if (selectedSector) extra.sector = selectedSector
        if (qcoOnly) extra.qco_required = true
        if (activeCategory !== 'all') extra.category = activeCategory

        const data = await api.search(text.trim(), selectedDept || null, false, extra)
        navigate('/results', { state: { query: text.trim(), response: data } })
      }
    } catch (err) {
      console.error(err)
      setToast({ message: err.message || 'Search failed. Please try again.', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const currentExamples = CATEGORY_EXAMPLES[activeCategory] || CATEGORY_EXAMPLES.all

  return (
    <Layout title={t('search.title')}>
      <div className="max-w-3xl mx-auto">
        {/* Page heading */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#111111] tracking-tight">
              {t('search.heading')}
            </h1>
            <span className="text-[11px] font-semibold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] px-2 py-0.5 rounded">
              BIS Standard Retrieval
            </span>
          </div>
          <p className="text-sm text-[#4B4845]">
            {t('search.subtitle')}
          </p>
        </div>

        {/* Mode tabs */}
        <div className="flex border-b border-[#DDD9D0] mb-6">
          {[
            { id: 'text', label: t('search.describeProduct') },
            { id: 'upload', label: t('search.uploadDocument') },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => { setMode(tab.id); setFile(null); setShowSuggestions(false); }}
              className={`px-5 py-2.5 text-sm font-semibold border-b-2 -mb-px transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D]
                ${mode === tab.id
                  ? 'border-[#16294D] text-[#16294D] bg-white rounded-t-md'
                  : 'border-transparent text-[#5C5A55] hover:text-[#111111] hover:bg-[#F4F3EF]'}`}
              aria-selected={mode === tab.id}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {mode === 'text' ? (
          <div>
            {/* Search Input Container */}
            <div ref={searchContainerRef} className="relative mb-3">
              <div className="relative flex items-center bg-white border border-[#DDD9D0] rounded-lg shadow-sm focus-within:border-[#16294D] focus-within:ring-2 focus-within:ring-[#16294D]/15 transition-all">
                <SearchIcon size={20} className="ml-4 text-[#8A8580] shrink-0 pointer-events-none" />
                
                <input
                  type="text"
                  value={query}
                  onChange={e => {
                    setQuery(e.target.value)
                    setShowSuggestions(true)
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleSearch()
                    }
                  }}
                  placeholder={t('search.placeholder')}
                  className="w-full h-[52px] pl-3 pr-28 text-[15px] text-[#111111] bg-transparent focus:outline-none placeholder-[#8A8580]"
                  aria-label={t('search.heading')}
                  autoFocus
                />

                {query && (
                  <button
                    type="button"
                    onClick={() => { setQuery(''); setShowSuggestions(false); }}
                    className="p-1.5 text-[#8A8580] hover:text-[#111111] mr-1 focus:outline-none cursor-pointer"
                    aria-label="Clear search"
                  >
                    <X size={16} />
                  </button>
                )}

                <div className="flex items-center gap-1.5 pr-2">
                  <span className="text-[11px] font-bold text-[#4B4845] font-mono bg-[#EDEBE5] px-1.5 py-0.5 rounded uppercase">
                    {lang}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleSearch()}
                    disabled={!query.trim() || loading}
                    className="h-[38px] px-4 text-xs font-semibold bg-[#16294D] hover:bg-[#1E3761] text-white rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-2xs cursor-pointer"
                  >
                    {loading ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        <span>{t('search.matching')}</span>
                      </>
                    ) : (
                      <>
                        <SearchIcon size={14} />
                        <span>{t('common.search')}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Autocomplete Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-20 left-0 right-0 top-full mt-1.5 bg-white border border-[#DDD9D0] rounded-lg shadow-md overflow-hidden animate-dropdown">
                  <div className="px-3.5 py-1.5 bg-[#FAFAF8] border-b border-[#DDD9D0] flex items-center justify-between text-[11px] text-[#5C5A55] font-semibold uppercase tracking-wider">
                    <span>{t('dashboard.frequentStandards')}</span>
                    <span className="font-normal font-sans">Press Enter to Search</span>
                  </div>
                  <div className="divide-y divide-[#EDEBE5]">
                    {suggestions.map((item, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setQuery(item.text)
                          handleSearch(item.text)
                        }}
                        className="w-full text-left px-4 py-2.5 hover:bg-[#F4F3EF] flex items-center justify-between gap-3 text-xs transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <BookOpen size={14} className="text-[#16294D] shrink-0" />
                          <span className="font-medium text-[#111111] truncate">{item.text}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="font-mono text-[11px] font-bold text-[#16294D] bg-[#E4EDF9] px-2 py-0.5 rounded">
                            {item.standard}
                          </span>
                          <span className="text-[10px] text-[#8A8580] hidden sm:inline">{item.category}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Filter Toggle & Controls */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <button
                  type="button"
                  onClick={() => setShowFilters(!showFilters)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#16294D] hover:text-[#1E3761] bg-[#F4F3EF] hover:bg-[#EDEBE5] border border-[#DDD9D0] px-3 py-1.5 rounded-md transition-colors cursor-pointer"
                >
                  <SlidersHorizontal size={13} />
                  <span>Procurement Filters</span>
                  {activeFilterCount > 0 && (
                    <span className="w-4 h-4 rounded-full bg-[#16294D] text-white text-[10px] font-bold inline-flex items-center justify-center">
                      {activeFilterCount}
                    </span>
                  )}
                </button>

                {activeFilterCount > 0 && (
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="inline-flex items-center gap-1 text-[11px] text-[#8A8580] hover:text-[#A6362C] transition-colors cursor-pointer"
                  >
                    <RotateCcw size={11} />
                    <span>Reset filters</span>
                  </button>
                )}
              </div>

              {showFilters && (
                <div className="p-3.5 bg-white border border-[#DDD9D0] rounded-lg shadow-sm mb-4 space-y-3 animate-dropdown">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {/* Department Dropdown */}
                    <div>
                      <label className="block text-[11px] font-bold text-[#5C5A55] uppercase tracking-wider mb-1">
                        BIS Technical Department
                      </label>
                      <select
                        value={selectedDept}
                        onChange={e => setSelectedDept(e.target.value)}
                        className="w-full text-xs bg-[#FAFAF8] border border-[#DDD9D0] rounded p-2 text-[#111111] focus:outline-none focus:border-[#16294D]"
                      >
                        {BIS_DEPARTMENTS.map(d => (
                          <option key={d.code} value={d.code}>{d.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Sector Dropdown */}
                    <div>
                      <label className="block text-[11px] font-bold text-[#5C5A55] uppercase tracking-wider mb-1">
                        Industry Sector
                      </label>
                      <select
                        value={selectedSector}
                        onChange={e => setSelectedSector(e.target.value)}
                        className="w-full text-xs bg-[#FAFAF8] border border-[#DDD9D0] rounded p-2 text-[#111111] focus:outline-none focus:border-[#16294D]"
                      >
                        {BIS_SECTORS.map(s => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* QCO Only Checkbox */}
                  <div className="pt-2 border-t border-[#EDEBE5] flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-[#111111] font-medium">
                      <input
                        type="checkbox"
                        checked={qcoOnly}
                        onChange={e => setQcoOnly(e.target.checked)}
                        className="rounded border-[#DDD9D0] text-[#16294D] focus:ring-[#16294D]"
                      />
                      <ShieldCheck size={14} className={qcoOnly ? "text-[#1F5C4D]" : "text-[#8A8580]"} />
                      <span>Restrict to Mandatory Quality Control Orders (QCO) Only</span>
                    </label>
                    {qcoOnly && (
                      <span className="text-[10px] font-bold text-[#8C2B22] bg-[#FAEBE9] border border-[#E8AFAA] px-2 py-0.5 rounded">
                        Mandatory Filter Active
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Procurement Category Filter Chips */}
            <div className="mb-6">
              <div className="flex items-center gap-1.5 mb-2">
                <Tag size={13} className="text-[#5C5A55]" />
                <span className="text-[11px] font-semibold text-[#5C5A55] uppercase tracking-wider">
                  {t('search.quickFilter')}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {categories.map(cat => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setActiveCategory(cat.id)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer
                      ${activeCategory === cat.id
                        ? 'bg-[#16294D] text-white border-[#16294D] shadow-2xs font-semibold'
                        : 'bg-white text-[#4B4845] border-[#DDD9D0] hover:bg-[#F4F3EF] hover:text-[#111111]'}`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Verified Specification Examples */}
            <div className="bg-white border border-[#DDD9D0] rounded-lg p-5 shadow-sm mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-[#F0A500]" />
                  <h3 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
                    {t('search.tryExample')} ({categories.find(c => c.id === activeCategory)?.label})
                  </h3>
                </div>
                <span className="text-[11px] text-[#8A8580]">{t('dashboard.actionShortcuts')}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {currentExamples.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setQuery(item.query)
                      handleSearch(item.query)
                    }}
                    className="group flex items-center justify-between gap-2.5 p-3 text-xs bg-[#FAFAF8] border border-[#DDD9D0] rounded-md text-left text-[#111111] hover:border-[#16294D] hover:bg-[#F0EEE9] transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#16294D] cursor-pointer"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[10px] font-semibold uppercase text-[#5C5A55] bg-white border border-[#DDD9D0] px-1.5 py-0.2 rounded">
                          {item.tag}
                        </span>
                        <span className="font-mono text-[10px] font-bold text-[#16294D]">{item.is}</span>
                      </div>
                      <p className="font-medium text-[#111111] group-hover:text-[#16294D] truncate">{item.query}</p>
                    </div>
                    <ArrowRight size={13} className="text-[#8A8580] group-hover:text-[#16294D] group-hover:translate-x-0.5 transition-transform shrink-0" />
                  </button>
                ))}
              </div>
            </div>

            {/* Official Guidance Banner */}
            <div className="rounded-lg border border-[#DDD9D0] bg-[#FAFAF8] p-4 text-xs text-[#5C5A55]">
              <div className="flex items-start gap-2.5">
                <CheckCircle2 size={16} className="text-[#2F6F5E] shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-[#111111] font-semibold">Bureau of Indian Standards: </strong>
                  MANAK-AI maps tender parameters (dimensions, electrical ratings, ingress protection, material grades) against the official BIS knowledge corpus. Matches are grounded with verifiable clauses and mandatory Quality Control Order (QCO) statuses.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div>
            {/* Upload Mode */}
            {!file ? (
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => {
                  e.preventDefault()
                  setDragging(false)
                  if (e.dataTransfer.files[0]) validateAndSetFile(e.dataTransfer.files[0])
                }}
                onClick={() => fileRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors duration-150 bg-white
                  ${dragging ? 'border-[#16294D] bg-[#E4EDF9]' : 'border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#FAFAF8]'}`}
              >
                <div className="w-14 h-14 rounded-xl bg-[#EDEBE5] flex items-center justify-center mx-auto mb-3.5 text-[#16294D]">
                  <Upload size={24} />
                </div>
                <h3 className="text-base font-bold text-[#111111] mb-1">{t('search.dropHere')}</h3>
                <p className="text-xs text-[#5C5A55] mb-4">
                  {t('search.subtitle')}
                </p>
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#F4F3EF] border border-[#DDD9D0] rounded text-xs font-semibold text-[#16294D] mb-4">
                  <span>{t('search.dropFormats')}</span>
                </div>
                <div>
                  <Button variant="secondary" size="md" onClick={e => { e.stopPropagation(); fileRef.current?.click() }}>
                    {t('search.browseFiles')}
                  </Button>
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={e => { if (e.target.files[0]) validateAndSetFile(e.target.files[0]) }}
                />
              </div>
            ) : (
              <div className="border border-[#DDD9D0] rounded-lg p-5 bg-white shadow-sm">
                <div className="flex items-center gap-3.5 mb-4">
                  <div className="w-11 h-11 rounded-lg bg-[#E4EDF9] flex items-center justify-center shrink-0">
                    <FileText size={20} className="text-[#2155A3]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-[#111111] truncate">{file.name}</p>
                    <p className="text-xs text-[#8A8580]">{(file.size / 1024).toFixed(1)} KB · {t('common.verified')}</p>
                  </div>
                  <button
                    onClick={() => setFile(null)}
                    className="text-[#8A8580] hover:text-[#A6362C] focus:outline-none p-1.5 rounded hover:bg-[#F4F3EF] cursor-pointer"
                    aria-label="Remove file"
                  >
                    <X size={16} />
                  </button>
                </div>
                <Button variant="primary" size="lg" className="w-full" onClick={() => handleSearch()} disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>{t('search.analysing')}</span>
                    </>
                  ) : (
                    <span>{t('search.analyseDoc')}</span>
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

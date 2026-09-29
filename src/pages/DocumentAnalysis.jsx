import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileText, X, Loader2, CheckCircle2, AlertTriangle,
  Cpu, Award, ShieldCheck, FileSpreadsheet, ArrowRight
} from 'lucide-react'
import Layout from '../components/Layout'
import Card from '../components/Card'
import Button from '../components/Button'
import Badge from '../components/Badge'
import Toast from '../components/Toast'
import { useLang } from '../context/LangContext'
import api from '../services/api'

export default function DocumentAnalysis() {
  const { t } = useLang()
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [step, setStep] = useState('idle') // idle | processing | done
  const [progressStage, setProgressStage] = useState(0)
  const [extractedSpecs, setExtractedSpecs] = useState([])
  const [fullResponse, setFullResponse] = useState(null)
  const [toast, setToast] = useState(null)
  const fileRef = useRef()
  const navigate = useNavigate()

  const handleFile = (f) => {
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
    setStep('idle')
    setFullResponse(null)
    setExtractedSpecs([])
  }

  const handleAnalyse = async () => {
    if (!file) return
    setStep('processing')
    setProgressStage(1)

    const stageTimer1 = setTimeout(() => setProgressStage(2), 700)
    const stageTimer2 = setTimeout(() => setProgressStage(3), 1500)

    try {
      const data = await api.searchDocument(file)
      clearTimeout(stageTimer1)
      clearTimeout(stageTimer2)
      setProgressStage(4)
      setFullResponse(data)
      const matched = data.results?.[0]?.evidence?.matched_specifications || []
      setExtractedSpecs(matched)
      setStep('done')
    } catch (err) {
      clearTimeout(stageTimer1)
      clearTimeout(stageTimer2)
      console.error(err)
      setToast({ message: err.message || 'Failed to process document.', type: 'error' })
      setStep('idle')
    }
  }

  const handleSearch = () => {
    navigate('/results', { state: { query: file.name, response: fullResponse } })
  }

  return (
    <Layout title={t('docAnalysis.title')}>
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#111111] tracking-tight">
              {t('docAnalysis.heading')}
            </h1>
            <span className="text-[11px] font-semibold text-[#16294D] bg-[#E4EDF9] border border-[#A8C2E8] px-2 py-0.5 rounded">
              {t('docAnalysis.badge')}
            </span>
          </div>
          <p className="text-sm text-[#4B4845]">
            {t('docAnalysis.subtitle')}
          </p>
        </div>

        {/* Dropzone & File Status Card */}
        <div className="mb-8">
          {!file ? (
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => {
                e.preventDefault()
                setDragging(false)
                if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
              }}
              onClick={() => fileRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors duration-150 bg-white
                ${dragging ? 'border-[#16294D] bg-[#E4EDF9]' : 'border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#FAFAF8]'}`}
            >
              <div className="w-14 h-14 rounded-xl bg-[#EDEBE5] flex items-center justify-center mx-auto mb-3.5 text-[#16294D]">
                <Upload size={24} />
              </div>
              <h3 className="text-base font-bold text-[#111111] mb-1">{t('docAnalysis.dragDrop')}</h3>
              <p className="text-xs text-[#5C5A55] mb-4">
                {t('docAnalysis.fileSizeNote')}
              </p>
              <div>
                <Button variant="secondary" size="md" onClick={e => { e.stopPropagation(); fileRef.current?.click() }}>
                  {t('docAnalysis.browseFileBtn')}
                </Button>
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={e => { if (e.target.files[0]) handleFile(e.target.files[0]) }}
              />
            </div>
          ) : (
            <div className="space-y-4">
              <Card className="p-4 border-[#DDD9D0] bg-white shadow-2xs">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-[#E4EDF9] flex items-center justify-center shrink-0">
                      <FileText size={20} className="text-[#2155A3]" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-[#111111] truncate">{file.name}</p>
                      <p className="text-xs text-[#8A8580]">
                        {(file.size / 1024).toFixed(1)} KB · {t('docAnalysis.selectedDoc')}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => { setFile(null); setStep('idle'); setFullResponse(null) }}
                    className="p-1.5 rounded text-[#5C5A55] hover:text-[#A6362C] hover:bg-[#FAEBE9] transition-colors cursor-pointer"
                    aria-label="Remove file"
                  >
                    <X size={16} />
                  </button>
                </div>
              </Card>

              {step === 'idle' && (
                <Button variant="primary" size="lg" className="w-full justify-center h-[46px] shadow-sm cursor-pointer" onClick={handleAnalyse}>
                  {t('docAnalysis.startAnalysis')}
                </Button>
              )}

              {step === 'processing' && (
                <Card className="p-6 border-[#DDD9D0] bg-white shadow-sm">
                  <div className="flex items-center justify-center gap-2.5 mb-3 text-[#16294D]">
                    <Loader2 size={20} className="animate-spin text-[#16294D]" />
                    <span className="text-sm font-bold text-[#111111]">{t('docAnalysis.analysingHeader')}</span>
                  </div>

                  {/* Multi-stage Progress Indicators */}
                  <div className="space-y-2 max-w-md mx-auto mt-4 text-xs">
                    <div className="flex items-center justify-between text-[#5C5A55]">
                      <span className={progressStage >= 1 ? 'font-semibold text-[#16294D]' : ''}>{t('docAnalysis.stage1')}</span>
                      {progressStage >= 1 && <CheckCircle2 size={13} className="text-[#2F6F5E]" />}
                    </div>
                    <div className="flex items-center justify-between text-[#5C5A55]">
                      <span className={progressStage >= 2 ? 'font-semibold text-[#16294D]' : ''}>{t('docAnalysis.stage2')}</span>
                      {progressStage >= 2 && <CheckCircle2 size={13} className="text-[#2F6F5E]" />}
                    </div>
                    <div className="flex items-center justify-between text-[#5C5A55]">
                      <span className={progressStage >= 3 ? 'font-semibold text-[#16294D]' : ''}>{t('docAnalysis.stage3')}</span>
                      {progressStage >= 3 && <CheckCircle2 size={13} className="text-[#2F6F5E]" />}
                    </div>
                    <div className="flex items-center justify-between text-[#5C5A55]">
                      <span className={progressStage >= 4 ? 'font-semibold text-[#16294D]' : ''}>{t('docAnalysis.stage4')}</span>
                      {progressStage >= 4 && <CheckCircle2 size={13} className="text-[#2F6F5E]" />}
                    </div>
                  </div>
                </Card>
              )}

              {step === 'done' && (
                <div>
                  <Card className="p-5 mb-4 border-[#DDD9D0] bg-white shadow-sm">
                    {fullResponse?.abstained ? (
                      <div className="flex items-start gap-3">
                        <AlertTriangle size={20} className="text-[#B8862B] shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-semibold text-[#111111] mb-1">{t('docAnalysis.lowConfidence')}</p>
                          <p className="text-xs text-[#5C5A55] leading-relaxed">
                            {fullResponse.abstention_reason || t('results.noMatchDesc')}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between gap-2 mb-4 pb-3 border-b border-[#EDEBE5]">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 size={18} className="text-[#2F6F5E]" />
                            <h3 className="text-sm font-bold text-[#111111]">
                              {t('docAnalysis.analysisComplete')} — {extractedSpecs.length} {t('docAnalysis.specsIdentified')}
                            </h3>
                          </div>
                          <span className="text-[11px] font-semibold text-[#1F5C4D] bg-[#E4F2EE] border border-[#A8D5C9] px-2 py-0.5 rounded">
                            {t('docAnalysis.verifiedMatch')}
                          </span>
                        </div>

                        {extractedSpecs.length > 0 ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
                            {extractedSpecs.map((item, i) => {
                              const label = typeof item === 'string'
                                ? item
                                : (item.query && item.matched ? `${item.query} (${item.matched})` : item.value || item.stored || item.query || JSON.stringify(item))
                              return (
                                <div key={i} className="flex items-center justify-between gap-2 text-xs p-2.5 rounded-md bg-[#FAFAF8] border border-[#DDD9D0]">
                                  <span className="text-[#111111] font-medium truncate">{label}</span>
                                  <Badge variant="success" size="sm">{t('docAnalysis.extracted')}</Badge>
                                </div>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="text-xs text-[#5C5A55] bg-[#FAFAF8] p-3 rounded border border-[#DDD9D0] mb-4">
                            {t('docAnalysis.noExplicitSpecs')}
                          </p>
                        )}

                        {/* Procurement Analysis Report Summary */}
                        {fullResponse?.results && fullResponse.results.length > 0 && (
                          <div className="pt-3 border-t border-[#EDEBE5]">
                            <h4 className="text-xs font-bold text-[#16294D] uppercase tracking-wider mb-2.5 flex items-center justify-between">
                              <span>Identified BIS Standards ({fullResponse.results.length})</span>
                              <span className="text-[11px] font-normal text-[#5C5A55]">Top Candidates Ranked</span>
                            </h4>
                            <div className="space-y-2 mb-3">
                              {fullResponse.results.slice(0, 3).map((std, idx) => (
                                <div key={idx} className="p-3 bg-[#FAFAF8] border border-[#DDD9D0] rounded-md">
                                  <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1.5">
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-mono text-xs font-bold text-[#16294D] bg-[#E4EDF9] px-2 py-0.5 rounded">
                                        {std.is_number}
                                      </span>
                                      {std.department && (
                                        <span className="text-[10px] text-[#4B4845] bg-white border border-[#DDD9D0] px-1.5 py-0.5 rounded font-medium">
                                          {std.department}
                                        </span>
                                      )}
                                      {(std.is_qco_mandatory || std.qco_required) && (
                                        <span className="text-[10px] font-bold text-[#8C2B22] bg-[#FAEBE9] border border-[#E8AFAA] px-1.5 py-0.5 rounded">
                                          QCO Mandatory
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-xs font-bold text-[#1F5C4D]">
                                      {std.confidence || Math.round((std.score || 0) * 100)}% Match
                                    </span>
                                  </div>
                                  <p className="text-xs font-semibold text-[#111111] line-clamp-1">{std.title}</p>
                                  {std.why_recommended && (
                                    <p className="text-[11px] text-[#5C5A55] mt-1 line-clamp-2">
                                      <strong>Justification: </strong>{std.why_recommended}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </Card>

                  <Button variant="primary" size="lg" className="w-full justify-center h-[46px] shadow-sm flex items-center gap-2 cursor-pointer" onClick={handleSearch}>
                    <span>{fullResponse?.abstained ? t('docAnalysis.viewDetails') : `${t('docAnalysis.viewMatching')} (${fullResponse?.results?.length || 0})`}</span>
                    <ArrowRight size={15} />
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 4 Informational Enterprise Workflow Cards */}
        <div className="pt-2">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-xs font-bold text-[#16294D] uppercase tracking-wider">
              {t('docAnalysis.capabilitiesHeading')}
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Card 1: Extract Specifications */}
            <div className="p-4 rounded-lg bg-white border border-[#DDD9D0] shadow-2xs">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-md bg-[#E4EDF9] text-[#2155A3] flex items-center justify-center shrink-0">
                  <Cpu size={16} />
                </div>
                <h4 className="text-xs font-bold text-[#111111]">{t('docAnalysis.cap1Title')}</h4>
              </div>
              <p className="text-xs text-[#5C5A55] leading-relaxed">
                {t('docAnalysis.cap1Desc')}
              </p>
            </div>

            {/* Card 2: Match BIS Standards */}
            <div className="p-4 rounded-lg bg-white border border-[#DDD9D0] shadow-2xs">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-md bg-[#ECEAF8] text-[#3D3A8C] flex items-center justify-center shrink-0">
                  <Award size={16} />
                </div>
                <h4 className="text-xs font-bold text-[#111111]">{t('docAnalysis.cap2Title')}</h4>
              </div>
              <p className="text-xs text-[#5C5A55] leading-relaxed">
                {t('docAnalysis.cap2Desc')}
              </p>
            </div>

            {/* Card 3: Identify QCO Mandates */}
            <div className="p-4 rounded-lg bg-white border border-[#DDD9D0] shadow-2xs">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-md bg-[#E4F2EE] text-[#1F5C4D] flex items-center justify-center shrink-0">
                  <ShieldCheck size={16} />
                </div>
                <h4 className="text-xs font-bold text-[#111111]">{t('docAnalysis.cap3Title')}</h4>
              </div>
              <p className="text-xs text-[#5C5A55] leading-relaxed">
                {t('docAnalysis.cap3Desc')}
              </p>
            </div>

            {/* Card 4: Generate Procurement Report */}
            <div className="p-4 rounded-lg bg-white border border-[#DDD9D0] shadow-2xs">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-md bg-[#FDF2DC] text-[#8A5E0E] flex items-center justify-center shrink-0">
                  <FileSpreadsheet size={16} />
                </div>
                <h4 className="text-xs font-bold text-[#111111]">{t('docAnalysis.cap4Title')}</h4>
              </div>
              <p className="text-xs text-[#5C5A55] leading-relaxed">
                {t('docAnalysis.cap4Desc')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </Layout>
  )
}

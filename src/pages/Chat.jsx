import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, Sparkles, RotateCcw, ShieldCheck } from 'lucide-react';
import Layout from '../components/Layout';
import Card from '../components/Card';
import Button from '../components/Button';
import ChatMessage from '../components/ChatMessage';
import TypingIndicator from '../components/TypingIndicator';
import { useLang } from '../context/LangContext';
import api from '../services/api';

const MULTILINGUAL_SUGGESTIONS = {
  en: [
    'Find BIS standard for PVC pipes.',
    'Is ISI mandatory for helmets?',
    'Explain IS 456:2000.',
    'Which standard applies to LED street lights?',
    'Find QCO for Pressure Cooker.',
    'Find BIS standard for TMT Steel Bars.',
  ],
  hi: [
    'PVC पाइप के लिए BIS मानक खोजें।',
    'क्या हेलमेट के लिए ISI अनिवार्य है?',
    'IS 456:2000 समझाएं।',
    'LED स्ट्रीट लाइट पर कौन सा मानक लागू होता है?',
    'प्रेशर कुकर के लिए QCO खोजें।',
    'TMT स्टील बार के लिए BIS मानक खोजें।',
  ],
  mr: [
    'PVC पाईपसाठी BIS मानक शोधा.',
    'हेल्मेटसाठी ISI सक्तीचे आहे का?',
    'IS 456:2000 स्पष्ट करा.',
    'LED स्ट्रीट लाइटवर कोणते मानक लागू होते?',
    'प्रेशर कुकरसाठी QCO शोधा.',
    'TMT स्टील बारसाठी BIS मानक शोधा.',
  ],
  ta: [
    'PVC குழாய்களுக்கான BIS தரநிலையைக் கண்டறியவும்.',
    'ஹெல்மெட்டுகளுக்கு ISI கட்டாயமா?',
    'IS 456:2000 விளக்குங்கள்.',
    'LED தெரு விளக்குகளுக்கு எந்தத் தரம் பொருந்தும்?',
    'பிரஷர் குக்கருக்கான QCO ஐக் கண்டறியவும்.',
    'TMT ஸ்டீல் கம்பிகளுக்கான BIS தரநிலையைக் கண்டறியவும்.',
  ],
  kn: [
    'PVC ಪೈಪ್‌ಗಳಿಗಾಗಿ BIS ಗುಣಮಟ್ಟವನ್ನು ಹುಡುಕಿ.',
    'ಹೆಲ್ಮೆಟ್‌ಗಳಿಗೆ ISI ಕಡ್ಡಾಯವೇ?',
    'IS 456:2000 ವಿವರಿಸಿ.',
    'LED ಬೀದಿ ದೀಪಗಳಿಗೆ ಯಾವ ಗುಣಮಟ್ಟ ಅನ್ವಯಿಸುತ್ತದೆ?',
    'ಪ್ರೆಶರ್ ಕುಕ್ಕರ್‌ಗಾಗಿ QCO ಹುಡುಕಿ.',
    'TMT ಸ್ಟೀಲ್ ಬಾರ್‌ಗಳಿಗಾಗಿ BIS ಗುಣಮಟ್ಟವನ್ನು ಹುಡುಕಿ.',
  ],
};

export default function Chat() {
  const { t, lang } = useLang();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [savedStandards, setSavedStandards] = useState(new Set());
  const queryCache = useRef(new Map());
  const endRef = useRef(null);

  // Load existing bookmarks to show correct saved state
  useEffect(() => {
    let isMounted = true;
    api.getSaved()
      .then(res => {
        if (isMounted && res) {
          const items = Array.isArray(res) ? res : (res.saved_items || []);
          const s = new Set(items.map(item => item.is_number));
          setSavedStandards(s);
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, []);

  // Smooth scroll on new message or typing state
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSaveStandard = useCallback(async (isNumber) => {
    if (!isNumber) return;
    try {
      if (savedStandards.has(isNumber)) {
        await api.deleteSaved(isNumber);
        setSavedStandards(prev => {
          const next = new Set(prev);
          next.delete(isNumber);
          return next;
        });
      } else {
        await api.saveStandard(isNumber);
        setSavedStandards(prev => new Set(prev).add(isNumber));
      }
    } catch (err) {
      console.error('Failed to update bookmark:', err);
    }
  }, [savedStandards]);

  const sendMessage = async (textToSend) => {
    const userQuery = (textToSend || input).trim();
    if (!userQuery || loading) return;

    setInput('');

    // Append user message
    const newMessages = [...messages, { role: 'user', content: userQuery }];
    setMessages(newMessages);
    setLoading(true);

    // Extract last 5 messages for conversation context
    const historyPayload = newMessages.slice(-5).map(m => ({
      role: m.role,
      content: m.content || m.answer || '',
    }));

    // Cache check for identical query in session with language
    const cacheKey = `${userQuery.toLowerCase()}_${sessionId}_${lang}`;
    if (queryCache.current.has(cacheKey)) {
      const cached = queryCache.current.get(cacheKey);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: cached.answer || cached.message,
        recommendations: cached.recommendations || [],
        qco: cached.qco || null,
        related_standards: cached.related_standards || [],
        evidence: cached.evidence || [],
        follow_up: cached.follow_up || [],
      }]);
      setLoading(false);
      return;
    }

    try {
      const data = await api.sendChatMessage(userQuery, sessionId, historyPayload, lang);

      if (data.sessionId && !sessionId) {
        setSessionId(data.sessionId);
      }

      // Store in session cache
      queryCache.current.set(cacheKey, data);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || data.message,
        recommendations: data.recommendations || [],
        qco: data.qco || null,
        related_standards: data.related_standards || [],
        evidence: data.evidence || [],
        follow_up: data.follow_up || [],
      }]);
    } catch (err) {
      console.error('Chat error:', err);
      const suggestions = MULTILINGUAL_SUGGESTIONS[lang] || MULTILINGUAL_SUGGESTIONS.en;
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: t('chat.errorConnecting'),
        error: err.message || 'Network request failed',
        follow_up: suggestions.slice(0, 3),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleResetSession = () => {
    setMessages([]);
    setSessionId('');
    setInput('');
  };

  const currentSuggestions = MULTILINGUAL_SUGGESTIONS[lang] || MULTILINGUAL_SUGGESTIONS.en;

  return (
    <Layout title={t('chat.title')}>
      <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-130px)]">
        {/* Header bar */}
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl md:text-2xl font-bold text-[#111111]">{t('chat.title')}</h1>
              <span className="text-[11px] font-bold uppercase tracking-wider bg-[#E4F2EE] text-[#1F5C4D] border border-[#A8D5C9] px-2 py-0.5 rounded">
                {t('chat.copilotBadge')}
              </span>
            </div>
            <p className="text-xs text-[#5C5A55]">
              {t('chat.description')}
            </p>
          </div>

          {messages.length > 0 && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleResetSession}
              className="gap-1.5 text-xs text-[#4B4845] cursor-pointer"
            >
              <RotateCcw size={13} />
              <span>{t('chat.newSession')}</span>
            </Button>
          )}
        </div>

        {/* Chat Main Card */}
        <Card className="flex-1 flex flex-col overflow-hidden bg-[#FAFAF8] border border-[#DDD9D0] shadow-sm">
          {/* Scrollable messages container */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {/* Compact Welcome Hero & Quick Suggestion Chips (shown when no messages yet) */}
            {messages.length === 0 && (
              <div className="py-4 flex flex-col items-center text-center max-w-xl mx-auto">
                <div className="w-10 h-10 rounded-lg bg-[#16294D] text-[#F0A500] flex items-center justify-center mb-2.5 shadow-2xs">
                  <Bot size={22} />
                </div>
                <h2 className="text-base font-bold text-[#111111] mb-1">
                  {t('chat.welcomeHeading')}
                </h2>
                <p className="text-xs text-[#5C5A55] mb-4 leading-relaxed max-w-md">
                  {t('chat.welcomeSub')}
                </p>

                <div className="w-full text-left">
                  <div className="flex items-center gap-1.5 mb-2 px-1">
                    <Sparkles size={13} className="text-[#F0A500]" />
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#4B4845]">
                      {t('chat.suggestedInquiries')}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {currentSuggestions.map((chip, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => sendMessage(chip)}
                        className="text-left p-2.5 rounded-md bg-white border border-[#DDD9D0] hover:border-[#16294D] hover:bg-[#F4F3EF] transition-all duration-150 text-xs font-medium text-[#111111] shadow-2xs group flex items-center justify-between cursor-pointer"
                      >
                        <span className="truncate pr-2">{chip}</span>
                        <Send size={11} className="text-[#8A8580] group-hover:text-[#16294D] group-hover:translate-x-0.5 transition-transform shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-5 flex items-center gap-1.5 text-[11px] text-[#5C5A55] bg-[#EDEBE5] px-3 py-1 rounded-md">
                  <ShieldCheck size={13} className="text-[#2F6F5E]" />
                  <span>{t('chat.zeroHallucination')}</span>
                </div>
              </div>
            )}

            {/* Chat conversation messages */}
            {messages.map((msg, idx) => (
              <ChatMessage
                key={idx}
                message={msg}
                onSelectQuestion={(q) => sendMessage(q)}
                onSaveStandard={handleSaveStandard}
                savedStandards={savedStandards}
              />
            ))}

            {/* Typing Indicator */}
            {loading && <TypingIndicator />}

            <div ref={endRef} />
          </div>

          {/* Chat Input Dock */}
          <div className="p-3 md:p-4 bg-white border-t border-[#DDD9D0]">
            <form onSubmit={handleFormSubmit} className="relative flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('chat.inputPlaceholder')}
                disabled={loading}
                className="w-full h-11 pl-4 pr-14 text-xs md:text-sm bg-[#FAFAF8] border border-[#DDD9D0] rounded-lg focus:outline-none focus:border-[#16294D] focus:ring-1 focus:ring-[#16294D] placeholder-[#8A8580] text-[#111111]"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="absolute right-1.5 h-8 w-10 bg-[#16294D] hover:bg-[#1E3761] disabled:opacity-40 disabled:hover:bg-[#16294D] text-white rounded-md flex items-center justify-center transition-colors cursor-pointer"
                aria-label="Send query"
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        </Card>
      </div>
    </Layout>
  );
}

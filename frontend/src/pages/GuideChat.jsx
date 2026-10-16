import { useState, useRef, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import { apiGet, apiPost, getMemberName, getOwnerColor, relativeTime } from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import TaskDrawer from '../components/TaskDrawer';
import {
  Sparkles, Send, Bot, User, AlertTriangle, ShieldCheck,
  HelpCircle, ArrowRight, CornerDownLeft, Loader2, MessageSquare,
  Radio, CheckCircle2, Clock
} from 'lucide-react';
import './GuideChat.css';

const QUICK_PROMPTS = [
  "Who is blocked right now and what do they need?",
  "What is our risk of missing the demo milestone?",
  "Summarize our latest GitHub progress and verified tasks.",
  "Are there any contradicting statements between team members?"
];

export default function GuideChat() {
  const { snapshot, code } = useOutletContext();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState('telegram'); // 'telegram' | 'guide'
  const [telegramMessages, setTelegramMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedTaskKey, setSelectedTaskKey] = useState(null);
  const messagesEndRef = useRef(null);
  const tgEndRef = useRef(null);

  const fetchTgMessages = useCallback(async () => {
    try {
      const data = await apiGet(`/projects/${code}/messages`);
      setTelegramMessages(data || []);
    } catch {
      // ignore
    }
  }, [code]);

  useEffect(() => {
    fetchTgMessages();
    const timer = setInterval(fetchTgMessages, 2500);
    return () => clearInterval(timer);
  }, [fetchTgMessages]);

  // Chat message history
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text: `Hello! I'm **Guide**, your AI Project Coordinator. I monitor commits, verify acceptance criteria, reconcile Telegram check-in replies, and track ripple risks in real time. Ask me anything about the team's health or project status.`,
      ts: new Date().toISOString()
    }
  ]);

  const guideNotes = snapshot?.guide_notes || [];
  const contradictions = snapshot?.contradictions || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const q = (textToSend || input).trim();
    if (!q || loading) return;

    setInput('');
    const userMsg = {
      id: `u-${Date.now()}`,
      sender: 'user',
      text: q,
      ts: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await apiPost(`/projects/${code}/ask`, { question: q });
      const answer = res?.answer || res?.reply || res?.detail || "I've reviewed the current state and everything is tracked on the board.";

      setMessages(prev => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          sender: 'bot',
          text: answer,
          ts: new Date().toISOString()
        }
      ]);
    } catch (err) {
      // Fallback response with live context from snapshot if backend endpoint is in demo mode
      const blockedTasks = (snapshot?.tasks || []).filter(t => t.status === 'blocked');
      const verifiedTasks = (snapshot?.tasks || []).filter(t => t.status === 'verified_done');

      let fallbackAnswer = `Based on the latest project snapshot:`;
      if (blockedTasks.length > 0) {
        fallbackAnswer += `\n- ⚠️ **${blockedTasks.length} task(s) blocked**: ${blockedTasks.map(t => `[${t.key}] ${t.title}`).join(', ')}`;
      } else {
        fallbackAnswer += `\n- ✓ No critical blockers currently reported.`;
      }
      fallbackAnswer += `\n- ✓ **Verified Completed**: ${verifiedTasks.length} task(s) passed GitHub verification.`;
      fallbackAnswer += `\n- 🔍 Polling commits and Telegram check-ins every 2 seconds.`;

      setMessages(prev => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          sender: 'bot',
          text: fallbackAnswer,
          ts: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Render markdown text and detect [T-X] task keys
  const formatText = (text) => {
    const parts = text.split(/(\[T-\d+\]|\*\*.*?\*\*)/g);

    return parts.map((part, i) => {
      if (part.startsWith('[T-') && part.endsWith(']')) {
        const key = part.slice(1, -1);
        return (
          <button
            key={i}
            className="chat-task-chip font-mono"
            onClick={() => setSelectedTaskKey(key)}
          >
            {part}
          </button>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="guide-chat-page">
      <div className="chat-layout">
        {/* Main Conversation Column */}
        <div className="chat-main">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-info">
              <div className="guide-avatar-wrap">
                {activeTab === 'telegram' ? (
                  <MessageSquare size={20} style={{ color: '#3b82f6' }} />
                ) : (
                  <Sparkles size={20} className="text-purple" />
                )}
              </div>
              <div>
                <h1 className="chat-title">
                  {activeTab === 'telegram' ? 'Telegram Group Feed' : 'Guide Agent Chat'}
                </h1>
                <p className="chat-subtitle">
                  {activeTab === 'telegram'
                    ? `Live monitoring linked Telegram group (${snapshot?.project?.telegram_status === 'connected' ? 'Connected' : 'Waiting for /link'})`
                    : 'Proactive coordination agent & project health advisor'}
                </p>
              </div>
            </div>

            {/* Segmented Tab Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(15, 23, 42, 0.6)', padding: 4, borderRadius: 10, border: '1px solid rgba(51, 65, 85, 0.5)' }}>
              <button
                className={`btn btn-sm ${activeTab === 'telegram' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 6 }}
                onClick={() => setActiveTab('telegram')}
              >
                <Radio size={12} style={{ color: snapshot?.project?.telegram_status === 'connected' ? '#10b981' : '#f59e0b' }} />
                <span>Telegram Live Feed</span>
                <span className="tab-count-badge" style={{ fontSize: 9 }}>{telegramMessages.length}</span>
              </button>
              <button
                className={`btn btn-sm ${activeTab === 'guide' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 6 }}
                onClick={() => setActiveTab('guide')}
              >
                <Sparkles size={12} />
                <span>Guide AI Chat</span>
              </button>
            </div>
          </div>

          {activeTab === 'telegram' ? (
            /* Telegram Group Live Feed View */
            <div className="chat-messages" style={{ flex: 1, overflowY: 'auto' }}>
              {telegramMessages.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
                  <MessageSquare size={36} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                    No Telegram Messages Recorded Yet
                  </h3>
                  <p style={{ fontSize: 12, maxWidth: 420, margin: '0 auto', lineHeight: 1.5 }}>
                    To connect your group, add your bot to your team Telegram group and type:
                  </p>
                  <code style={{ display: 'inline-block', margin: '10px 0', padding: '6px 14px', background: 'rgba(0,0,0,0.3)', borderRadius: 6, color: '#38bdf8', fontSize: 13, border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                    /link {code}
                  </code>
                  <p style={{ fontSize: 11, opacity: 0.7 }}>
                    Every message, check-in, blocker, and completion claim sent in that group will appear here live in real-time.
                  </p>
                </div>
              ) : (
                telegramMessages.map(msg => {
                  const isBot = msg.direction === 'out';
                  const ownerColor = getOwnerColor(msg.member_id);

                  return (
                    <div
                      key={msg.id}
                      className={`chat-bubble-wrap ${isBot ? 'bot-wrap' : 'user-wrap'}`}
                    >
                      <div
                        className="sender-avatar"
                        style={{
                          background: isBot ? 'var(--accent)' : ownerColor,
                          color: '#fff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: 10
                        }}
                      >
                        {isBot ? '🤖' : (msg.sender?.[0] || 'U')}
                      </div>

                      <div className={`chat-bubble ${isBot ? 'bot' : 'user'}`} style={{ maxWidth: '85%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: isBot ? 'var(--accent)' : ownerColor }}>
                            {msg.sender}
                          </span>
                          {msg.intent && (
                            <span
                              className="pill"
                              style={{
                                fontSize: 9,
                                padding: '1px 6px',
                                textTransform: 'uppercase',
                                background: msg.intent === 'blocker' ? 'rgba(239, 68, 68, 0.2)' : msg.intent === 'completion_claim' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                                color: msg.intent === 'blocker' ? '#ef4444' : msg.intent === 'completion_claim' ? '#10b981' : '#60a5fa'
                              }}
                            >
                              {msg.intent.replace('_', ' ')}
                            </span>
                          )}
                        </div>

                        <div className="bubble-text" style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
                          {formatText(msg.text || '')}
                        </div>

                        <div className="bubble-meta" style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className="bubble-time">{relativeTime(msg.created_at)}</span>
                          <span style={{ fontSize: 9, opacity: 0.5 }}>• {isBot ? 'Bot Outbound' : 'Group Inbound'}</span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={tgEndRef} />
            </div>
          ) : (
            /* Guide AI Chat View */
            <>
              {/* Quick prompt chips */}
              <div className="quick-prompts-bar">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    className="quick-prompt-btn"
                    onClick={() => handleSend(prompt)}
                    disabled={loading}
                  >
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>

              {/* Message Stream */}
              <div className="chat-messages">
                {messages.map(msg => (
                  <div
                    key={msg.id}
                    className={`chat-bubble-wrap ${msg.sender === 'user' ? 'user-wrap' : 'bot-wrap'}`}
                  >
                    {msg.sender === 'bot' && (
                      <div className="sender-avatar bot">
                        <Sparkles size={16} />
                      </div>
                    )}

                    <div className={`chat-bubble ${msg.sender}`}>
                      <div className="bubble-text">{formatText(msg.text)}</div>
                      <div className="bubble-meta">
                        <span className="bubble-time">{relativeTime(msg.ts)}</span>
                      </div>
                    </div>

                    {msg.sender === 'user' && (
                      <div className="sender-avatar user">
                        <User size={16} />
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="chat-bubble-wrap bot-wrap">
                    <div className="sender-avatar bot">
                      <Sparkles size={16} />
                    </div>
                    <div className="chat-bubble bot thinking">
                      <Loader2 size={16} className="animate-pulse text-purple" />
                      <span>Guide is analyzing snapshot &amp; repository...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Box */}
              <form
                className="chat-input-container"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
              >
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Ask Guide anything about the project, blockers, commits, or risks..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                />
                <button
                  type="submit"
                  className="btn btn-primary chat-send-btn"
                  disabled={!input.trim() || loading}
                >
                  <Send size={15} />
                </button>
              </form>
            </>
          )}
        </div>

        {/* Sidebar: Proactive Insights & Contradictions */}
        <aside className="chat-insights-panel">
          <div className="insights-header">
            <Sparkles size={16} className="text-purple" />
            <h2>Proactive AI Stream</h2>
          </div>

          {/* Contradictions Alert */}
          {contradictions.length > 0 && (
            <div className="contradictions-box">
              <div className="contradictions-title">
                <AlertTriangle size={15} className="text-red" />
                <span>Contradictions Detected ({contradictions.length})</span>
              </div>
              {contradictions.map((c, i) => (
                <div key={i} className="contradiction-item">
                  <p className="contradiction-summary">{c.summary}</p>
                  <span className="contradiction-status font-mono">Status: {c.status}</span>
                </div>
              ))}
            </div>
          )}

          {/* Guide Notes */}
          <div className="notes-list">
            <h3 className="notes-heading">Recent Guide Notes</h3>
            {guideNotes.length === 0 ? (
              <div className="no-notes text-muted text-xs">
                No recent warnings or notes. Guide is silently observing check-in replies.
              </div>
            ) : (
              guideNotes.map((note, idx) => {
                const noteText = typeof note === 'string' ? note : note.text || note.summary || JSON.stringify(note);
                return (
                  <div key={idx} className="guide-note-card">
                    <p className="note-text">{noteText}</p>
                    {note.created_at && (
                      <span className="note-time">{relativeTime(note.created_at)}</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </aside>
      </div>

      {/* Task Drawer */}
      {selectedTaskKey && (
        <TaskDrawer
          taskKey={selectedTaskKey}
          snapshot={snapshot}
          code={code}
          onClose={() => setSelectedTaskKey(null)}
          onOpenTask={key => setSelectedTaskKey(key)}
        />
      )}
    </div>
  );
}

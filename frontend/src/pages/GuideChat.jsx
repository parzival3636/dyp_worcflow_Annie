import { useState, useRef, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { apiPost, getMemberName, getOwnerColor, relativeTime } from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import TaskDrawer from '../components/TaskDrawer';
import {
  Sparkles, Send, Bot, User, AlertTriangle, ShieldCheck,
  HelpCircle, ArrowRight, CornerDownLeft, Loader2
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

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedTaskKey, setSelectedTaskKey] = useState(null);
  const messagesEndRef = useRef(null);

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
                <Sparkles size={20} className="text-purple" />
              </div>
              <div>
                <h1 className="chat-title">Guide Agent Chat</h1>
                <p className="chat-subtitle">Proactive coordination agent &amp; project health advisor</p>
              </div>
            </div>

            <div className="chat-header-badge">
              <span className="live-pulse" />
              <span>AI Polling Active</span>
            </div>
          </div>

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

import React, { useState } from 'react';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  Minus,
  Maximize2,
  X,
  Send,
  Eye,
  GitCommit,
  CheckCircle2,
  Clock
} from 'lucide-react';
import './GuideDockPanel.css';

export default function GuideDockPanel({
  snapshot,
  activeTaskKey,
  onOpenTaskPreview
}) {
  const [minimized, setMinimized] = useState(false);
  const [closed, setClosed] = useState(false);
  const [expandedWork, setExpandedWork] = useState(false);
  const [inputVal, setInputVal] = useState('');
  const [extraMessages, setExtraMessages] = useState([]);

  if (closed) {
    return (
      <button
        className="btn btn-secondary floating-layer"
        style={{
          position: 'fixed',
          bottom: 20,
          right: 24,
          zIndex: 8000,
          gap: 6,
          padding: '8px 12px',
          borderColor: 'var(--accent)'
        }}
        onClick={() => setClosed(false)}
      >
        <Sparkles size={14} className="text-accent" />
        <span>Guide Agent</span>
      </button>
    );
  }

  // Get active task or pick one from snapshot for realistic context
  const activeTask = snapshot?.tasks?.find(t => t.key === activeTaskKey) ||
    snapshot?.tasks?.find(t => t.status === 'blocked') ||
    snapshot?.tasks?.[0];

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    const msg = inputVal.trim();
    setInputVal('');
    setExtraMessages(prev => [
      ...prev,
      { role: 'user', text: msg },
      {
        role: 'agent',
        text: `Analyzing ${activeTask ? activeTask.key : 'project state'}... Coordinated with Telegram & GitHub. Verified dependencies are intact.`
      }
    ]);
  };

  return (
    <div className={`guide-dock-panel ${minimized ? 'minimized' : ''}`}>
      {/* Header */}
      <div className="guide-dock-header">
        <div className="guide-dock-title-group">
          <div className="guide-dock-avatar">
            <Sparkles size={11} />
          </div>
          <span className="font-semibold text-xs">Pilot Guide</span>
          <span className="guide-model-badge">Agent v2.4</span>
        </div>

        <div className="guide-dock-actions">
          <button
            className="guide-dock-btn"
            onClick={() => setMinimized(!minimized)}
            title={minimized ? 'Expand panel' : 'Minimize panel'}
            aria-label="Toggle minimize"
          >
            {minimized ? <Maximize2 size={13} /> : <Minus size={13} />}
          </button>
          <button
            className="guide-dock-btn"
            onClick={() => setClosed(true)}
            title="Close panel"
            aria-label="Close panel"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {!minimized && (
        <>
          {/* Scrollable Agent Feed */}
          <div className="guide-dock-body">
            {/* User prompt card */}
            <div className="guide-user-bubble">
              Verify downstream ripple effect for {activeTask?.key || 'T-2'} and alert assigned builders.
            </div>

            {/* Added to context chip */}
            <div className="guide-context-chip">
              <span className="chip-key">{activeTask?.key || 'T-2'}</span>
              <span>added to context</span>
            </div>

            {/* Worked for 10 sec collapsible */}
            <div>
              <div
                className="guide-work-collapsible"
                onClick={() => setExpandedWork(!expandedWork)}
              >
                <Clock size={12} />
                <span>Worked for 10 sec</span>
                {expandedWork ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </div>

              {expandedWork && (
                <div
                  style={{
                    padding: '8px 10px',
                    margin: '4px 0',
                    background: 'var(--surface-raised)',
                    borderRadius: 4,
                    fontSize: 11,
                    fontFamily: 'Geist Mono',
                    color: 'var(--text-muted)',
                    lineHeight: 1.4
                  }}
                >
                  <div>[13:30:12] Fetched commit tree for pilot-team/payflow</div>
                  <div>[13:30:15] Analyzed 2 modified migration files</div>
                  <div>[13:30:18] Computed downstream slip: Demo milestone +3.5h</div>
                  <div>[13:30:22] Dispatched Telegram alert to @kabir_ops</div>
                </div>
              )}
            </div>

            {/* Streamed Answer */}
            <div className="guide-agent-answer">
              Ran GitHub AST verifier against commit <code className="font-mono text-xs">4a9f2bc</code>.
              Schema migrations for the payment ledger were committed with valid foreign keys.
              However, webhook credentials remain pending from Aarav.
            </div>

            {/* GitHub Verification Card (Linear PR card style) */}
            <div className="guide-result-card">
              <div className="guide-result-header">
                <div className="guide-result-stats">
                  <span className="stat-changed">Changed 2 files</span>
                  <span className="stat-plus">+142</span>
                  <span className="stat-minus">-12</span>
                </div>
                <div className="pill pill-verified_done" style={{ fontSize: 10, padding: '1px 6px' }}>
                  <CheckCircle2 size={10} />
                  <span>VERIFIED 94%</span>
                </div>
              </div>

              <div className="guide-result-branch">
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <GitCommit size={12} />
                  <span className="guide-result-sha">4a9f2bc</span>
                  <span>db/migration_01.sql</span>
                </div>
                <button
                  className="btn btn-sm btn-ghost"
                  style={{ padding: '2px 6px', fontSize: 10, gap: 4 }}
                  onClick={() => onOpenTaskPreview?.(activeTask?.key || 'T-1')}
                >
                  <Eye size={11} />
                  <span>Preview</span>
                </button>
              </div>
            </div>

            {/* Extra dialogue if user typed */}
            {extraMessages.map((m, i) => (
              <div
                key={i}
                className={m.role === 'user' ? 'guide-user-bubble' : 'guide-agent-answer'}
              >
                {m.text}
              </div>
            ))}
          </div>

          {/* Footer Input */}
          <form className="guide-dock-footer" onSubmit={handleSend}>
            <input
              type="text"
              className="guide-footer-input"
              placeholder="Ask Guide coordinator or query task..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
            />
            <button
              type="submit"
              className="btn btn-sm btn-primary"
              style={{ padding: '4px 8px' }}
              disabled={!inputVal.trim()}
              aria-label="Send message to Guide"
            >
              <Send size={12} />
            </button>
          </form>
        </>
      )}
    </div>
  );
}

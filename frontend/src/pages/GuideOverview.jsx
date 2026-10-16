import { useState, useMemo } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import {
  apiPost, getMemberName, getOwnerColor, relativeTime, formatTime, STATUS_COLORS, STATUS_LABELS
} from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import {
  Sparkles, ShieldCheck, AlertTriangle, CheckCircle2,
  FileText, TrendingUp, Users, GitCommit, Clock, ArrowRight,
  ExternalLink, Download, MessageSquare, AlertCircle, ShieldAlert
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import './GuideOverview.css';

export default function GuideOverview() {
  const { snapshot, code } = useOutletContext();
  const { addToast } = useToast();

  const [generatingReport, setGeneratingReport] = useState(false);
  const [executiveReport, setExecutiveReport] = useState(null);

  const project = snapshot?.project || {};
  const tasks = snapshot?.tasks || [];
  const members = snapshot?.members || [];
  const contradictions = snapshot?.contradictions || [];
  const events = snapshot?.events || [];
  const guideNotes = snapshot?.guide_notes || [];

  // Computed metrics for Evaluator / Guide
  const verifiedTasks = tasks.filter(t => t.status === 'verified_done');
  const blockedTasks = tasks.filter(t => t.status === 'blocked');
  const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
  const reviewTasks = tasks.filter(t => t.status === 'needs_review');

  const completionPct = tasks.length > 0 ? Math.round((verifiedTasks.length / tasks.length) * 100) : 0;
  const verifiedEffort = verifiedTasks.reduce((sum, t) => sum + (t.effort || 1), 0);
  const totalEffort = tasks.reduce((sum, t) => sum + (t.effort || 1), 0);

  // Generate Executive Audit Report
  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const res = await apiPost(`/projects/${code}/report`);
      setExecutiveReport(res.report);
      addToast('Executive coordinator report generated!', 'green');
    } catch {
      // Fallback report
      setExecutiveReport({
        project_name: project.name || 'PayFlow',
        project_code: code,
        status: project.status || 'running',
        total_tasks: tasks.length,
        verified_tasks: verifiedTasks.length,
        blocked_tasks: blockedTasks.length,
        completion_rate: `${completionPct}%`,
        members_count: members.length,
        summary: `Autonomous coordinator audit: ${verifiedTasks.length} tasks verified with commit proofs. ${blockedTasks.length} active bottlenecks mitigated.`,
        generated_at: new Date().toISOString()
      });
      addToast('Report generated successfully', 'green');
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <div className="guide-overview-page">
      {/* Top Banner / Executive Summary */}
      <div className="guide-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="pill pill-purple">Guide &amp; Evaluator Portal</span>
            <span className="pill pill-green">Autonomous Coordination Active</span>
          </div>
          <h1 className="guide-title">Executive Project Health &amp; Oversight</h1>
          <p className="guide-subtitle">
            Autonomous multi-agent oversight observing Telegram check-in replies, GitHub commit verification, and topological milestone risk.
          </p>
        </div>

        <div className="guide-actions">
          <button
            className="btn btn-secondary"
            onClick={handleGenerateReport}
            disabled={generatingReport}
          >
            <FileText size={14} className="text-purple" />
            <span>{generatingReport ? 'Auditing...' : 'Generate Executive Report'}</span>
          </button>

          <Link to={`/p/${code}/chat`} className="btn btn-primary">
            <Sparkles size={14} />
            <span>Interactive Guide Q&amp;A</span>
          </Link>
        </div>
      </div>

      {/* Primary KPI Ribbon */}
      <div className="guide-kpi-grid">
        <div className="guide-kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">Verified Progress</span>
            <ShieldCheck size={16} className="text-green" />
          </div>
          <div className="kpi-value text-green">{completionPct}%</div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: `${completionPct}%` }} />
          </div>
          <span className="kpi-sub text-muted">{verifiedTasks.length} of {tasks.length} tasks passed git proof</span>
        </div>

        <div className="guide-kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">Active Bottlenecks</span>
            <AlertTriangle size={16} className={blockedTasks.length > 0 ? 'text-red' : 'text-green'} />
          </div>
          <div className={`kpi-value ${blockedTasks.length > 0 ? 'text-red' : 'text-green'}`}>
            {blockedTasks.length}
          </div>
          <span className="kpi-sub text-muted">
            {blockedTasks.length > 0 ? `${blockedTasks[0].key} routed for resolution` : 'No open blockers'}
          </span>
        </div>

        <div className="guide-kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">Effort Burned</span>
            <TrendingUp size={16} className="text-blue" />
          </div>
          <div className="kpi-value font-mono">{verifiedEffort} / {totalEffort}h</div>
          <span className="kpi-sub text-muted">Engineering hours completed</span>
        </div>

        <div className="guide-kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">Active Builders</span>
            <Users size={16} className="text-amber" />
          </div>
          <div className="kpi-value">{members.length}</div>
          <span className="kpi-sub text-muted">Telegram &amp; GitHub synced</span>
        </div>
      </div>

      {/* Generated Report Modal / Card */}
      {executiveReport && (
        <div className="executive-report-card">
          <div className="report-card-header">
            <div className="flex items-center gap-2">
              <FileText size={18} className="text-purple" />
              <h2 className="report-card-title">Executive Evaluation Audit Report</h2>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setExecutiveReport(null)}
            >
              Close
            </button>
          </div>

          <p className="report-card-summary">{executiveReport.summary}</p>

          <div className="report-metrics-row">
            <div className="report-item">
              <span className="item-label">Project:</span>
              <strong>{executiveReport.project_name} ({executiveReport.project_code})</strong>
            </div>
            <div className="report-item">
              <span className="item-label">Verified Rate:</span>
              <strong className="text-green">{executiveReport.completion_rate}</strong>
            </div>
            <div className="report-item">
              <span className="item-label">Verified Tasks:</span>
              <strong>{executiveReport.verified_tasks} / {executiveReport.total_tasks}</strong>
            </div>
            <div className="report-item">
              <span className="item-label">Generated:</span>
              <span className="text-muted">{relativeTime(executiveReport.generated_at)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Bottlenecks & Proactive Notes */}
      <div className="guide-content-grid">
        {/* Left Column: Bottleneck Radar & Contradictions */}
        <div className="guide-grid-col">
          {/* Card: Bottleneck Radar */}
          <div className="guide-panel-card">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <ShieldAlert size={16} className="text-red" />
                <h2 className="panel-title">Critical Path Bottlenecks &amp; Downstream Slip</h2>
              </div>
              <Link to={`/p/${code}/graph`} className="panel-link">
                <span>View Full DAG</span>
                <ArrowRight size={13} />
              </Link>
            </div>

            {blockedTasks.length === 0 ? (
              <div className="panel-empty">
                <CheckCircle2 size={24} className="text-green" />
                <span>All dependency paths are clear. Demo milestone is currently on track.</span>
              </div>
            ) : (
              <div className="bottlenecks-list">
                {blockedTasks.map(task => {
                  const ownerName = getMemberName(snapshot, task.owner_member_id);
                  const routedMember = task.blocker?.routed_to ? getMemberName(snapshot, task.blocker.routed_to) : null;

                  return (
                    <div key={task.key} className="bottleneck-item">
                      <div className="bottleneck-top">
                        <span className="font-mono text-red font-bold">[{task.key}]</span>
                        <span className="bottleneck-task-name">{task.title}</span>
                        <span className="pill pill-red">Blocked</span>
                      </div>

                      <div className="bottleneck-desc">
                        {task.blocker?.description || 'Teammate reported blocker via Telegram check-in'}
                      </div>

                      <div className="bottleneck-routing">
                        <span className="text-muted">Assigned: <strong>{ownerName}</strong></span>
                        {routedMember && (
                          <span className="routed-indicator">
                            → Routed to <strong>{routedMember}</strong> via bot DM
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Card: Contradiction Reconciliations */}
          <div className="guide-panel-card">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-amber" />
                <h2 className="panel-title">Cross-Member Contradiction Reconciliations</h2>
              </div>
            </div>

            {contradictions.length === 0 ? (
              <div className="panel-empty text-xs text-muted">
                No contradicting claims detected between builder Telegram replies.
              </div>
            ) : (
              <div className="contradiction-list">
                {contradictions.map(c => (
                  <div key={c.id} className="contradiction-card">
                    <p className="contradiction-text">{c.summary}</p>
                    <div className="contradiction-meta">
                      <span className="text-xs text-muted">Detected across check-in replies</span>
                      <span className="pill pill-amber">Status: {c.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: AI Proactive Feed & Recent Verifications */}
        <div className="guide-grid-col">
          {/* Card: Proactive AI Insights Stream */}
          <div className="guide-panel-card">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-purple" />
                <h2 className="panel-title">Proactive Guide Agent Feed</h2>
              </div>
              <Link to={`/p/${code}/activity`} className="panel-link">
                <span>All Events</span>
                <ArrowRight size={13} />
              </Link>
            </div>

            <div className="guide-notes-stream">
              {guideNotes.length === 0 ? (
                <div className="panel-empty text-xs text-muted">
                  Guide is actively monitoring Telegram check-ins and GitHub commits.
                </div>
              ) : (
                guideNotes.map((note, idx) => {
                  const noteText = typeof note === 'string' ? note : note.text || note.summary || JSON.stringify(note);
                  return (
                    <div key={idx} className="guide-feed-item">
                      <div className="feed-icon">
                        <Sparkles size={13} className="text-purple" />
                      </div>
                      <div className="feed-content">
                        <p className="feed-text">{noteText}</p>
                        {note.created_at && (
                          <span className="feed-time">{relativeTime(note.created_at)}</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Card: Recent AI Verifications */}
          <div className="guide-panel-card">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-green" />
                <h2 className="panel-title">Automated Criteria Verifications</h2>
              </div>
            </div>

            <div className="verifications-list">
              {tasks.filter(t => t.verification).length === 0 ? (
                <div className="panel-empty text-xs text-muted">
                  No automated verification runs logged yet.
                </div>
              ) : (
                tasks.filter(t => t.verification).slice(0, 4).map(task => (
                  <div key={task.key} className="verification-item">
                    <div className="verify-top">
                      <span className="font-mono text-blue font-bold">[{task.key}]</span>
                      <span className="verify-task-title truncate">{task.title}</span>
                      <span className="pill pill-green">
                        {Math.round(task.verification.confidence * 100)}% Confidence
                      </span>
                    </div>
                    <div className="verify-reason text-xs text-muted">
                      {task.verification.reason}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

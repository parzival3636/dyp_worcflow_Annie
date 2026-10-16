import { useState, useCallback } from 'react';
import {
  getOwnerColor, getMemberName, relativeTime, formatTime,
  isOverdue, getTaskDeps, getTask, STATUS_LABELS, STATUS_COLORS, apiPost
} from '../hooks/useSnapshot';
import { useToast } from './ToastProvider';
import {
  X, Calendar, Target, GitCommit, Link as LinkIcon, Shield,
  Star, CheckCircle, XCircle, MessageSquare, ArrowRight,
  ChevronDown, AlertCircle, Clock
} from 'lucide-react';
import './TaskDrawer.css';

export default function TaskDrawer({ taskKey, snapshot, code, onClose, onOpenTask }) {
  const task = getTask(snapshot, taskKey);
  const { addToast } = useToast();
  const [overrideConfirm, setOverrideConfirm] = useState(false);
  const [overrideLoading, setOverrideLoading] = useState(false);

  if (!task) return null;

  const ownerColor = getOwnerColor(task.owner_member_id);
  const ownerName = getMemberName(snapshot, task.owner_member_id);
  const { dependsOn, blocks } = getTaskDeps(snapshot, task.key);
  const overdue = isOverdue(task.deadline);
  const statusClass = STATUS_COLORS[task.status] || 'muted';

  const verification = task.verification;
  const blocker = task.blocker;

  // Messages for this task from events (simplified)
  const messages = (snapshot?.events || [])
    .filter(e =>
      (e.type === 'checkin_sent' || e.type === 'reply_received') &&
      e.task_id === task.key
    )
    .map(e => ({
      id: e.id,
      direction: e.type === 'checkin_sent' ? 'out' : 'in',
      text: typeof e.payload === 'string' ? e.payload : (e.payload?.text || e.type),
      ts: e.ts,
      member: e.actor_member_id,
    }));

  const handleOverride = async () => {
    setOverrideLoading(true);
    try {
      await apiPost(`/projects/${code}/tasks/${task.key}/override-verify`);
      addToast(`${task.key} overridden to Verified Done`, 'green');
      setOverrideConfirm(false);
    } catch {
      addToast('Override failed', 'red');
    } finally {
      setOverrideLoading(false);
    }
  };

  const confidenceColor = (c) => {
    if (c >= 0.7) return 'green';
    if (c >= 0.4) return 'amber';
    return 'red';
  };

  const criteria = task.acceptance_criteria || [];
  const criteriaResults = verification?.criteria_results || [];

  return (
    <>
      <div className="overlay-backdrop" onClick={onClose} />
      <div className="task-drawer animate-slide-in">
        {/* Header */}
        <div className="drawer-header">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="font-mono text-sm text-muted">{task.key}</span>
            <span className="font-semibold text-base truncate">{task.title}</span>
            <span className={`pill pill-${statusClass}`}>{STATUS_LABELS[task.status]}</span>
          </div>
          <button className="btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="drawer-body">
          {/* Meta strip */}
          <div className="drawer-meta">
            <div className="drawer-meta-chip" style={{ borderColor: ownerColor, color: ownerColor }}>
              <span className="member-dot" style={{ background: ownerColor, width: 8, height: 8 }} />
              {ownerName}
            </div>
            {task.deadline && (
              <div className={`flex items-center gap-1 text-xs ${overdue ? 'text-red font-bold' : 'text-muted'}`}>
                <Calendar size={12} />
                {overdue ? `${relativeTime(task.deadline)} overdue` : `due ${relativeTime(task.deadline)}`}
              </div>
            )}
            <span className="text-xs text-muted font-mono">{task.block_id ? `Block ${task.block_id}` : ''}</span>
            {task.effort && (
              <span className="pill pill-muted">{task.effort} pts</span>
            )}
          </div>

          {/* Description */}
          {task.description && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Description</h4>
              <p className="text-base text-muted" style={{ lineHeight: 1.6 }}>{task.description}</p>
            </div>
          )}

          {/* Acceptance criteria */}
          {criteria.length > 0 && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Acceptance Criteria</h4>
              <div className="criteria-list">
                {criteria.map((c, i) => {
                  const result = criteriaResults.find(r => r.criterion === c);
                  const met = result?.met;
                  return (
                    <div key={i} className="criteria-row">
                      <span className={`criteria-check ${met === true ? 'met' : met === false ? 'not-met' : ''}`}>
                        {met === true ? <CheckCircle size={14} /> : met === false ? <XCircle size={14} /> : <span className="criteria-empty" />}
                      </span>
                      <span className="text-sm flex-1">{c}</span>
                      {result?.note && (
                        <span className="text-xs text-muted" style={{ fontStyle: 'italic' }}>{result.note}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {(dependsOn.length > 0 || blocks.length > 0) && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Dependencies</h4>
              {dependsOn.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span className="text-xs text-muted" style={{ marginBottom: 4, display: 'block' }}>Depends on</span>
                  <div className="flex flex-wrap gap-2">
                    {dependsOn.map(d => (
                      <button
                        key={d.key}
                        className="dep-chip"
                        onClick={() => onOpenTask(d.key)}
                      >
                        <span className="font-mono">{d.key}</span>
                        {d.kind === 'handoff' && <span className="text-xs text-amber">handoff</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {blocks.length > 0 && (
                <div>
                  <span className="text-xs text-muted" style={{ marginBottom: 4, display: 'block' }}>Blocks</span>
                  <div className="flex flex-wrap gap-2">
                    {blocks.map(d => (
                      <button
                        key={d.key}
                        className="dep-chip"
                        onClick={() => onOpenTask(d.key)}
                      >
                        <span className="font-mono">{d.key}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Verification report */}
          {verification && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Verification Report</h4>
              <div className="verification-card">
                <div className="flex items-center gap-3" style={{ marginBottom: 12 }}>
                  <span className={`pill pill-${confidenceColor(verification.confidence)}`} style={{ fontSize: 12, padding: '4px 10px' }}>
                    <Shield size={12} />
                    {verification.verdict}
                  </span>
                  <div className="verification-bar">
                    <div
                      className={`verification-bar-fill bg-${confidenceColor(verification.confidence)}`}
                      style={{ width: `${Math.round(verification.confidence * 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-sm">{Math.round(verification.confidence * 100)}%</span>
                </div>
                {verification.reason && (
                  <p className="text-sm" style={{ lineHeight: 1.5, marginBottom: 8 }}>{verification.reason}</p>
                )}
                {verification.matched_shas?.length > 0 && (
                  <div className="flex flex-wrap gap-2" style={{ marginBottom: 8 }}>
                    {verification.matched_shas.map(sha => (
                      <a
                        key={sha}
                        href={snapshot?.project?.repo_url ? `${snapshot.project.repo_url}/commit/${sha}` : '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="sha-chip font-mono text-xs"
                      >
                        <GitCommit size={10} />
                        {sha.substring(0, 7)}
                      </a>
                    ))}
                  </div>
                )}
                {criteriaResults.length > 0 && (
                  <div className="criteria-results">
                    {criteriaResults.map((cr, i) => (
                      <div key={i} className="criteria-result-row">
                        <span className={cr.met ? 'text-green' : 'text-red'}>
                          {cr.met ? <CheckCircle size={12} /> : <XCircle size={12} />}
                        </span>
                        <span className="text-sm flex-1">{cr.criterion}</span>
                        {cr.note && <span className="text-xs text-muted" style={{ fontStyle: 'italic' }}>{cr.note}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Blocker */}
          {blocker && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Blocker</h4>
              <div className="blocker-card">
                <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                  <LinkIcon size={14} className="text-red" />
                  <span className="font-medium text-sm">{blocker.description}</span>
                </div>
                {blocker.type && <div className="text-xs text-muted">Type: {blocker.type}</div>}
                <div className="text-xs" style={{ marginTop: 4 }}>
                  {blocker.status === 'routed' && (
                    <span className="text-amber">Waiting on {blocker.routed_to ? getMemberName(snapshot, blocker.routed_to) : 'someone'}</span>
                  )}
                  {blocker.status === 'resolved' && (
                    <span className="text-green">✓ Resolved</span>
                  )}
                  {blocker.status === 'open' && (
                    <span className="text-red">Open — not yet routed</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Message thread */}
          {messages.length > 0 && (
            <div className="drawer-section">
              <h4 className="drawer-section-title">Message Thread</h4>
              <div className="message-thread">
                {messages.map(m => (
                  <div key={m.id} className={`message-bubble ${m.direction}`}>
                    <p className="text-sm">{m.text}</p>
                    <span className="font-mono text-xs text-muted" style={{ marginTop: 4, display: 'block' }}>
                      {formatTime(m.ts)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Lead override footer */}
        <div className="drawer-footer">
          {!overrideConfirm ? (
            <button
              className="btn btn-outline-red btn-sm w-full"
              onClick={() => setOverrideConfirm(true)}
            >
              Override to Verified
            </button>
          ) : (
            <div className="override-confirm">
              <p className="text-xs text-muted" style={{ marginBottom: 8 }}>
                <AlertCircle size={12} style={{ verticalAlign: 'middle' }} /> This bypasses GitHub verification. Are you sure?
              </p>
              <div className="flex gap-2">
                <button
                  className="btn btn-outline-red btn-sm flex-1"
                  onClick={handleOverride}
                  disabled={overrideLoading}
                >
                  {overrideLoading ? 'Overriding…' : 'Confirm Override'}
                </button>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setOverrideConfirm(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

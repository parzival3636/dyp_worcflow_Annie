import { useState, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  STATUS_ORDER, STATUS_LABELS, STATUS_COLORS,
  getOwnerColor, getMemberName, relativeTime, isOverdue, apiPatch,
  getTaskDeps, formatTime
} from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import TaskDrawer from '../components/TaskDrawer';
import {
  AlertTriangle, AlertCircle, Calendar, Star, Link as LinkIcon,
  Shield, Clock, ChevronRight
} from 'lucide-react';
import './Board.css';

export default function Board() {
  const { snapshot, code } = useOutletContext();
  const { addToast } = useToast();
  const [drawerTaskKey, setDrawerTaskKey] = useState(null);
  const [dragState, setDragState] = useState(null);

  const tasks = snapshot?.tasks || [];
  const members = snapshot?.members || [];
  const contradictions = snapshot?.contradictions || [];

  // Group tasks by status
  const columns = {};
  STATUS_ORDER.forEach(s => { columns[s] = []; });
  tasks.forEach(t => {
    if (columns[t.status]) columns[t.status].push(t);
    else if (columns.todo) columns.todo.push(t); // fallback
  });

  // Drag handlers
  const handleDragStart = (e, taskKey) => {
    setDragState(taskKey);
    e.dataTransfer.setData('text/plain', taskKey);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = useCallback(async (e, newStatus) => {
    e.preventDefault();
    const taskKey = e.dataTransfer.getData('text/plain');
    setDragState(null);
    if (!taskKey) return;

    const task = tasks.find(t => t.key === taskKey);
    if (!task || task.status === newStatus) return;

    try {
      await apiPatch(`/projects/${code}/tasks/${taskKey}`, { status: newStatus });
      addToast(`${taskKey} moved to ${STATUS_LABELS[newStatus]}`, 'blue');
    } catch {
      addToast(`Failed to update ${taskKey}`, 'red');
    }
  }, [tasks, code, addToast]);

  // Project health stats
  const verified = tasks.filter(t => t.status === 'verified_done').length;
  const inProgress = tasks.filter(t => t.status === 'in_progress').length;
  const blocked = tasks.filter(t => t.status === 'blocked').length;
  const overdue = tasks.filter(t => isOverdue(t.deadline) && t.status !== 'verified_done').length;

  return (
    <div className="board-page">
      {/* Contradiction banner */}
      {contradictions.length > 0 && (
        <div className="contradiction-banner">
          <AlertCircle size={16} />
          <strong>{contradictions.length} open contradiction{contradictions.length > 1 ? 's' : ''} detected</strong>
          {contradictions[0]?.summary && (
            <span className="text-sm" style={{ opacity: 0.8 }}>
              — {contradictions[0].summary.substring(0, 80)}{contradictions[0].summary.length > 80 ? '…' : ''}
            </span>
          )}
          <span className="text-sm" style={{ marginLeft: 'auto', cursor: 'pointer' }}>
            View all <ChevronRight size={12} style={{ verticalAlign: 'middle' }} />
          </span>
        </div>
      )}

      {/* Health summary strip */}
      <div className="board-health-strip">
        <div className="health-stat">
          <span className="health-stat-value text-green">{verified}</span>
          <span className="health-stat-label">Verified</span>
          <span className="text-xs text-muted">/ {tasks.length}</span>
        </div>
        <div className="health-stat">
          <span className="health-stat-value text-blue">{inProgress}</span>
          <span className="health-stat-label">In Progress</span>
        </div>
        <div className="health-stat">
          <span className="health-stat-value text-red">{blocked}</span>
          <span className="health-stat-label">Blocked</span>
        </div>
        <div className="health-stat">
          <span className="health-stat-value text-amber">{overdue}</span>
          <span className="health-stat-label">Overdue</span>
        </div>
      </div>

      {/* Columns */}
      <div className="board-columns">
        {STATUS_ORDER.map(status => (
          <div
            key={status}
            className={`board-column ${dragState ? 'drop-target' : ''}`}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, status)}
          >
            <div className="board-column-header">
              <div className="flex items-center gap-2">
                <span className={`board-column-dot status-${status}`} />
                <span className="font-medium text-sm">{STATUS_LABELS[status]}</span>
              </div>
              <span className="text-xs text-muted">{columns[status].length}</span>
            </div>

            <div className="board-column-cards">
              {columns[status].length === 0 && (
                <div className="board-empty-col text-xs text-muted">No tasks</div>
              )}
              {columns[status].map(task => (
                <TaskCard
                  key={task.key}
                  task={task}
                  snapshot={snapshot}
                  onDragStart={handleDragStart}
                  onClick={() => setDrawerTaskKey(task.key)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {tasks.length === 0 && (
        <div className="board-empty">
          <LayoutGridIcon />
          <p className="text-muted text-base">No tasks yet — go to <strong>Plan</strong> to generate tasks</p>
        </div>
      )}

      {/* Task drawer */}
      {drawerTaskKey && (
        <TaskDrawer
          taskKey={drawerTaskKey}
          snapshot={snapshot}
          code={code}
          onClose={() => setDrawerTaskKey(null)}
          onOpenTask={(key) => setDrawerTaskKey(key)}
        />
      )}
    </div>
  );
}

function LayoutGridIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted" style={{ opacity: 0.4 }}>
      <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function TaskCard({ task, snapshot, onDragStart, onClick }) {
  const ownerColor = getOwnerColor(task.owner_member_id);
  const ownerName = getMemberName(snapshot, task.owner_member_id);
  const deadline = task.deadline;
  const overdue = isOverdue(deadline);

  const confidenceColor = (c) => {
    if (c >= 0.7) return 'green';
    if (c >= 0.4) return 'amber';
    return 'red';
  };

  return (
    <div
      className="task-card"
      style={{ borderLeftColor: ownerColor }}
      draggable
      onDragStart={(e) => onDragStart(e, task.key)}
      onClick={onClick}
    >
      {/* Top row */}
      <div className="task-card-top">
        <span className="font-mono text-xs text-muted">{task.key}</span>
        {task.risk === 'at_risk' && (
          <span className="pill pill-amber" style={{ fontSize: 10 }}>
            <AlertTriangle size={10} /> At Risk
          </span>
        )}
        {task.risk === 'critical' && (
          <span className="pill pill-red animate-pulse" style={{ fontSize: 10 }}>
            🔴 Critical
          </span>
        )}
      </div>

      {/* Title */}
      <div className="task-card-title">{task.title}</div>

      {/* Owner */}
      <div className="task-card-owner">
        <span className="member-dot" style={{ background: ownerColor, width: 6, height: 6 }} />
        <span className="text-xs text-muted truncate">{ownerName}</span>
      </div>

      {/* Deadline */}
      {deadline && (
        <div className={`task-card-deadline ${overdue ? 'overdue' : ''}`} title={formatTime(deadline)}>
          <Calendar size={11} />
          <span>{overdue ? `${relativeTime(deadline)} overdue` : `due ${relativeTime(deadline)}`}</span>
        </div>
      )}

      {/* Progress bar */}
      {task.status === 'in_progress' && task.progress > 0 && (
        <div className="task-card-progress">
          <div className="task-card-progress-fill" style={{ width: `${task.progress}%` }} />
        </div>
      )}

      {/* Bottom row */}
      <div className="task-card-bottom">
        <div className="flex items-center gap-2">
          {task.verification && (
            <span className={`pill pill-${confidenceColor(task.verification.confidence)}`} style={{ fontSize: 10 }}>
              {task.verification.confidence >= 0.7 ? '✓' : '⚠'}{' '}
              {Math.round(task.verification.confidence * 100)}%
            </span>
          )}
          {task.blocker && <LinkIcon size={11} className="text-red" />}
          {task.is_milestone && <Star size={11} className="text-amber" />}
        </div>
      </div>
    </div>
  );
}

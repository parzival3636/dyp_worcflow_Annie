import React, { useState, useMemo, useCallback } from 'react';
import { useOutletContext, useParams } from 'react-router-dom';
import {
  STATUS_ORDER, STATUS_LABELS, getOwnerColor, getMemberName,
  apiPatch
} from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import {
  Layers, Users, ChevronDown, ChevronRight, CheckCircle2,
  AlertOctagon, AlertTriangle, Archive, Grid, List, Shield,
  GitCommit
} from 'lucide-react';
import './Board.css';

// Default WIP limits per column (editable)
const DEFAULT_WIP_LIMITS = {
  todo: 10,
  in_progress: 3,
  blocked: 2,
  claimed_done: 4,
  needs_review: 3,
  verified_done: 20
};

export default function Board() {
  const { code } = useParams();
  const { snapshot, onSelectTask } = useOutletContext?.() || {};
  const { addToast } = useToast();

  const [groupBy, setGroupBy] = useState('member'); // 'member' | 'block'
  const [zoomMode, setZoomMode] = useState('expanded'); // 'compact' | 'expanded'
  const [collapsedLanes, setCollapsedLanes] = useState({});
  const [wipLimits, setWipLimits] = useState(DEFAULT_WIP_LIMITS);
  const [showArchived, setShowArchived] = useState(false);
  const [draggedKey, setDraggedKey] = useState(null);
  const [dragOverCol, setDragOverCol] = useState(null);

  const tasks = snapshot?.tasks || [];
  const members = snapshot?.members || [];
  const blocks = snapshot?.blocks || [];

  // Count tasks per column for WIP limit banners
  const colCounts = useMemo(() => {
    const counts = {};
    STATUS_ORDER.forEach(s => { counts[s] = 0; });
    tasks.forEach(t => {
      if (counts[t.status] !== undefined) counts[t.status]++;
    });
    return counts;
  }, [tasks]);

  // Group swimlanes
  const swimlanes = useMemo(() => {
    if (groupBy === 'member') {
      return members.map(m => ({
        id: m.id,
        title: `${m.name} ${m.role === 'lead' ? '(Lead)' : ''}`,
        avatarColor: getOwnerColor(m.id),
        tasks: tasks.filter(t => t.owner_member_id === m.id)
      }));
    } else {
      return blocks.map(b => ({
        id: b.id,
        title: `Block ${b.id}: ${b.name}`,
        avatarColor: 'var(--accent)',
        tasks: tasks.filter(t => t.block_id === b.id)
      }));
    }
  }, [groupBy, members, blocks, tasks]);

  const toggleLane = (laneId) => {
    setCollapsedLanes(prev => ({ ...prev, [laneId]: !prev[laneId] }));
  };

  // Drag and drop handlers
  const handleDragStart = (e, taskKey) => {
    setDraggedKey(taskKey);
    e.dataTransfer.setData('text/plain', taskKey);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, status) => {
    e.preventDefault();
    setDragOverCol(status);
  };

  const handleDrop = useCallback(async (e, newStatus) => {
    e.preventDefault();
    setDragOverCol(null);
    const taskKey = e.dataTransfer.getData('text/plain') || draggedKey;
    setDraggedKey(null);
    if (!taskKey) return;

    const task = tasks.find(t => t.key === taskKey);
    if (!task || task.status === newStatus) return;

    try {
      await apiPatch(`/projects/${code}/tasks/${taskKey}`, { status: newStatus });
      addToast(`${taskKey} updated to ${STATUS_LABELS[newStatus]}`, 'green');
    } catch {
      // Local state simulation if backend is offline
      task.status = newStatus;
      addToast(`${taskKey} moved to ${STATUS_LABELS[newStatus]} (offline mode)`, 'green');
    }
  }, [draggedKey, tasks, code, addToast]);

  return (
    <div className="board-page">
      {/* Board Toolbar (Swimlane & Zoom Switches) */}
      <div className="board-toolbar">
        <div className="board-toolbar-left">
          <div className="swimlane-toggle-group">
            <button
              className={`swimlane-btn ${groupBy === 'member' ? 'active' : ''}`}
              onClick={() => setGroupBy('member')}
              title="Group swimlanes by team member"
            >
              <Users size={12} style={{ display: 'inline', marginRight: 4 }} />
              Members
            </button>
            <button
              className={`swimlane-btn ${groupBy === 'block' ? 'active' : ''}`}
              onClick={() => setGroupBy('block')}
              title="Group swimlanes by architecture block"
            >
              <Layers size={12} style={{ display: 'inline', marginRight: 4 }} />
              Blocks
            </button>
          </div>

          <span className="text-xs text-muted" style={{ marginLeft: 8 }}>
            Taiga Kanban • {tasks.length} total user stories
          </span>
        </div>

        <div className="board-toolbar-right">
          {/* Zoom toggle: Compact vs Expanded */}
          <div className="zoom-toggle-group">
            <button
              className={`zoom-btn ${zoomMode === 'compact' ? 'active' : ''}`}
              onClick={() => setZoomMode('compact')}
              title="Compact view (ID & Owner only)"
            >
              <Grid size={12} />
              <span>Compact</span>
            </button>
            <button
              className={`zoom-btn ${zoomMode === 'expanded' ? 'active' : ''}`}
              onClick={() => setZoomMode('expanded')}
              title="Expanded view (Full metadata)"
            >
              <List size={12} />
              <span>Expanded</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Board Scroll Area */}
      <div className="board-main-area">
        <div style={{ display: 'flex', flex: 1 }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Columns Header with WIP Limits */}
            <div className="board-columns-header">
              {STATUS_ORDER.map(status => {
                const count = colCounts[status] || 0;
                const limit = wipLimits[status] || 99;
                const isExceeded = count > limit;

                return (
                  <div key={status} className="board-col-header-cell">
                    <div className="col-title-row">
                      <div className="col-title-left">
                        <span className={`status-light status-light-${status}`} />
                        <span>{STATUS_LABELS[status]}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span className="col-count-badge">
                          {count} / {limit}
                        </span>
                      </div>
                    </div>

                    {/* WIP limit warning banner (red hatched if exceeded) */}
                    <div
                      className={`wip-limit-banner ${isExceeded ? 'exceeded' : ''}`}
                      title={isExceeded ? `WIP Limit Exceeded! (${count} > ${limit})` : `WIP Limit: ${limit}`}
                    />
                  </div>
                );
              })}
            </div>

            {/* Swimlanes List */}
            <div className="board-swimlanes">
              {swimlanes.map(lane => {
                const isCollapsed = collapsedLanes[lane.id];

                return (
                  <div key={lane.id} className="swimlane-row">
                    {/* Swimlane Header */}
                    <div className="swimlane-header" onClick={() => toggleLane(lane.id)}>
                      <div className="swimlane-header-left">
                        {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                        <span
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: lane.avatarColor
                          }}
                        />
                        <span>{lane.title}</span>
                        <span className="tab-count-badge">
                          {lane.tasks.length}
                        </span>
                      </div>
                    </div>

                    {/* Swimlane Columns Grid */}
                    {!isCollapsed && (
                      <div className="swimlane-grid">
                        {STATUS_ORDER.map(status => {
                          const laneColTasks = lane.tasks.filter(t => t.status === status);
                          const isDragOver = dragOverCol === status;

                          return (
                            <div
                              key={status}
                              className={`swimlane-cell ${isDragOver ? 'drag-over' : ''}`}
                              onDragOver={(e) => handleDragOver(e, status)}
                              onDrop={(e) => handleDrop(e, status)}
                            >
                              {laneColTasks.map(task => {
                                const isBlocked = task.status === 'blocked' || task.risk === 'critical';
                                const isClaimed = task.status === 'claimed_done' || task.status === 'needs_review';
                                const isVerified = task.status === 'verified_done';
                                const ownerColor = getOwnerColor(task.owner_member_id);

                                const cardClasses = [
                                  'kanban-card',
                                  zoomMode === 'compact' ? 'compact' : '',
                                  isBlocked ? 'card-blocked' : '',
                                  isClaimed ? 'card-claimed' : '',
                                  isVerified ? 'card-verified' : ''
                                ].filter(Boolean).join(' ');

                                return (
                                  <div
                                    key={task.key}
                                    className={cardClasses}
                                    draggable
                                    onDragStart={(e) => handleDragStart(e, task.key)}
                                    onClick={() => onSelectTask?.(task.key)}
                                  >
                                    {zoomMode === 'compact' ? (
                                      /* Compact zoom mode */
                                      <>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                          <span className="card-key">{task.key}</span>
                                          <span className="truncate font-medium text-xs" style={{ maxWidth: 110 }}>
                                            {task.title}
                                          </span>
                                        </div>
                                        <div
                                          style={{
                                            width: 18,
                                            height: 18,
                                            borderRadius: '50%',
                                            background: ownerColor,
                                            color: '#fff',
                                            fontSize: 9,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontWeight: 700
                                          }}
                                        >
                                          {getMemberName(snapshot, task.owner_member_id)?.[0] || 'U'}
                                        </div>
                                      </>
                                    ) : (
                                      /* Expanded zoom mode */
                                      <>
                                        <div className="card-top-row">
                                          <span className="card-key">{task.key}</span>
                                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                            {isBlocked && (
                                              <span className="pill pill-blocked" style={{ fontSize: 9, padding: '1px 4px' }}>
                                                BLOCKED
                                              </span>
                                            )}
                                            {isClaimed && (
                                              <span className="pill pill-claimed_done" style={{ fontSize: 9, padding: '1px 4px' }}>
                                                UNVERIFIED
                                              </span>
                                            )}
                                            <span className="font-mono text-xs text-muted">
                                              {task.effort || 4} pts
                                            </span>
                                          </div>
                                        </div>

                                        <div className="card-title">{task.title}</div>

                                        {task.blocker && (
                                          <div
                                            style={{
                                              fontSize: 10,
                                              color: 'var(--status-blocked)',
                                              background: 'rgba(240, 82, 74, 0.15)',
                                              padding: '3px 6px',
                                              borderRadius: 4
                                            }}
                                          >
                                            {task.blocker.description}
                                          </div>
                                        )}

                                        <div className="card-footer">
                                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            <div
                                              style={{
                                                width: 16,
                                                height: 16,
                                                borderRadius: '50%',
                                                background: ownerColor,
                                                color: '#fff',
                                                fontSize: 9,
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                fontWeight: 700
                                              }}
                                            >
                                              {getMemberName(snapshot, task.owner_member_id)?.[0] || 'U'}
                                            </div>
                                            <span className="text-muted text-xs">
                                              {getMemberName(snapshot, task.owner_member_id)}
                                            </span>
                                          </div>

                                          {task.verification && (
                                            <div
                                              style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 3,
                                                color: 'var(--status-verified_done)',
                                                fontSize: 10
                                              }}
                                              title={`Verification confidence: ${Math.round((task.verification.confidence || 0.9) * 100)}%`}
                                            >
                                              <CheckCircle2 size={11} />
                                              <span>{Math.round((task.verification.confidence || 0.9) * 100)}%</span>
                                            </div>
                                          )}
                                        </div>
                                      </>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Archived Column Collapsed Vertically on the Right */}
          <div
            className="archived-col-bar"
            onClick={() => {
              setShowArchived(!showArchived);
              addToast(showArchived ? 'Archived view closed' : 'No archived stories in current sprint', 'blue');
            }}
            title="Archived stories (collapsed)"
          >
            <Archive size={14} className="text-muted" style={{ marginBottom: 12 }} />
            <span className="archived-label-vertical">ARCHIVED (0)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useMemo } from 'react';
import { useParams, useOutletContext } from 'react-router-dom';
import { useSnapshot, getOwnerColor } from '../hooks/useSnapshot';
import {
  Calendar,
  ZoomIn,
  ZoomOut,
  ChevronDown,
  ChevronRight,
  Flag,
  AlertTriangle,
  Info
} from 'lucide-react';
import './Timeline.css';

// 6 time slots across the hackathon project schedule
const TIME_SLOTS = [
  { id: 'd1_m', label: 'Oct 16 08:00', date: '2026-10-16T08:00:00Z', x: 0 },
  { id: 'd1_a', label: 'Oct 16 14:00', date: '2026-10-16T14:00:00Z', x: 140 },
  { id: 'd1_e', label: 'Oct 16 20:00', date: '2026-10-16T20:00:00Z', x: 280 },
  { id: 'd2_m', label: 'Oct 17 08:00', date: '2026-10-17T08:00:00Z', x: 420 },
  { id: 'd2_a', label: 'Oct 17 14:00', date: '2026-10-17T14:00:00Z', x: 560 },
  { id: 'd2_e', label: 'Oct 17 20:00', date: '2026-10-17T20:00:00Z', x: 700 },
  { id: 'd3_m', label: 'Oct 18 08:00', date: '2026-10-18T08:00:00Z', x: 840 },
  { id: 'd3_e', label: 'Oct 18 16:00', date: '2026-10-18T16:00:00Z', x: 980 },
];

export default function Timeline() {
  const { code } = useParams();
  const { snapshot } = useSnapshot(code);
  const outletCtx = useOutletContext?.() || {};
  const [collapsedBlocks, setCollapsedBlocks] = useState({});
  const [slotWidth, setSlotWidth] = useState(140);
  const [selectedTaskKey, setSelectedTaskKey] = useState(null);

  const blocks = snapshot?.blocks || [];
  const tasks = snapshot?.tasks || [];
  const deps = snapshot?.deps || [];

  // Group tasks by block
  const groupedData = useMemo(() => {
    return blocks.map(block => {
      const blockTasks = tasks.filter(t => t.block_id === block.id);
      return { block, tasks: blockTasks };
    });
  }, [blocks, tasks]);

  const toggleBlock = (blockId) => {
    setCollapsedBlocks(prev => ({ ...prev, [blockId]: !prev[blockId] }));
  };

  const handleSelectTask = (key) => {
    setSelectedTaskKey(key);
    outletCtx?.onSelectTask?.(key);
  };

  // Map task index to x position on Gantt
  const getTaskGeometry = (task, idx) => {
    const startOffset = ((idx % 5) * 1.3) * slotWidth * 0.9;
    const durationSlots = Math.max(1, (task.effort || 4) / 4);
    const width = Math.min(360, durationSlots * slotWidth);
    const hasSlip = task.status === 'blocked' || task.risk === 'critical';
    const slipWidth = hasSlip ? 90 : 0;
    return { x: startOffset, width, hasSlip, slipWidth };
  };

  return (
    <div className="timeline-page">
      {/* Timeline Toolbar */}
      <div className="timeline-toolbar">
        <div className="timeline-title-cluster">
          <Calendar size={18} className="text-accent" />
          <div>
            <div className="font-semibold text-sm">Gantt Schedule & Ripple Analysis</div>
            <div className="text-xs text-muted">
              MS Project WBS • Critical Path & Projected Delay Slip
            </div>
          </div>
        </div>

        <div className="timeline-controls">
          <div className="kpi-chip" style={{ gap: 6 }}>
            <span className="status-light status-light-blocked" />
            <span className="text-xs">Slip Tail = Downstream Risk</span>
          </div>

          <button
            className="btn btn-sm btn-secondary"
            onClick={() => setSlotWidth(prev => Math.max(90, prev - 25))}
            title="Zoom Out"
            aria-label="Zoom out"
          >
            <ZoomOut size={13} />
          </button>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => setSlotWidth(prev => Math.min(220, prev + 25))}
            title="Zoom In"
            aria-label="Zoom in"
          >
            <ZoomIn size={13} />
          </button>
        </div>
      </div>

      {/* Split View Container */}
      <div className="timeline-split-view">
        {/* Left WBS Pane */}
        <div className="timeline-wbs-pane">
          <table className="wbs-table">
            <thead>
              <tr>
                <th style={{ width: 65 }}>ID</th>
                <th>Task Name</th>
                <th style={{ width: 50, textAlign: 'center' }}>%</th>
                <th style={{ width: 75 }}>Duration</th>
                <th style={{ width: 75 }}>Risk</th>
              </tr>
            </thead>
            <tbody>
              {groupedData.map(({ block, tasks: bTasks }) => {
                const isCollapsed = collapsedBlocks[block.id];
                return (
                  <React.Fragment key={block.id}>
                    {/* Block Group Header */}
                    <tr
                      className="wbs-block-header"
                      onClick={() => toggleBlock(block.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td colSpan={5} style={{ padding: '8px 10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                          <span>Block {block.id}: {block.name}</span>
                          <span className="tab-count-badge" style={{ marginLeft: 'auto' }}>
                            {bTasks.length} tasks
                          </span>
                        </div>
                      </td>
                    </tr>

                    {/* Block Tasks */}
                    {!isCollapsed && bTasks.map(task => {
                      const isSelected = selectedTaskKey === task.key;
                      const progress = task.status === 'verified_done' ? 100 : (task.progress || 0);

                      return (
                        <tr
                          key={task.key}
                          className={`wbs-row ${isSelected ? 'selected' : ''}`}
                          onClick={() => handleSelectTask(task.key)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td className="font-mono text-xs font-semibold text-accent">
                            {task.key}
                          </td>
                          <td>
                            <div className="truncate" style={{ maxWidth: 180 }} title={task.title}>
                              {task.title}
                            </div>
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <div className="progress-ring-container" title={`${progress}% complete`}>
                              <svg width="20" height="20" viewBox="0 0 24 24">
                                <circle
                                  cx="12"
                                  cy="12"
                                  r="9"
                                  stroke="var(--border)"
                                  strokeWidth="2.5"
                                  fill="none"
                                />
                                <circle
                                  cx="12"
                                  cy="12"
                                  r="9"
                                  stroke={task.status === 'verified_done' ? 'var(--status-verified_done)' : 'var(--accent)'}
                                  strokeWidth="2.5"
                                  strokeDasharray={56.5}
                                  strokeDashoffset={56.5 - (56.5 * progress) / 100}
                                  strokeLinecap="round"
                                  fill="none"
                                />
                              </svg>
                            </div>
                          </td>
                          <td className="font-mono text-xs">
                            {task.effort || 4}h
                          </td>
                          <td>
                            <span className={`pill pill-${task.status}`} style={{ fontSize: 10, padding: '1px 5px' }}>
                              {task.status.replace('_', ' ')}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Gantt Chart Pane */}
        <div className="timeline-gantt-pane">
          {/* Header Time Slots */}
          <div className="gantt-header-row" style={{ width: slotWidth * TIME_SLOTS.length }}>
            {TIME_SLOTS.map(slot => (
              <div
                key={slot.id}
                className="gantt-time-cell"
                style={{ width: slotWidth }}
              >
                {slot.label}
              </div>
            ))}
          </div>

          {/* Body with gridlines, today marker & task bars */}
          <div className="gantt-body-container" style={{ width: slotWidth * TIME_SLOTS.length }}>
            {/* Grid overlay */}
            <div className="gantt-grid-overlay">
              {TIME_SLOTS.map(slot => (
                <div
                  key={slot.id}
                  className="gantt-grid-col"
                  style={{ width: slotWidth }}
                />
              ))}
            </div>

            {/* Today marker (Red vertical indicator) */}
            <div
              className="gantt-today-line"
              style={{ left: slotWidth * 1.8 }}
            >
              <div className="gantt-today-badge">TODAY</div>
            </div>

            {/* Project start flag */}
            <div
              style={{
                position: 'absolute',
                top: 4,
                left: 6,
                zIndex: 15,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                color: 'var(--text-muted)'
              }}
            >
              <Flag size={11} className="text-accent" />
              <span>Project Kickoff</span>
            </div>

            {/* Render Rows */}
            {groupedData.map(({ block, tasks: bTasks }) => {
              const isCollapsed = collapsedBlocks[block.id];
              return (
                <React.Fragment key={block.id}>
                  {/* Block Group Space */}
                  <div className="gantt-task-row block-row" />

                  {/* Task Bars */}
                  {!isCollapsed && bTasks.map((task, idx) => {
                    const geo = getTaskGeometry(task, idx);
                    const ownerColor = getOwnerColor(task.owner_member_id);
                    const isMilestone = task.is_milestone || idx === bTasks.length - 1;

                    return (
                      <div key={task.key} className="gantt-task-row">
                        {isMilestone ? (
                          <div
                            className="gantt-milestone-diamond"
                            style={{ left: geo.x + geo.width }}
                            title={`Milestone: ${task.title}`}
                            onClick={() => handleSelectTask(task.key)}
                          />
                        ) : (
                          <>
                            {/* Main Task Bar */}
                            <div
                              className="gantt-bar"
                              style={{
                                left: geo.x,
                                width: geo.width,
                                background: ownerColor,
                              }}
                              onClick={() => handleSelectTask(task.key)}
                              title={`${task.key}: ${task.title} (${task.effort || 4}h)`}
                            >
                              <span style={{ fontWeight: 600, marginRight: 6 }}>{task.key}</span>
                              <span className="truncate">{task.title}</span>
                            </div>

                            {/* Red Slip Tail if Blocked or Critical Risk */}
                            {geo.hasSlip && (
                              <div
                                className="gantt-slip-tail"
                                style={{
                                  left: geo.x + geo.width,
                                  width: geo.slipWidth,
                                }}
                                title="Projected downstream slip (+3.5h delay)"
                              />
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

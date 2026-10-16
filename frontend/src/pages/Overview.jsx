import React, { useState, useEffect } from 'react';
import { useParams, Link, useOutletContext } from 'react-router-dom';
import { useSnapshot, getOwnerColor } from '../hooks/useSnapshot';
import {
  Activity,
  AlertOctagon,
  Clock,
  CheckCircle2,
  Calendar as CalIcon,
  Send,
  Sparkles,
  ChevronRight,
  TrendingDown,
  AlertTriangle
} from 'lucide-react';
import './Overview.css';

export default function Overview() {
  const { code } = useParams();
  const { snapshot } = useSnapshot(code);
  const outletCtx = useOutletContext?.() || {};

  const tasks = snapshot?.tasks || [];
  const members = snapshot?.members || [];
  const contradictions = snapshot?.contradictions || [];
  const project = snapshot?.project || {};

  // Compute effort points
  const totalPoints = tasks.reduce((acc, t) => acc + (t.effort || 4), 0);
  const verifiedPoints = tasks
    .filter(t => t.status === 'verified_done')
    .reduce((acc, t) => acc + (t.effort || 4), 0);
  const claimedPoints = tasks
    .filter(t => t.status === 'claimed_done' || t.status === 'needs_review')
    .reduce((acc, t) => acc + (t.effort || 4), 0);
  const blockedPoints = tasks
    .filter(t => t.status === 'blocked')
    .reduce((acc, t) => acc + (t.effort || 4), 0);
  const inProgressPoints = tasks
    .filter(t => t.status === 'in_progress')
    .reduce((acc, t) => acc + (t.effort || 4), 0);

  const completionPct = totalPoints > 0 ? Math.round((verifiedPoints / totalPoints) * 100) : 0;

  // Countdown timer to hackathon deadline
  const [timeLeft, setTimeLeft] = useState('21h : 42m : 18s');
  useEffect(() => {
    const timer = setInterval(() => {
      const target = new Date(project.ends_at || '2026-10-18T18:00:00Z').getTime();
      const now = Date.now();
      const diff = Math.max(0, target - now);
      const h = Math.floor(diff / (1000 * 60 * 60));
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const s = Math.floor((diff % (1000 * 60)) / 1000);
      setTimeLeft(`${h}h : ${m.toString().padStart(2, '0')}m : ${s.toString().padStart(2, '0')}s`);
    }, 1000);
    return () => clearInterval(timer);
  }, [project.ends_at]);

  // Burndown points calculation (8 sprint slots)
  const burndownData = [
    { slot: 'Day 1 AM', ideal: 100, actual: 100 },
    { slot: 'Day 1 PM', ideal: 85, actual: 92 },
    { slot: 'Day 1 Eve', ideal: 70, actual: 80 },
    { slot: 'Day 2 AM', ideal: 55, actual: 68 }, // Behind ideal (red dot)
    { slot: 'Day 2 PM', ideal: 40, actual: 48 },
    { slot: 'Day 2 Eve', ideal: 25, actual: 30 },
    { slot: 'Day 3 AM', ideal: 10, actual: 12 },
    { slot: 'Final Demo', ideal: 0, actual: 0 }
  ];

  // Group tasks into "Today" and "Tomorrow" horizons
  const todayTasks = tasks.slice(0, 4);
  const tomorrowTasks = tasks.slice(4, 8);

  return (
    <div className="overview-page">
      {/* Open Contradiction Alert Banner (if any) */}
      {contradictions.length > 0 && (
        <div className="contradiction-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertOctagon size={18} style={{ color: 'var(--status-blocked)' }} />
            <div>
              <div className="font-semibold text-xs text-primary" style={{ textTransform: 'uppercase' }}>
                Telegram Contradiction Detected ({contradictions[0].task_ids.join(' & ')})
              </div>
              <div className="text-xs text-secondary" style={{ marginTop: 2 }}>
                {contradictions[0].summary}
              </div>
            </div>
          </div>
          <Link to={`/p/${code}/guide`} className="btn btn-sm btn-secondary">
            Reconcile via Guide Radar
          </Link>
        </div>
      )}

      {/* 1. Taiga Scrum Progress Strip */}
      <div className="taiga-strip">
        <div className="taiga-strip-top">
          <div className="taiga-strip-bar-wrap">
            <span className="caps-label">Sprint Progress</span>
            <div className="taiga-progress-bar">
              <div
                className="taiga-bar-fill taiga-bar-verified"
                style={{ width: `${(verifiedPoints / totalPoints) * 100}%` }}
                title={`Verified: ${verifiedPoints} pts`}
              />
              <div
                className="taiga-bar-fill taiga-bar-claimed"
                style={{ width: `${(claimedPoints / totalPoints) * 100}%` }}
                title={`Claimed / Review: ${claimedPoints} pts`}
              />
              <div
                className="taiga-bar-fill taiga-bar-progress"
                style={{ width: `${(inProgressPoints / totalPoints) * 100}%` }}
                title={`In Progress: ${inProgressPoints} pts`}
              />
              <div
                className="taiga-bar-fill taiga-bar-blocked"
                style={{ width: `${(blockedPoints / totalPoints) * 100}%` }}
                title={`Blocked: ${blockedPoints} pts`}
              />
            </div>
            <span className="font-mono text-sm font-semibold text-primary">{completionPct}%</span>
          </div>

          <div className="taiga-readouts">
            <div className="taiga-readout-item">
              <span className="taiga-readout-val" style={{ color: 'var(--status-verified_done)' }}>
                {verifiedPoints}
              </span>
              <span className="taiga-readout-label">Verified Pts</span>
            </div>
            <div className="taiga-readout-item">
              <span className="taiga-readout-val" style={{ color: 'var(--status-claimed_done)' }}>
                {claimedPoints}
              </span>
              <span className="taiga-readout-label">Claimed</span>
            </div>
            <div className="taiga-readout-item">
              <span className="taiga-readout-val" style={{ color: 'var(--status-blocked)' }}>
                {blockedPoints}
              </span>
              <span className="taiga-readout-label">Blocked</span>
            </div>
            <div className="taiga-readout-item">
              <span className="taiga-readout-val text-muted">
                {totalPoints}
              </span>
              <span className="taiga-readout-label">Total Effort</span>
            </div>
          </div>
        </div>

        {/* Taiga Burndown Chart */}
        <div className="taiga-burndown-card">
          <div className="burndown-header">
            <div>
              <span className="font-semibold text-xs">Sprint Burndown</span>
              <span className="text-xs text-muted" style={{ marginLeft: 8 }}>
                Ideal Burndown vs. Actual Verified Points
              </span>
            </div>
            <div className="burndown-legend">
              <div className="legend-item">
                <span className="legend-line-ideal" />
                <span className="text-muted">Ideal</span>
              </div>
              <div className="legend-item">
                <span className="legend-line-actual" />
                <span style={{ color: 'var(--status-verified_done)' }}>Actual</span>
              </div>
              <div className="legend-item">
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-blocked)' }} />
                <span style={{ color: 'var(--status-blocked)' }}>Slip Point</span>
              </div>
            </div>
          </div>

          {/* SVG Burndown curve */}
          <div style={{ width: '100%', height: 110, position: 'relative' }}>
            <svg width="100%" height="100%" viewBox="0 0 600 110" preserveAspectRatio="none">
              <defs>
                <linearGradient id="burndownGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--status-verified_done)" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="var(--status-verified_done)" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Gridlines */}
              <line x1="0" y1="20" x2="600" y2="20" stroke="var(--border-subtle)" strokeDasharray="3 3" />
              <line x1="0" y1="55" x2="600" y2="55" stroke="var(--border-subtle)" strokeDasharray="3 3" />
              <line x1="0" y1="90" x2="600" y2="90" stroke="var(--border-subtle)" strokeDasharray="3 3" />

              {/* Ideal dashed line */}
              <line x1="20" y1="15" x2="580" y2="95" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="4 4" />

              {/* Actual area fill */}
              <polygon
                points="20,15 95,22 175,32 255,42 340,60 420,74 505,86 580,95 580,105 20,105"
                fill="url(#burndownGrad)"
              />

              {/* Actual line */}
              <polyline
                points="20,15 95,22 175,32 255,42 340,60 420,74 505,86 580,95"
                fill="none"
                stroke="var(--status-verified_done)"
                strokeWidth="2.5"
              />

              {/* Slippage Red Point where actual falls behind ideal */}
              <circle cx="255" cy="42" r="5" fill="var(--status-blocked)" stroke="#fff" strokeWidth="1.5" />
            </svg>
          </div>
        </div>
      </div>

      {/* 2. Planti Dashboard Layout Grid */}
      <div className="planti-grid">
        {/* Left column: Tiles, Hero Donut & Horizon */}
        <div className="planti-left-col">
          {/* Planti Soft KPI Tiles */}
          <div className="planti-tiles-row">
            <div className="planti-tile">
              <span className="planti-tile-num text-accent">14</span>
              <span className="planti-tile-label">Check-ins Sent Today</span>
            </div>
            <div className="planti-tile">
              <span className="planti-tile-num" style={{ color: 'var(--status-verified_done)' }}>4</span>
              <span className="planti-tile-label">Verified Tasks</span>
            </div>
            <div className="planti-tile">
              <span className="planti-tile-num text-secondary">11</span>
              <span className="planti-tile-label">Due This Sprint</span>
            </div>
            <div className="planti-tile">
              <span className="planti-tile-num" style={{ color: 'var(--status-blocked)' }}>2</span>
              <span className="planti-tile-label">Active Blockers</span>
            </div>
          </div>

          {/* Planti Hero Donut Card */}
          <div className="planti-hero-card">
            <div className="planti-hero-text">
              <h3>Sprint Delivery Velocity</h3>
              <p>
                {completionPct}% of planned effort verified against GitHub commits.
                Telegram verification loop active for 4 builders.
              </p>
              <div style={{ marginTop: 14 }}>
                <Link to={`/p/${code}/plan`} className="btn btn-sm btn-primary">
                  Review Sprint Plan
                </Link>
              </div>
            </div>

            {/* Donut Chart SVG */}
            <div style={{ width: 100, height: 100, position: 'relative', flexShrink: 0 }}>
              <svg width="100" height="100" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--border)"
                  strokeWidth="3.5"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="3.5"
                  strokeDasharray={`${completionPct}, 100`}
                />
              </svg>
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: 16,
                  fontFamily: 'Geist Mono'
                }}
              >
                {completionPct}%
              </div>
            </div>
          </div>

          {/* Planti Grouped Task Horizon: Today & Tomorrow */}
          <div className="planti-horizon-card">
            <div className="horizon-section-title">Focus Horizon: Today</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {todayTasks.map(t => {
                const ownerColor = getOwnerColor(t.owner_member_id);
                return (
                  <div
                    key={t.key}
                    className="horizon-task-row"
                    onClick={() => outletCtx?.onSelectTask?.(t.key)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: ownerColor
                        }}
                      />
                      <span className="font-mono text-xs text-accent">{t.key}</span>
                      <span className="font-medium text-xs">{t.title}</span>
                    </div>

                    <div className="horizon-meta-line">
                      <span className={`pill pill-${t.status}`} style={{ fontSize: 10, padding: '1px 5px' }}>
                        {t.status.replace('_', ' ')}
                      </span>
                      <span className="text-muted text-xs">Awaiting reply 2h</span>
                      <ChevronRight size={13} className="text-muted" />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="horizon-section-title" style={{ marginTop: 8 }}>Horizon: Tomorrow</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {tomorrowTasks.map(t => {
                const ownerColor = getOwnerColor(t.owner_member_id);
                return (
                  <div
                    key={t.key}
                    className="horizon-task-row"
                    onClick={() => outletCtx?.onSelectTask?.(t.key)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: ownerColor
                        }}
                      />
                      <span className="font-mono text-xs text-accent">{t.key}</span>
                      <span className="font-medium text-xs">{t.title}</span>
                    </div>

                    <div className="horizon-meta-line">
                      <span className={`pill pill-${t.status}`} style={{ fontSize: 10, padding: '1px 5px' }}>
                        {t.status.replace('_', ' ')}
                      </span>
                      <span className="text-muted text-xs">Verified 10m ago</span>
                      <ChevronRight size={13} className="text-muted" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right column: Calendar Widget & Live Countdown */}
        <div className="planti-right-col">
          {/* Live Countdown Card */}
          <div className="countdown-card">
            <span className="caps-label">Time to Final Submission</span>
            <div className="countdown-timer">{timeLeft}</div>
            <span className="text-xs text-muted">Kurukshetra Hackathon 2026</span>
          </div>

          {/* Planti Calendar Widget */}
          <div className="planti-calendar-card">
            <div className="calendar-header">
              <span>October 2026</span>
              <CalIcon size={14} className="text-muted" />
            </div>

            <div className="calendar-days-grid">
              <div className="cal-day-header">M</div>
              <div className="cal-day-header">T</div>
              <div className="cal-day-header">W</div>
              <div className="cal-day-header">T</div>
              <div className="cal-day-header">F</div>
              <div className="cal-day-header">S</div>
              <div className="cal-day-header">S</div>

              <div className="cal-day-num">12</div>
              <div className="cal-day-num">13</div>
              <div className="cal-day-num">14</div>
              <div className="cal-day-num">15</div>
              <div className="cal-day-num today" title="Today">16</div>
              <div className="cal-day-num has-deadline" title="Checkpoint 1">17</div>
              <div className="cal-day-num has-deadline" title="Final Submission">18</div>
            </div>
          </div>

          {/* Top Project Risks */}
          <div className="flight-panel" style={{ padding: 14 }}>
            <div className="caps-label" style={{ marginBottom: 10, color: 'var(--status-blocked)' }}>
              Top Operational Risks
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div className="flight-panel-raised" style={{ padding: '8px 10px', fontSize: 11 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
                  <AlertTriangle size={12} style={{ color: 'var(--status-blocked)' }} />
                  <span>T-2: Payment Gateway Blocked</span>
                </div>
                <div className="text-muted" style={{ marginTop: 4 }}>
                  Waiting on webhook endpoint from Aarav. Downstream slip: 3.5h.
                </div>
              </div>

              <div className="flight-panel-raised" style={{ padding: '8px 10px', fontSize: 11 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
                  <AlertTriangle size={12} style={{ color: 'var(--status-claimed_done)' }} />
                  <span>T-4: Partial Test Coverage</span>
                </div>
                <div className="text-muted" style={{ marginTop: 4 }}>
                  65% confidence verification. Telegram receipt integration unverified.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

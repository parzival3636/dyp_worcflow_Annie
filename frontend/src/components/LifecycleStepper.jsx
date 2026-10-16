import { NavLink, useParams } from 'react-router-dom';
import { Check, Search, Moon, Sun, MoreHorizontal, Activity, Layers, Calendar, GitFork, BarChart3, Clock, AlertTriangle } from 'lucide-react';
import './LifecycleStepper.css';

const LIFECYCLE_STAGES = [
  { id: 'planning', label: 'Planning', order: 1 },
  { id: 'assigned', label: 'Assigned', order: 2 },
  { id: 'running', label: 'Running', order: 3 },
  { id: 'verifying', label: 'Verifying', order: 4 },
  { id: 'closed', label: 'Closed', order: 5 },
];

export default function LifecycleStepper({
  snapshot,
  theme,
  onToggleTheme,
  onOpenCmdk,
  onOpenDemoMenu
}) {
  const { code } = useParams();
  const tasks = snapshot?.tasks || [];
  const project = snapshot?.project || {};

  // Compute stats
  const totalTasks = tasks.length || 1;
  const verifiedTasks = tasks.filter(t => t.status === 'verified_done').length;
  const blockedTasks = tasks.filter(t => t.status === 'blocked').length;
  const percentComplete = Math.round((verifiedTasks / totalTasks) * 100);

  // Overall health assessment
  let healthLabel = 'Healthy (Green)';
  let healthClass = 'ok';
  if (blockedTasks > 1 || tasks.some(t => t.risk === 'critical')) {
    healthLabel = 'Critical (Red)';
    healthClass = 'critical';
  } else if (blockedTasks === 1 || tasks.some(t => t.risk === 'at_risk')) {
    healthLabel = 'At Risk (Amber)';
    healthClass = 'at_risk';
  }

  // Active lifecycle stage
  const currentStage = project.status === 'done'
    ? 'closed'
    : project.status === 'running'
      ? 'running'
      : 'planning';

  const currentOrder = LIFECYCLE_STAGES.find(s => s.id === currentStage)?.order || 3;

  return (
    <div className="lifecycle-container">
      {/* Top row: Stepper + Health KPI + Controls */}
      <div className="lifecycle-top-row">
        {/* Stepper nodes */}
        <div className="lifecycle-stepper">
          {LIFECYCLE_STAGES.map((stage, idx) => {
            const isCompleted = stage.order < currentOrder;
            const isActive = stage.order === currentOrder;
            const nodeClass = `step-node ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`;

            return (
              <div key={stage.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className={nodeClass} title={`Stage: ${stage.label}`}>
                  <div className="step-circle">
                    {isCompleted ? <Check size={11} strokeWidth={2.5} /> : stage.order}
                  </div>
                  <span>{stage.label}</span>
                </div>
                {idx < LIFECYCLE_STAGES.length - 1 && (
                  <div className={`step-connector ${isCompleted ? 'completed' : ''}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Right side: KPI block & Controls */}
        <div className="lifecycle-actions">
          {/* Health & completion KPI */}
          <div className="lifecycle-kpi-block">
            <div className="kpi-chip" title="Overall Project Health Status">
              <span className={`kpi-health-dot ${healthClass}`} />
              <span className="text-secondary font-mono text-xs">{healthLabel}</span>
            </div>

            <div className="kpi-chip" title="Verified Task Completion">
              <span className="text-muted text-xs">Progress:</span>
              <span className="text-primary font-mono text-xs font-semibold">{percentComplete}%</span>
            </div>
          </div>

          {/* Quick command search */}
          <button
            className="cmd-trigger-btn"
            onClick={onOpenCmdk}
            aria-label="Open command palette"
          >
            <Search size={13} />
            <span>Search / Commands</span>
            <span className="cmd-kbd">⌘K</span>
          </button>

          {/* Theme switcher (Dark linear vs Warm paper) */}
          <button
            className="theme-toggle-btn"
            onClick={onToggleTheme}
            title={theme === 'dark' ? 'Switch to Warm Paper theme' : 'Switch to Flight Deck Dark theme'}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>

          {/* Demo menu button */}
          <button
            className="theme-toggle-btn"
            onClick={onOpenDemoMenu}
            title="Demo actions & overrides"
            aria-label="Open demo controls"
          >
            <MoreHorizontal size={14} />
          </button>
        </div>
      </div>

      {/* Bottom row: Horizontal tab strip for the project */}
      <nav className="lifecycle-tab-strip" aria-label="Project tabs">
        <NavLink
          to={`/p/${code}/overview`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <Activity size={13} />
          <span>Overview</span>
        </NavLink>

        <NavLink
          to={`/p/${code}`}
          end
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <Layers size={13} />
          <span>Board</span>
          <span className="tab-count-badge">{tasks.length}</span>
        </NavLink>

        <NavLink
          to={`/p/${code}/plan`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <Clock size={13} />
          <span>Plan & Backlog</span>
        </NavLink>

        <NavLink
          to={`/p/${code}/timeline`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <Calendar size={13} />
          <span>Timeline (Gantt)</span>
        </NavLink>

        <NavLink
          to={`/p/${code}/graph`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <GitFork size={13} />
          <span>Graph (DAG)</span>
        </NavLink>

        <NavLink
          to={`/p/${code}/contributions`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <BarChart3 size={13} />
          <span>Contributions</span>
        </NavLink>

        <NavLink
          to={`/p/${code}/activity`}
          className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
        >
          <Clock size={13} />
          <span>Activity</span>
        </NavLink>

        {blockedTasks > 0 && (
          <NavLink
            to={`/p/${code}/guide`}
            className={({ isActive }) => `tab-strip-item ${isActive ? 'active' : ''}`}
            style={{ color: 'var(--status-blocked)' }}
          >
            <AlertTriangle size={13} />
            <span>Risks & Blockers</span>
            <span
              className="tab-count-badge"
              style={{
                background: 'var(--status-blocked-bg)',
                color: 'var(--status-blocked)',
                borderColor: 'var(--status-blocked)'
              }}
            >
              {blockedTasks}
            </span>
          </NavLink>
        )}
      </nav>
    </div>
  );
}

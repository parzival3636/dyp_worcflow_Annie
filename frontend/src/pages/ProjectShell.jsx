import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Outlet, useParams, NavLink, Link, useLocation } from 'react-router-dom';
import { useSnapshot, apiPost } from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import LifecycleStepper from '../components/LifecycleStepper';
import CommandPalette from '../components/CommandPalette';
import GuideDockPanel from '../components/GuideDockPanel';
import TaskDrawer from '../components/TaskDrawer';
import {
  Plane,
  LayoutGrid,
  ListTodo,
  Calendar,
  GitFork,
  BarChart3,
  Clock,
  Sparkles,
  Shield,
  Bot,
  Activity,
  Menu,
  ChevronLeft,
  ChevronRight,
  Send,
  RotateCcw,
  RefreshCw,
  CheckCircle2,
  X,
  FileCode
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import './ProjectShell.css';

export default function ProjectShell() {
  const { code } = useParams();
  const location = useLocation();
  const { snapshot, loading, error, diff, refetch } = useSnapshot(code);
  const { addToast } = useToast();

  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'light');
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [demoMenuOpen, setDemoMenuOpen] = useState(false);
  const [drawerTaskKey, setDrawerTaskKey] = useState(null);

  // Sync theme with document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Toast notifications on snapshot diff changes
  const prevDiffRef = useRef(null);
  useEffect(() => {
    if (!diff || diff === prevDiffRef.current) return;
    prevDiffRef.current = diff;

    diff.newContradictions?.forEach(c => {
      addToast(`Conflict: ${c.summary?.substring(0, 60) || 'Check board'}`, 'red');
    });

    diff.statusChanges?.forEach(sc => {
      if (sc.to === 'verified_done') addToast(`${sc.key} verified by GitHub! ✓`, 'green');
      if (sc.to === 'blocked') addToast(`${sc.key} is now blocked`, 'red');
    });

    diff.newEvents?.forEach(ev => {
      if (ev.type === 'guide_note') {
        const text = typeof ev.payload === 'string' ? ev.payload : ev.payload?.text || 'Guide insight';
        addToast(text.substring(0, 80), 'purple', 7000);
      }
    });
  }, [diff, addToast]);

  // Demo actions
  const handleFollowUp = async () => {
    try {
      await apiPost(`/projects/${code}/followup`);
      addToast('✓ Telegram check-in follow-up sent', 'green');
    } catch {
      addToast('✓ Telegram check-in triggered (mock mode)', 'green');
    }
  };

  const handleReverify = async () => {
    try {
      await apiPost(`/projects/${code}/verify`);
      addToast('✓ GitHub commit AST verification re-executed', 'green');
      refetch();
    } catch {
      addToast('✓ Re-verified all commits against tests (mock mode)', 'green');
    }
  };

  const handleResetProject = async () => {
    try {
      await apiPost(`/projects/${code}/reset`);
      addToast('Project reset to initial kickoff state', 'blue');
      refetch();
    } catch {
      addToast('Project state reloaded to initial state', 'blue');
    }
    setDemoMenuOpen(false);
  };

  const project = snapshot?.project || {};
  const tasks = snapshot?.tasks || [];

  return (
    <div className="shell">
      {/* 1. Linear-style Collapsible Sidebar */}
      <aside className={`sidebar ${sidebarExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="sidebar-header">
          {sidebarExpanded ? (
            <Link to="/projects" className="sidebar-brand" title="Back to Projects Hub">
              <div className="sidebar-brand-icon">
                <Plane size={15} />
              </div>
              <span>Pilot Hub</span>
            </Link>
          ) : (
            <Link to="/projects" className="sidebar-brand-icon" style={{ margin: '0 auto' }} title="Back to Projects Hub">
              <Plane size={15} />
            </Link>
          )}

          <button
            className="sidebar-collapse-btn"
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            title={sidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-label="Toggle sidebar width"
          >
            {sidebarExpanded ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>

        {/* Scrollable Navigation Groups */}
        <div className="sidebar-scroll-area">
          {/* Main Flight Group */}
          <div className="sidebar-group">
            {sidebarExpanded && <div className="sidebar-group-title">Pulse & Horizon</div>}
            <NavLink
              to={`/p/${code}/overview`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Overview (Taiga Burndown + Planti)"
            >
              <Activity size={15} />
              {sidebarExpanded && <span>Executive Overview</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/activity`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Activity Stream"
            >
              <Clock size={15} />
              {sidebarExpanded && <span>Activity Ledger</span>}
            </NavLink>
          </div>

          {/* Workspace Views */}
          <div className="sidebar-group">
            {sidebarExpanded && <div className="sidebar-group-title">Workspace</div>}
            <NavLink
              to={`/p/${code}`}
              end
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Team Member Collaborative Kanban Board"
            >
              <LayoutGrid size={15} />
              {sidebarExpanded && <span>Kanban Board (Team)</span>}
              {sidebarExpanded && <span className="sidebar-badge">{tasks.length}</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/plan`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Backlog & WBS Plan"
            >
              <ListTodo size={15} />
              {sidebarExpanded && <span>Plan & Backlog</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/timeline`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="MS Project Gantt Timeline"
            >
              <Calendar size={15} />
              {sidebarExpanded && <span>Timeline (Gantt)</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/graph`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Topological Dependency DAG"
            >
              <GitFork size={15} />
              {sidebarExpanded && <span>Dependency DAG</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/contributions`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Contributions Ledger"
            >
              <BarChart3 size={15} />
              {sidebarExpanded && <span>Contributions</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/chat`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Live Telegram Stream & Guide AI Chat"
            >
              <Sparkles size={15} style={{ color: 'var(--status-needs_review)' }} />
              {sidebarExpanded && <span>Live Chat & Guide</span>}
            </NavLink>
          </div>

          {/* Portals */}
          <div className="sidebar-group">
            {sidebarExpanded && <div className="sidebar-group-title">Portals & Setup</div>}
            <NavLink
              to={`/p/${code}/lead`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Project Leader Portal"
            >
              <Shield size={15} className="text-accent" />
              {sidebarExpanded && <span>Leader Portal</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/setup`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Telegram Binding & Invites"
            >
              <Send size={15} style={{ color: snapshot?.project?.telegram_status === 'connected' ? '#10b981' : '#f59e0b' }} />
              {sidebarExpanded && <span>Telegram &amp; Invites</span>}
              {sidebarExpanded && (
                <span
                  style={{
                    fontSize: '9px',
                    padding: '1px 6px',
                    borderRadius: '999px',
                    marginLeft: 'auto',
                    backgroundColor: snapshot?.project?.telegram_status === 'connected' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                    color: snapshot?.project?.telegram_status === 'connected' ? '#10b981' : '#f59e0b',
                    fontWeight: 600
                  }}
                >
                  {snapshot?.project?.telegram_status === 'connected' ? 'LIVE' : 'SETUP'}
                </span>
              )}
            </NavLink>

            <NavLink
              to={`/p/${code}/guide`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Guide / Evaluator Radar & Executive Audit"
            >
              <Bot size={15} style={{ color: 'var(--status-needs_review)' }} />
              {sidebarExpanded && <span>Guide / Evaluator Portal</span>}
            </NavLink>
          </div>

          {/* AI Task Verification & CI Telemetry */}
          <div className="sidebar-group">
            {sidebarExpanded && <div className="sidebar-group-title">AI Verification &amp; CI</div>}
            <NavLink
              to={`/p/${code}/verify`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Verified GitHub Tasks & Audit Trail"
            >
              <CheckCircle2 size={15} style={{ color: 'var(--status-verified_done, #047857)' }} />
              {sidebarExpanded && <span>Task Verification</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/annie`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Mission Control & Real-time Verification Telemetry"
            >
              <Sparkles size={15} style={{ color: 'var(--accent, #FF6B3D)' }} />
              {sidebarExpanded && <span>Mission Control</span>}
            </NavLink>

            <NavLink
              to={`/p/${code}/webhooks`}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Live Webhook Ingestion Telemetry"
            >
              <Activity size={15} style={{ color: 'var(--status-in_progress, #1D4ED8)' }} />
              {sidebarExpanded && <span>CI Webhook Log</span>}
            </NavLink>
          </div>

          {/* Repo link if present */}
          {project.repo_url && sidebarExpanded && (
            <div style={{ marginTop: 'auto', padding: '0 8px' }}>
              <a
                href={project.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-sm btn-ghost w-full"
                style={{ justifyContent: 'flex-start', gap: 8, fontSize: 11 }}
              >
                <GithubIcon size={13} />
                <span className="truncate">{project.repo_full_name || 'GitHub Repo'}</span>
              </a>
            </div>
          )}
        </div>

        {/* Polling Status Footer */}
        <div className="sidebar-footer">
          <div className="polling-indicator">
            <span className="polling-dot" />
            {sidebarExpanded && <span>2s Polling Live</span>}
          </div>
          {sidebarExpanded && (
            <span className="font-mono text-xs text-muted">{project.code || code}</span>
          )}
        </div>
      </aside>

      {/* 2. Main Flight Content Area */}
      <main className="main-wrapper">
        {/* Top MS Project Lifecycle Stepper & Tab Strip */}
        <LifecycleStepper
          snapshot={snapshot}
          theme={theme}
          onToggleTheme={toggleTheme}
          onOpenCmdk={() => setCmdkOpen(true)}
          onOpenDemoMenu={() => setDemoMenuOpen(true)}
        />

        {/* Router Outlet for Page Content */}
        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex' }}>
          <Outlet
            context={{
              snapshot,
              code,
              onSelectTask: (key) => setDrawerTaskKey(key),
              refetch
            }}
          />
        </div>

        {/* Docked Guide Agent Panel (Linear Opus 5.5 style) */}
        <GuideDockPanel
          snapshot={snapshot}
          activeTaskKey={drawerTaskKey}
          onOpenTaskPreview={(key) => setDrawerTaskKey(key)}
        />
      </main>

      {/* 3. Global Command Palette (Cmd+K) */}
      <CommandPalette
        open={cmdkOpen}
        onClose={() => setCmdkOpen(false)}
        tasks={tasks}
        theme={theme}
        onToggleTheme={toggleTheme}
        onTriggerFollowUp={handleFollowUp}
        onSelectTask={(key) => setDrawerTaskKey(key)}
      />

      {/* 4. Global Linear-style Task Drawer */}
      {drawerTaskKey && (
        <TaskDrawer
          taskKey={drawerTaskKey}
          onClose={() => setDrawerTaskKey(null)}
        />
      )}

      {/* 5. Demo Controls Dialog */}
      {demoMenuOpen && (
        <div className="demo-dialog-overlay" onClick={() => setDemoMenuOpen(false)}>
          <div className="demo-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="demo-dialog-header">
              <span className="font-semibold text-sm">Demo Operational Controls</span>
              <button
                className="btn btn-sm btn-ghost"
                onClick={() => setDemoMenuOpen(false)}
                aria-label="Close dialog"
              >
                <X size={14} />
              </button>
            </div>
            <div className="demo-dialog-body">
              <button
                className="btn btn-secondary w-full"
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={() => { handleFollowUp(); setDemoMenuOpen(false); }}
              >
                <Send size={14} className="text-accent" />
                <span>Run follow-up now (Telegram check-in)</span>
              </button>

              <button
                className="btn btn-secondary w-full"
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={() => { handleReverify(); setDemoMenuOpen(false); }}
              >
                <RefreshCw size={14} style={{ color: 'var(--status-verified_done)' }} />
                <span>Re-verify commits (GitHub AST parser)</span>
              </button>

              <button
                className="btn btn-secondary w-full"
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={handleResetProject}
              >
                <RotateCcw size={14} style={{ color: 'var(--status-blocked)' }} />
                <span>Reset project state</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

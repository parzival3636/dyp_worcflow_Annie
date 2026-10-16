import { Outlet, useParams, NavLink, Link } from 'react-router-dom';
import { useSnapshot, useHealth, getOwnerColor } from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import { useState, useEffect, useRef, useCallback } from 'react';
import { apiPost } from '../hooks/useSnapshot';
import {
  LayoutGrid, ListTodo, GitFork, BarChart3, Clock, Sparkles,
  Plane, Users, Loader2, CheckCircle, AlertCircle,
  Send, Zap, Cpu
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import './ProjectShell.css';

const NAV_ITEMS = [
  { path: '', label: 'Board', icon: LayoutGrid, end: true },
  { path: 'plan', label: 'Plan', icon: ListTodo },
  { path: 'graph', label: 'Graph', icon: GitFork },
  { path: 'contributions', label: 'Contributions', icon: BarChart3 },
  { path: 'activity', label: 'Activity', icon: Clock },
  { path: 'chat', label: 'Guide Chat', icon: Sparkles, purple: true },
];

export default function ProjectShell() {
  const { code } = useParams();
  const { snapshot, loading, error, diff } = useSnapshot(code);
  const health = useHealth();
  const { addToast } = useToast();
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const prevDiffRef = useRef(null);

  // Toast on diff changes
  useEffect(() => {
    if (!diff || diff === prevDiffRef.current) return;
    prevDiffRef.current = diff;

    diff.newContradictions?.forEach(c => {
      addToast(`Contradiction detected: ${c.summary?.substring(0, 60) || 'Check board'}`, 'red');
    });

    diff.statusChanges?.forEach(sc => {
      if (sc.to === 'verified_done') addToast(`${sc.key} verified! ✓`, 'green');
      if (sc.to === 'blocked') addToast(`${sc.key} is now blocked`, 'red');
    });

    diff.newEvents?.forEach(ev => {
      if (ev.type === 'guide_note') {
        const note = typeof ev.payload === 'string' ? ev.payload : ev.payload?.text || 'New insight';
        addToast(note.substring(0, 80), 'purple', 8000);
      }
      if (ev.type === 'blocker_resolved') addToast(`Blocker resolved on ${ev.task_id || ''}`, 'green');
    });
  }, [diff, addToast]);

  const handleFollowUp = useCallback(async () => {
    setFollowUpLoading(true);
    try {
      await apiPost(`/projects/${code}/followup`);
      addToast('✓ Check-ins sent', 'green');
    } catch {
      addToast('Failed to send check-ins', 'red');
    } finally {
      setTimeout(() => setFollowUpLoading(false), 2000);
    }
  }, [code, addToast]);

  if (loading && !snapshot) {
    return (
      <div className="shell-loading">
        <Loader2 size={32} className="animate-pulse text-blue" />
        <p className="text-muted" style={{ marginTop: 12 }}>Loading project…</p>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className="shell-loading">
        <AlertCircle size={32} className="text-red" />
        <p className="text-red" style={{ marginTop: 12 }}>Cannot reach backend — retrying…</p>
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    );
  }

  const project = snapshot?.project || {};
  const members = snapshot?.members || [];
  const contradictions = snapshot?.contradictions || [];
  const isLead = members.some(m => m.role === 'lead'); // simplified: show lead controls by default for demo

  const statusPillClass = {
    planning: 'pill-blue',
    running: 'pill-green',
    done: 'pill-muted',
  };

  return (
    <div className="shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-top">
          {/* Project identity */}
          <div className="sidebar-project">
            <div className="sidebar-project-name truncate font-semibold text-md">
              {project.name || code}
            </div>
            <div className="font-mono text-xs text-muted" style={{ marginTop: 2 }}>
              {project.code || code}
            </div>
            <div style={{ marginTop: 6 }}>
              <span className={`pill ${statusPillClass[project.status] || 'pill-muted'}`}>
                {project.status || 'loading'}
              </span>
            </div>
            {project.repo_url && (
              <a
                href={project.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="sidebar-repo-link"
              >
                <GithubIcon size={14} />
                <span>View repo</span>
              </a>
            )}
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path === '' ? `/p/${code}` : `/p/${code}/${item.path}`}
                  end={item.end}
                  className={({ isActive }) =>
                    `sidebar-nav-link ${isActive ? 'active' : ''} ${item.purple ? 'purple' : ''}`
                  }
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Team roster */}
        <div className="sidebar-bottom">
          <div className="sidebar-section-label">Team</div>
          <div className="sidebar-team">
            {members.map(m => (
              <div key={m.id} className="sidebar-member">
                <span
                  className="member-dot"
                  style={{
                    background: m.invite_status === 'pending' ? '#8B949E' : getOwnerColor(m.id),
                  }}
                />
                <span
                  className={`flex-1 truncate text-sm ${m.invite_status === 'pending' ? 'text-muted' : ''}`}
                  style={{ fontStyle: m.invite_status === 'pending' ? 'italic' : 'normal' }}
                >
                  {m.name}
                </span>
                <span className={`pill ${m.role === 'lead' ? 'pill-blue' : 'pill-muted'}`}>
                  {m.role}
                </span>
                {m.invite_status === 'pending' && (
                  <span className="text-xs text-amber" style={{ marginLeft: 4 }}>invite pending</span>
                )}
              </div>
            ))}
          </div>

          {/* Health strip */}
          {health && (
            <div className="sidebar-health">
              <HealthDot name="Telegram" icon={Send} alive={health.telegram} />
              <HealthDot name="GitHub" icon={GithubIcon} alive={health.github} />
              <HealthDot name="LLM" icon={Cpu} alive={health.llm} />
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="shell-main">
        {/* Top navbar */}
        <header className="navbar">
          <div className="navbar-left">
            <Link to="/" className="navbar-logo">
              <Plane size={18} />
            </Link>
            <span className="navbar-sep">/</span>
            <span className="text-sm font-medium truncate">{project.name || code}</span>
          </div>

          <div className="navbar-center">
            {project.status === 'running' && (
              <div className="live-indicator">
                <span className="live-dot" />
                <span className="text-xs text-green font-medium">Live</span>
              </div>
            )}
          </div>

          <div className="navbar-right">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Users size={14} />
              <span>{members.length}</span>
            </div>

            {isLead && (
              <button
                className="btn btn-outline-blue btn-sm"
                onClick={handleFollowUp}
                disabled={followUpLoading}
              >
                {followUpLoading ? (
                  <><Loader2 size={14} className="animate-pulse" /> Sending…</>
                ) : (
                  'Run follow-up now'
                )}
              </button>
            )}

            {contradictions.length > 0 && (
              <Link to={`/p/${code}`} className="pill pill-red" style={{ cursor: 'pointer' }}>
                <AlertCircle size={12} />
                {contradictions.length} Contradiction{contradictions.length > 1 ? 's' : ''}
              </Link>
            )}
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="error-banner">
            <AlertCircle size={14} />
            Cannot reach backend — retrying…
            <div className="loading-dots"><span /><span /><span /></div>
          </div>
        )}

        {/* Page outlet */}
        <div className="shell-content">
          <Outlet context={{ snapshot, code, loading, diff }} />
        </div>
      </div>
    </div>
  );
}

function HealthDot({ name, icon: Icon, alive }) {
  return (
    <div className="health-dot-wrapper" title={`${name}: ${alive ? 'Online' : 'Offline'}`}>
      <span className={`health-dot ${alive ? 'alive' : 'dead'}`} />
      <Icon size={11} className="text-muted" />
    </div>
  );
}

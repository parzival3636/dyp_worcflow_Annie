import { useState, useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  getMemberName, getOwnerColor, relativeTime, formatTime, STATUS_COLORS, STATUS_LABELS
} from '../hooks/useSnapshot';
import TaskDrawer from '../components/TaskDrawer';
import {
  Clock, GitCommit, AlertTriangle, ShieldCheck, Sparkles,
  UserCheck, ArrowRight, CheckCircle2, MessageSquare, Flag,
  Filter, Search, ExternalLink, ChevronDown, ChevronRight
} from 'lucide-react';
import './Activity.css';

const EVENT_CONFIG = {
  project_created: { label: 'Project Created', color: 'var(--accent-blue)', icon: Flag },
  member_joined: { label: 'Member Joined', color: 'var(--green)', icon: UserCheck },
  task_created: { label: 'Task Created', color: 'var(--accent-blue)', icon: Flag },
  status_changed: { label: 'Status Transition', color: 'var(--purple)', icon: ArrowRight },
  blocker_opened: { label: 'Blocker Opened', color: 'var(--red)', icon: AlertTriangle },
  blocker_routed: { label: 'Blocker Routed', color: 'var(--amber)', icon: ArrowRight },
  blocker_resolved: { label: 'Blocker Resolved', color: 'var(--green)', icon: CheckCircle2 },
  contradiction_opened: { label: 'Contradiction Detected', color: 'var(--red)', icon: AlertTriangle },
  contradiction_resolved: { label: 'Contradiction Resolved', color: 'var(--green)', icon: CheckCircle2 },
  commit_seen: { label: 'Git Commit', color: '#58A6FF', icon: GitCommit },
  verification_done: { label: 'AI Verification', color: 'var(--green)', icon: ShieldCheck },
  guide_note: { label: 'Guide AI Note', color: 'var(--purple)', icon: Sparkles },
  checkin_sent: { label: 'Check-in Sent', color: 'var(--text-muted)', icon: MessageSquare },
  reply_received: { label: 'Member Reply', color: 'var(--accent-blue)', icon: MessageSquare },
  risk_changed: { label: 'Risk Recalculated', color: 'var(--amber)', icon: AlertTriangle },
};

export default function Activity() {
  const { snapshot, code } = useOutletContext();
  const [selectedTaskKey, setSelectedTaskKey] = useState(null);
  const [filterType, setFilterType] = useState('all');
  const [filterMember, setFilterMember] = useState('all');
  const [search, setSearch] = useState('');
  const [expandedEvents, setExpandedEvents] = useState(new Set());

  const events = useMemo(() => snapshot?.events || [], [snapshot]);
  const members = useMemo(() => snapshot?.members || [], [snapshot]);
  const repoUrl = snapshot?.project?.repo_url;

  // Toggle event expansion
  const toggleExpand = (evId) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(evId)) next.delete(evId);
      else next.add(evId);
      return next;
    });
  };

  // Filtered event stream
  const filteredEvents = useMemo(() => {
    return events.filter(ev => {
      // Type filter
      if (filterType !== 'all') {
        if (filterType === 'commits' && ev.type !== 'commit_seen') return false;
        if (filterType === 'blockers' && !ev.type.startsWith('blocker_') && !ev.type.startsWith('contradiction_')) return false;
        if (filterType === 'verifications' && ev.type !== 'verification_done') return false;
        if (filterType === 'guide' && ev.type !== 'guide_note') return false;
        if (filterType === 'tasks' && !['task_created', 'status_changed', 'risk_changed'].includes(ev.type)) return false;
      }

      // Member filter
      if (filterMember !== 'all' && String(ev.actor_member_id) !== filterMember) {
        return false;
      }

      // Search
      if (search) {
        const query = search.toLowerCase();
        const payloadStr = typeof ev.payload === 'string' ? ev.payload : JSON.stringify(ev.payload || '');
        const matchTask = ev.task_id && ev.task_id.toLowerCase().includes(query);
        const matchText = payloadStr.toLowerCase().includes(query) || ev.type.toLowerCase().includes(query);
        if (!matchTask && !matchText) return false;
      }

      return true;
    });
  }, [events, filterType, filterMember, search]);

  return (
    <div className="activity-page">
      {/* Header */}
      <div className="activity-header">
        <div>
          <h1 className="activity-title">Live Audit &amp; Event Stream</h1>
          <p className="activity-subtitle">
            Immutable Jira-grade audit ledger tracking state mutations, Telegram replies, commits, and AI verifications.
          </p>
        </div>
      </div>

      {/* Toolbar / Filters */}
      <div className="activity-toolbar">
        <div className="search-wrap">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="activity-search"
            placeholder="Search activity by keyword, SHA, or task key..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="filters-group">
          <div className="filter-item">
            <Filter size={14} className="text-muted" />
            <select
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
              className="activity-select"
            >
              <option value="all">All Events ({events.length})</option>
              <option value="commits">Git Commits</option>
              <option value="blockers">Blockers &amp; Contradictions</option>
              <option value="verifications">AI Verifications</option>
              <option value="tasks">Task Transitions</option>
              <option value="guide">Guide Insights</option>
            </select>
          </div>

          <div className="filter-item">
            <select
              value={filterMember}
              onChange={e => setFilterMember(e.target.value)}
              className="activity-select"
            >
              <option value="all">All Actors</option>
              {members.map(m => (
                <option key={m.id} value={String(m.id)}>{m.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Timeline Stream */}
      <div className="activity-timeline">
        {filteredEvents.length === 0 ? (
          <div className="empty-activity">
            <Clock size={32} className="text-muted" />
            <p>No activity events match your filter criteria.</p>
          </div>
        ) : (
          filteredEvents.map((ev, idx) => {
            const cfg = EVENT_CONFIG[ev.type] || { label: ev.type, color: 'var(--text-muted)', icon: Clock };
            const Icon = cfg.icon;
            const actorName = ev.actor_member_id ? getMemberName(snapshot, ev.actor_member_id) : 'Pilot Bot';
            const actorColor = ev.actor_member_id ? getOwnerColor(ev.actor_member_id) : '#8B949E';
            const isExpanded = expandedEvents.has(ev.id || idx);

            return (
              <div key={ev.id || idx} className="timeline-item">
                {/* Event Marker */}
                <div className="timeline-marker-col">
                  <div className="timeline-icon-wrap" style={{ borderColor: cfg.color, color: cfg.color }}>
                    <Icon size={14} />
                  </div>
                  {idx !== filteredEvents.length - 1 && <div className="timeline-connector" />}
                </div>

                {/* Event Content Box */}
                <div className="timeline-content">
                  <div className="timeline-top">
                    <div className="timeline-meta-left">
                      <span
                        className="event-type-badge"
                        style={{ color: cfg.color, borderColor: `${cfg.color}40`, background: `${cfg.color}15` }}
                      >
                        {cfg.label}
                      </span>

                      {ev.task_id && (
                        <button
                          className="event-task-link font-mono"
                          onClick={() => setSelectedTaskKey(ev.task_id)}
                        >
                          [{ev.task_id}]
                        </button>
                      )}

                      <div className="event-actor">
                        <span className="owner-dot" style={{ background: actorColor }} />
                        <span>{actorName}</span>
                      </div>
                    </div>

                    <div className="timeline-meta-right">
                      <span className="event-time" title={formatTime(ev.ts)}>
                        {relativeTime(ev.ts)}
                      </span>
                    </div>
                  </div>

                  {/* Body description */}
                  <div className="timeline-body">
                    {renderEventBody(ev, repoUrl, () => setSelectedTaskKey(ev.task_id))}
                  </div>

                  {/* Expandable details if payload has extra properties */}
                  {hasDeepPayload(ev.payload) && (
                    <div className="timeline-expandable">
                      <button
                        className="btn-expand"
                        onClick={() => toggleExpand(ev.id || idx)}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <span>{isExpanded ? 'Hide Payload' : 'View Raw Payload'}</span>
                      </button>

                      {isExpanded && (
                        <pre className="payload-json font-mono">
                          {JSON.stringify(ev.payload, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Task Drawer */}
      {selectedTaskKey && (
        <TaskDrawer
          taskKey={selectedTaskKey}
          snapshot={snapshot}
          code={code}
          onClose={() => setSelectedTaskKey(null)}
          onOpenTask={key => setSelectedTaskKey(key)}
        />
      )}
    </div>
  );
}

// Helper to render human-readable body according to event type
function renderEventBody(ev, repoUrl, onOpenTask) {
  const p = ev.payload || {};

  switch (ev.type) {
    case 'commit_seen':
      const sha = p.sha || p.commit_sha || '';
      const shortSha = sha ? sha.substring(0, 7) : '';
      const commitUrl = repoUrl && sha ? `${repoUrl}/commit/${sha}` : null;

      return (
        <div className="commit-event-body">
          <div className="commit-msg">"{p.message || 'Pushed new commit'}"</div>
          <div className="commit-details font-mono text-xs text-muted">
            {commitUrl ? (
              <a href={commitUrl} target="_blank" rel="noopener noreferrer" className="commit-sha-link">
                <span>{shortSha}</span>
                <ExternalLink size={11} />
              </a>
            ) : (
              <span>{shortSha}</span>
            )}
            {p.additions != null && <span className="text-green">+{p.additions}</span>}
            {p.deletions != null && <span className="text-red">-{p.deletions}</span>}
            {p.files && <span>({p.files.length || p.files} files)</span>}
          </div>
        </div>
      );

    case 'verification_done':
      const verdict = p.verdict || 'verified';
      const conf = p.confidence != null ? Math.round(p.confidence * 100) : 85;
      return (
        <div className="verify-event-body">
          <div className="verify-pill-row">
            <span className={`verdict-tag ${verdict}`}>
              {verdict === 'verified' ? 'Passed' : verdict} ({conf}%)
            </span>
            <span className="verify-reason">{p.reason || 'Criteria verified against pushed commits'}</span>
          </div>
        </div>
      );

    case 'status_changed':
      return (
        <div className="status-event-body">
          <span className="status-tag from">{STATUS_LABELS[p.from] || p.from}</span>
          <ArrowRight size={13} className="text-muted" />
          <span className="status-tag to">{STATUS_LABELS[p.to] || p.to}</span>
          {p.reason && <span className="status-reason">— {p.reason}</span>}
        </div>
      );

    case 'blocker_opened':
    case 'blocker_routed':
      return (
        <div className="blocker-event-body">
          <span className="blocker-desc">{p.description || (typeof p === 'string' ? p : 'Blocker encountered')}</span>
          {p.routed_to && <span className="routed-tag">Routed to member #{p.routed_to}</span>}
        </div>
      );

    case 'guide_note':
      const text = typeof p === 'string' ? p : (p.text || p.summary || JSON.stringify(p));
      return (
        <div className="guide-note-body">
          <span className="guide-text">{text}</span>
        </div>
      );

    default:
      if (typeof p === 'string') return <div>{p}</div>;
      if (p.summary) return <div>{p.summary}</div>;
      if (p.text) return <div>{p.text}</div>;
      if (p.title) return <div>Task: <strong>{p.title}</strong></div>;
      return <div className="text-muted text-xs">{JSON.stringify(p)}</div>;
  }
}

function hasDeepPayload(payload) {
  if (!payload || typeof payload !== 'object') return false;
  return Object.keys(payload).length > 2;
}

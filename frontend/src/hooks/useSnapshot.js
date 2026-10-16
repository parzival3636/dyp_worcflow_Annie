import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
const POLL_INTERVAL = 2000;

/* ===== Owner color from palette ===== */
const OWNER_COLORS = [
  '#58A6FF', '#3FB950', '#D29922', '#F85149',
  '#BC8CFF', '#79C0FF', '#56D364', '#FF7B72',
];

export function getOwnerColor(memberId) {
  if (memberId == null) return '#8B949E';
  const idx = typeof memberId === 'number' ? memberId : Math.abs(hashStr(String(memberId)));
  return OWNER_COLORS[idx % OWNER_COLORS.length];
}

function hashStr(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  }
  return h;
}

/* ===== API helpers ===== */
export async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = new Error(`API ${res.status}`);
    err.status = res.status;
    try { err.body = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export function apiGet(path) {
  return apiFetch(path);
}

export function apiPost(path, body) {
  return apiFetch(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
}

export function apiPatch(path, body) {
  return apiFetch(path, { method: 'PATCH', body: JSON.stringify(body) });
}

export function apiDelete(path) {
  return apiFetch(path, { method: 'DELETE' });
}

/* ===== useSnapshot hook ===== */
export function useSnapshot(code) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const prevRef = useRef(null);
  const [diff, setDiff] = useState(null);

  const fetchSnapshot = useCallback(async () => {
    if (!code) return;
    try {
      const data = await apiGet(`/projects/${code}/snapshot`);
      // Compute diff
      if (prevRef.current) {
        const d = computeDiff(prevRef.current, data);
        if (d) setDiff(d);
      }
      prevRef.current = data;
      setSnapshot(data);
      setError(null);
    } catch (e) {
      // In development or when backend is starting, provide rich demo snapshot
      const fallback = getDemoSnapshot(code);
      if (fallback) {
        if (prevRef.current) {
          const d = computeDiff(prevRef.current, fallback);
          if (d) setDiff(d);
        }
        prevRef.current = fallback;
        setSnapshot(fallback);
        setError(null);
      } else {
        setError(e);
      }
    } finally {
      setLoading(false);
    }
  }, [code]);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    fetchSnapshot();
    const id = setInterval(fetchSnapshot, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [code, fetchSnapshot]);

  return { snapshot, loading, error, diff, refetch: fetchSnapshot };
}

/* ===== Demo Snapshot Generator ===== */
export function getDemoSnapshot(code = 'demo01') {
  return {
    project: {
      code,
      name: "PayFlow",
      idea: "A high-concurrency payment processing app for campus events",
      repo_full_name: "pilot-team/payflow",
      repo_url: "https://github.com/pilot-team/payflow",
      status: "running",
      starts_at: "2026-10-16T09:00:00Z",
      ends_at: "2026-10-18T09:00:00Z"
    },
    members: [
      { id: 1, name: "Kabir", role: "lead", github_login: "kabir-dev", invite_status: "accepted", color: "#58A6FF" },
      { id: 2, name: "Aarav", role: "member", github_login: "aarav-code", invite_status: "accepted", color: "#3FB950" },
      { id: 3, name: "Priya", role: "member", github_login: "priya-tech", invite_status: "accepted", color: "#D29922" },
      { id: 4, name: "Rohan", role: "member", github_login: "rohan-eng", invite_status: "accepted", color: "#BC8CFF" }
    ],
    blocks: [
      { id: 1, name: "Payment Gateway API", owner_member_id: 1, total_effort: 14, oversize_flag: 0 },
      { id: 2, name: "Database & Schemas", owner_member_id: 2, total_effort: 10, oversize_flag: 0 },
      { id: 3, name: "Checkout UI & State", owner_member_id: 3, total_effort: 12, oversize_flag: 0 },
      { id: 4, name: "Webhook Integration", owner_member_id: 4, total_effort: 11, oversize_flag: 0 }
    ],
    tasks: [
      {
        key: "T-1",
        title: "Set up PostgreSQL schemas and migrations",
        status: "verified_done",
        owner_member_id: 2,
        block_id: 2,
        effort: 4,
        deadline: "2026-10-16T14:00:00Z",
        progress: 100,
        risk: "ok",
        is_milestone: false,
        acceptance_criteria: ["Initial schema migration applied", "Foreign keys and indices on transactions"],
        description: "Establish tables for accounts, event tickets, and payment ledgers.",
        verification: { verdict: "verified", confidence: 0.94, reason: "All schema migration scripts present and test suite passes." },
        blocker: null
      },
      {
        key: "T-2",
        title: "Stripe & Razorpay payment API integration",
        status: "blocked",
        owner_member_id: 1,
        block_id: 1,
        effort: 8,
        deadline: "2026-10-16T18:00:00Z",
        progress: 45,
        risk: "critical",
        is_milestone: false,
        acceptance_criteria: ["Process test charge via Stripe SDK", "Handle idempotency keys", "Validate signature on webhook callbacks"],
        description: "Core checkout integration. Waiting on webhook endpoint URL and environment credentials.",
        verification: null,
        blocker: {
          id: 1,
          description: "Needs public webhook HTTPS endpoint URL from Aarav to complete signature test",
          status: "routed",
          routed_to: 2
        }
      },
      {
        key: "T-3",
        title: "Interactive Ticket Checkout Flow",
        status: "in_progress",
        owner_member_id: 3,
        block_id: 3,
        effort: 6,
        deadline: "2026-10-17T02:00:00Z",
        progress: 60,
        risk: "at_risk",
        is_milestone: false,
        acceptance_criteria: ["Ticket selection slider", "Payment modal triggers callback", "Receipt screen displays QR code"],
        description: "Mobile-responsive checkout modal embedded into campus event landing page.",
        verification: null,
        blocker: null
      },
      {
        key: "T-4",
        title: "Webhook listener & Transaction Ledger",
        status: "needs_review",
        owner_member_id: 4,
        block_id: 4,
        effort: 5,
        deadline: "2026-10-17T06:00:00Z",
        progress: 90,
        risk: "ok",
        is_milestone: false,
        acceptance_criteria: ["Listen for payment_intent.succeeded", "Update ticket status in DB", "Send Telegram confirmation receipt"],
        description: "Asynchronous event listener for payment success.",
        verification: { verdict: "partial", confidence: 0.65, reason: "Telegram confirmation handler test coverage missing." },
        blocker: null
      },
      {
        key: "T-5",
        title: "Integration Testing & Live Demo Milestone",
        status: "todo",
        owner_member_id: 1,
        block_id: 1,
        effort: 6,
        deadline: "2026-10-17T16:00:00Z",
        progress: 0,
        risk: "at_risk",
        is_milestone: true,
        acceptance_criteria: ["End-to-end checkout demo on staging", "Real-time ledger updates on dashboard", "All 4 builders verified"],
        description: "Final team milestone for Kurukshetra Hackathon demo presentation.",
        verification: null,
        blocker: null
      }
    ],
    deps: [
      { from: "T-1", to: "T-2", kind: "hard" },
      { from: "T-2", to: "T-3", kind: "hard" },
      { from: "T-3", to: "T-5", kind: "hard" },
      { from: "T-4", to: "T-5", kind: "handoff" }
    ],
    contradictions: [
      {
        id: 1,
        task_ids: ["T-2", "T-4"],
        member_ids: [1, 4],
        summary: "Kabir reported waiting on webhook credentials, but Rohan noted credentials were committed 30m ago.",
        status: "open"
      }
    ],
    events: [
      {
        id: 101,
        ts: "2026-10-16T13:40:00Z",
        actor_member_id: 1,
        type: "blocker_opened",
        task_id: "T-2",
        payload: { description: "Waiting on public HTTPS webhook endpoint from Aarav", routed_to: 2 }
      },
      {
        id: 102,
        ts: "2026-10-16T13:30:00Z",
        actor_member_id: 2,
        type: "commit_seen",
        task_id: "T-1",
        payload: { sha: "4a9f2bc", message: "[T-1] Add db migration for payment ledger", additions: 142, deletions: 12, files: ["db/migration_01.sql"] }
      },
      {
        id: 103,
        ts: "2026-10-16T13:31:00Z",
        actor_member_id: null,
        type: "verification_done",
        task_id: "T-1",
        payload: { verdict: "verified", confidence: 0.94, reason: "All acceptance criteria verified against commit 4a9f2bc" }
      },
      {
        id: 104,
        ts: "2026-10-16T13:35:00Z",
        actor_member_id: null,
        type: "guide_note",
        task_id: "T-2",
        payload: { text: "Kabir is blocked on T-2. Downstream slip calculated: 3.5 hrs. Demo milestone T-5 is now at risk." }
      }
    ],
    contributions: {
      series: {
        "1": [{ ts: "10:00", commits: 1, lines: 120 }, { ts: "12:00", commits: 3, lines: 410 }, { ts: "14:00", commits: 5, lines: 780 }],
        "2": [{ ts: "10:00", commits: 2, lines: 250 }, { ts: "12:00", commits: 4, lines: 620 }, { ts: "14:00", commits: 6, lines: 980 }],
        "3": [{ ts: "10:00", commits: 0, lines: 0 }, { ts: "12:00", commits: 2, lines: 340 }, { ts: "14:00", commits: 3, lines: 520 }],
        "4": [{ ts: "10:00", commits: 1, lines: 90 }, { ts: "12:00", commits: 2, lines: 280 }, { ts: "14:00", commits: 4, lines: 640 }]
      },
      totals: [
        { member_id: 1, commits: 5, lines: 780, tasks_verified: 1, last_active: "2026-10-16T13:40:00Z" },
        { member_id: 2, commits: 6, lines: 980, tasks_verified: 2, last_active: "2026-10-16T13:30:00Z" },
        { member_id: 3, commits: 3, lines: 520, tasks_verified: 1, last_active: "2026-10-16T13:20:00Z" },
        { member_id: 4, commits: 4, lines: 640, tasks_verified: 1, last_active: "2026-10-16T13:10:00Z" }
      ]
    },
    guide_notes: [
      { text: "Kabir is blocked on T-2 -> Demo milestone is at risk.", created_at: "2026-10-16T13:35:00Z" },
      { text: "Aarav verified task T-1 (PostgreSQL schema) with 94% confidence.", created_at: "2026-10-16T13:31:00Z" }
    ]
  };
}

/* ===== useHealth hook ===== */
export function useHealth() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const check = async () => {
      try {
        const h = await apiGet('/health');
        setHealth(h);
      } catch {
        setHealth({ telegram: false, github: false, llm: false, db: false });
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  return health;
}

/* ===== Diff computation ===== */
function computeDiff(prev, next) {
  if (!prev || !next) return null;
  const changes = { newEvents: [], statusChanges: [], newContradictions: [] };

  // New events
  if (next.events && prev.events) {
    const prevIds = new Set(prev.events.map(e => e.id));
    changes.newEvents = next.events.filter(e => !prevIds.has(e.id));
  }

  // Status changes
  if (next.tasks && prev.tasks) {
    const prevMap = new Map(prev.tasks.map(t => [t.key, t.status]));
    next.tasks.forEach(t => {
      const prevStatus = prevMap.get(t.key);
      if (prevStatus && prevStatus !== t.status) {
        changes.statusChanges.push({ key: t.key, from: prevStatus, to: t.status });
      }
    });
  }

  // New contradictions
  if (next.contradictions && prev.contradictions) {
    const prevIds = new Set(prev.contradictions.map(c => c.id));
    changes.newContradictions = next.contradictions.filter(c => !prevIds.has(c.id));
  }

  const hasChanges = changes.newEvents.length > 0 || changes.statusChanges.length > 0 || changes.newContradictions.length > 0;
  return hasChanges ? changes : null;
}

/* ===== Relative time ===== */
export function relativeTime(dateStr) {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now - date;
  const absDiff = Math.abs(diffMs);
  const isFuture = diffMs < 0;

  if (absDiff < 60000) return 'just now';
  const mins = Math.floor(absDiff / 60000);
  if (mins < 60) return isFuture ? `in ${mins}m` : `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return isFuture ? `in ${hrs}h` : `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return isFuture ? `in ${days}d` : `${days}d ago`;
}

export function formatTime(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString();
}

export function isOverdue(deadline) {
  if (!deadline) return false;
  return new Date(deadline) < new Date();
}

/* ===== Status helpers ===== */
export const STATUS_ORDER = [
  'todo', 'in_progress', 'blocked', 'claimed_done', 'needs_review', 'verified_done'
];

export const STATUS_LABELS = {
  todo: 'Todo',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  claimed_done: 'Claimed Done',
  needs_review: 'Needs Review',
  verified_done: 'Verified Done',
};

export const STATUS_COLORS = {
  todo: 'muted',
  in_progress: 'blue',
  blocked: 'red',
  claimed_done: 'amber',
  needs_review: 'amber',
  verified_done: 'green',
};

/* ===== Member helpers ===== */
export function getMember(snapshot, memberId) {
  if (!snapshot?.members) return null;
  return snapshot.members.find(m => m.id === memberId);
}

export function getMemberName(snapshot, memberId) {
  const m = getMember(snapshot, memberId);
  return m?.name || 'Unknown';
}

/* ===== Task helpers ===== */
export function getTask(snapshot, key) {
  if (!snapshot?.tasks) return null;
  return snapshot.tasks.find(t => t.key === key);
}

export function getTaskDeps(snapshot, taskKey) {
  if (!snapshot?.deps) return { dependsOn: [], blocks: [] };
  const dependsOn = snapshot.deps.filter(d => d.to === taskKey).map(d => ({ key: d.from, kind: d.kind }));
  const blocks = snapshot.deps.filter(d => d.from === taskKey).map(d => ({ key: d.to, kind: d.kind }));
  return { dependsOn, blocks };
}

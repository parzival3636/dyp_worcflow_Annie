import { useState, useEffect, useRef, useCallback } from 'react';
import { SEEDED_SNAPSHOT } from '../mock/snapshot';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const POLL_INTERVAL = 2000;

/* ===== Owner color from palette (Jira Accessible) ===== */
export const OWNER_COLORS = [
  '#4C8DFF', // Member 1 (Kabir - Lead)
  '#3DD68C', // Member 2 (Aarav)
  '#F2B33D', // Member 3 (Priya)
  '#A78BFA', // Member 4 (Rohan)
  '#00D2D3', // Member 5
  '#FF6B8B', // Member 6
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

export function getDemoSnapshot(code = 'demo01') {
  const clone = JSON.parse(JSON.stringify(SEEDED_SNAPSHOT));
  if (clone.project) {
    clone.project.code = code;
  }
  return clone;
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

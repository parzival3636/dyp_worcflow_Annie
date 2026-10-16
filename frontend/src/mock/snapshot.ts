/**
 * Pilot Seeded Mock Snapshot
 * Realistic hackathon project state for campus payment processing app "PayFlow".
 * 4 members, 16 tasks, 4 blocks, 2 blockers, 1 contradiction, commits, and events.
 */

export interface SnapshotMember {
  id: number;
  name: string;
  role: 'lead' | 'member';
  github_login: string;
  telegram_username: string;
  telegram_id: number;
  invite_status: 'accepted' | 'pending';
  color?: string;
}

export interface SnapshotBlock {
  id: number;
  name: string;
  owner_member_id: number;
  total_effort: number;
  oversize_flag: boolean;
}

export interface SnapshotVerification {
  verdict: 'verified' | 'partial' | 'no_evidence';
  confidence: number;
  reason: string;
  matched_shas?: string[];
  criteria_results?: { criterion: string; met: boolean }[];
}

export interface SnapshotBlocker {
  id: number;
  description: string;
  status: 'open' | 'routed' | 'resolved';
  routed_to?: number;
}

export interface SnapshotTask {
  key: string;
  title: string;
  status: 'todo' | 'in_progress' | 'blocked' | 'claimed_done' | 'needs_review' | 'verified_done';
  owner_member_id: number | null;
  block_id: number | null;
  effort: number;
  deadline: string;
  progress: number;
  risk: 'ok' | 'at_risk' | 'critical';
  is_milestone: boolean;
  acceptance_criteria: string[];
  description: string;
  verification?: SnapshotVerification | null;
  blocker?: SnapshotBlocker | null;
  started_at?: string;
  completed_at?: string;
}

export interface SnapshotDep {
  from: string;
  to: string;
  kind: 'hard' | 'handoff';
}

export interface SnapshotContradiction {
  id: number;
  task_ids: string[];
  member_ids: number[];
  summary: string;
  status: 'open' | 'resolved';
}

export interface SnapshotCommit {
  sha: string;
  message: string;
  author_login: string;
  member_id: number;
  files: string[];
  additions: number;
  deletions: number;
  committed_at: string;
  task_id: string;
}

export interface SnapshotEvent {
  id: number;
  ts: string;
  actor_member_id: number | null;
  type: string;
  task_id?: string | null;
  payload: any;
}

export interface ProjectSnapshot {
  project: {
    code: string;
    name: string;
    idea: string;
    repo_full_name: string;
    repo_url: string;
    status: 'planning' | 'running' | 'done';
    starts_at: string;
    ends_at: string;
  };
  members: SnapshotMember[];
  blocks: SnapshotBlock[];
  tasks: SnapshotTask[];
  deps: SnapshotDep[];
  contradictions: SnapshotContradiction[];
  events: SnapshotEvent[];
  commits?: SnapshotCommit[];
  contributions: {
    series: Record<string, { ts: string; commits: number; lines: number }[]>;
    totals: {
      member_id: number;
      commits: number;
      lines: number;
      tasks_verified: number;
      last_active: string;
    }[];
  };
  guide_notes: { text: string; created_at: string }[];
}

export const SEEDED_SNAPSHOT: ProjectSnapshot = {
  project: {
    code: "demo01",
    name: "PayFlow",
    idea: "High-throughput campus payment orchestration engine connecting UPI, Stripe webhooks, and QR admissions.",
    repo_full_name: "pilot-team/payflow",
    repo_url: "https://github.com/pilot-team/payflow",
    status: "running",
    starts_at: "2026-10-16T08:00:00Z",
    ends_at: "2026-10-18T18:00:00Z"
  },
  members: [
    {
      id: 1,
      name: "Kabir",
      role: "lead",
      github_login: "kabir-dev",
      telegram_username: "kabir_ops",
      telegram_id: 84729102,
      invite_status: "accepted",
      color: "#4C8DFF"
    },
    {
      id: 2,
      name: "Aarav",
      role: "member",
      github_login: "aarav-code",
      telegram_username: "aarav_backend",
      telegram_id: 93847201,
      invite_status: "accepted",
      color: "#3DD68C"
    },
    {
      id: 3,
      name: "Priya",
      role: "member",
      github_login: "priya-tech",
      telegram_username: "priya_ui",
      telegram_id: 72619482,
      invite_status: "accepted",
      color: "#F2B33D"
    },
    {
      id: 4,
      name: "Rohan",
      role: "member",
      github_login: "rohan-eng",
      telegram_username: "rohan_infra",
      telegram_id: 61829471,
      invite_status: "accepted",
      color: "#A78BFA"
    }
  ],
  blocks: [
    {
      id: 1,
      name: "Gateway API & Integrations",
      owner_member_id: 1,
      total_effort: 18,
      oversize_flag: false
    },
    {
      id: 2,
      name: "PostgreSQL Ledger & Schemas",
      owner_member_id: 2,
      total_effort: 14,
      oversize_flag: false
    },
    {
      id: 3,
      name: "Checkout UI & State Engine",
      owner_member_id: 3,
      total_effort: 16,
      oversize_flag: false
    },
    {
      id: 4,
      name: "Webhook Pipeline & Ingestion",
      owner_member_id: 4,
      total_effort: 15,
      oversize_flag: false
    }
  ],
  tasks: [
    // --- Block 2: Schemas ---
    {
      key: "T-1",
      title: "Design PostgreSQL migrations for tickets and transaction ledger",
      status: "verified_done",
      owner_member_id: 2,
      block_id: 2,
      effort: 4,
      deadline: "2026-10-16T12:00:00Z",
      progress: 100,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Tables for accounts, event_tickets, and transaction_ledger created",
        "Unique constraint on transaction idempotency key",
        "Rollback migration script verified"
      ],
      description: "Define baseline relational schema for multi-tenant ticketing and ledger balance checks with audit trail.",
      verification: {
        verdict: "verified",
        confidence: 0.94,
        reason: "Matched commit 4a9f2bc with 3 migration files and pytest suite passing 100%.",
        matched_shas: ["4a9f2bc", "8f12a0d"]
      },
      blocker: null,
      started_at: "2026-10-16T08:30:00Z",
      completed_at: "2026-10-16T11:45:00Z"
    },
    {
      key: "T-2",
      title: "Build database connection pool and repository query helpers",
      status: "verified_done",
      owner_member_id: 2,
      block_id: 2,
      effort: 3,
      deadline: "2026-10-16T15:00:00Z",
      progress: 100,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Asyncpg connection pool with max 20 connections",
        "Health check query ping with <5ms latency",
        "Context manager for atomic transaction rollbacks"
      ],
      description: "Low-latency repository query engine wrapping asyncpg with structured query tracing.",
      verification: {
        verdict: "verified",
        confidence: 0.91,
        reason: "Commit 9b30c11 introduced connection pool manager and test suite with mock DB.",
        matched_shas: ["9b30c11"]
      },
      blocker: null,
      started_at: "2026-10-16T12:00:00Z",
      completed_at: "2026-10-16T14:30:00Z"
    },
    // --- Block 1: Gateway API ---
    {
      key: "T-3",
      title: "Implement Stripe Checkout session initiation endpoint",
      status: "verified_done",
      owner_member_id: 1,
      block_id: 1,
      effort: 5,
      deadline: "2026-10-16T18:00:00Z",
      progress: 100,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "POST /api/v1/checkout/session returns valid stripe session_id",
        "Validates line items, currency constraints, and campus discount codes",
        "Stores pending transaction record in Postgres"
      ],
      description: "Server endpoint to instantiate Stripe sessions and inject tracking metadata.",
      verification: {
        verdict: "verified",
        confidence: 0.88,
        reason: "Session initiation handler tests verified against Stripe test environment.",
        matched_shas: ["1d4a8ef"]
      },
      blocker: null,
      started_at: "2026-10-16T13:00:00Z",
      completed_at: "2026-10-16T17:20:00Z"
    },
    {
      key: "T-4",
      title: "Connect Razorpay UPI intent payload and signature generation",
      status: "blocked",
      owner_member_id: 1,
      block_id: 1,
      effort: 6,
      deadline: "2026-10-16T21:00:00Z",
      progress: 40,
      risk: "critical",
      is_milestone: false,
      acceptance_criteria: [
        "Generate UPI deep-link URL and QR string for mobile UPI intent",
        "Compute SHA256 signature for order validation",
        "Handle payment timeout within 300 seconds"
      ],
      description: "Core domestic payment rail integration. Stalled due to missing live sandbox credentials from team lead.",
      verification: null,
      blocker: {
        id: 1,
        description: "Waiting on public HTTPS webhook tunnel and Razorpay API key pair from Rohan",
        status: "routed",
        routed_to: 4
      },
      started_at: "2026-10-16T17:30:00Z"
    },
    // --- Block 3: UI & State ---
    {
      key: "T-5",
      title: "Create interactive ticket tier selection and summary sheet",
      status: "in_progress",
      owner_member_id: 3,
      block_id: 3,
      effort: 4,
      deadline: "2026-10-17T00:00:00Z",
      progress: 65,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Tier selector supporting Early Bird, General, and VIP tiers",
        "Live recalculation of service tax and total payable",
        "Mobile viewport responsive layout at 390px"
      ],
      description: "Frontend ticket selection flow with instant price breakdown and inventory locks.",
      verification: null,
      blocker: null,
      started_at: "2026-10-16T18:00:00Z"
    },
    {
      key: "T-6",
      title: "Build payment processing modal and QR code scanner",
      status: "in_progress",
      owner_member_id: 3,
      block_id: 3,
      effort: 5,
      deadline: "2026-10-17T04:00:00Z",
      progress: 50,
      risk: "at_risk",
      is_milestone: false,
      acceptance_criteria: [
        "Embedded QR display for UPI transactions with timer countdown",
        "Stripe Elements iframe container with zero layout shift",
        "Polling payment status every 2 seconds with optimistic UI"
      ],
      description: "Unified checkout modal supporting dynamic tab switching between Credit Card and UPI.",
      verification: null,
      blocker: null,
      started_at: "2026-10-16T19:00:00Z"
    },
    // --- Block 4: Webhook Pipeline ---
    {
      key: "T-7",
      title: "Develop HMAC SHA256 signature validation middleware",
      status: "verified_done",
      owner_member_id: 4,
      block_id: 4,
      effort: 3,
      deadline: "2026-10-16T16:00:00Z",
      progress: 100,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Constant-time string comparison preventing timing attacks",
        "Replay attack rejection for timestamps older than 5 minutes",
        "Detailed structured rejection logs"
      ],
      description: "FastAPI security middleware verifying raw payload signatures from webhook incoming traffic.",
      verification: {
        verdict: "verified",
        confidence: 0.96,
        reason: "Test suite with valid and invalid cryptographic signatures passed.",
        matched_shas: ["3c21a99"]
      },
      blocker: null,
      started_at: "2026-10-16T12:00:00Z",
      completed_at: "2026-10-16T15:10:00Z"
    },
    {
      key: "T-8",
      title: "Ingest Stripe payment_intent.succeeded and update ledger",
      status: "blocked",
      owner_member_id: 4,
      block_id: 4,
      effort: 4,
      deadline: "2026-10-17T02:00:00Z",
      progress: 30,
      risk: "critical",
      is_milestone: false,
      acceptance_criteria: [
        "Idempotent event ingestion preventing duplicate ticket issuance",
        "Atomic update on user ticket state from pending to confirmed",
        "Dispatch confirmation email via SendGrid stub"
      ],
      description: "Webhook processing worker translating payment events to ticket ledger mutations.",
      verification: null,
      blocker: {
        id: 2,
        description: "Database transaction deadlocks on concurrent ticket status updates",
        status: "routed",
        routed_to: 2
      },
      started_at: "2026-10-16T19:30:00Z"
    },
    // --- Additional Tasks across Columns ---
    {
      key: "T-9",
      title: "Produce dynamic QR admission ticket PDF generator",
      status: "needs_review",
      owner_member_id: 3,
      block_id: 3,
      effort: 4,
      deadline: "2026-10-17T07:00:00Z",
      progress: 85,
      risk: "at_risk",
      is_milestone: false,
      acceptance_criteria: [
        "Generates PDF ticket with signed cryptographically verifiable QR",
        "Includes attendee name, seat category, and event rules",
        "File size under 300KB"
      ],
      description: "PDF report generator rendering printable tickets once payment completes.",
      verification: {
        verdict: "partial",
        confidence: 0.62,
        reason: "Claimed completion but commit has missing unit tests for corrupted QR payloads.",
        matched_shas: ["7f41b02"]
      },
      blocker: null,
      started_at: "2026-10-16T20:00:00Z"
    },
    {
      key: "T-10",
      title: "Configure Redis caching for ticket inventory balance",
      status: "claimed_done",
      owner_member_id: 2,
      block_id: 2,
      effort: 3,
      deadline: "2026-10-17T09:00:00Z",
      progress: 95,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Atomic DECR operations preventing overselling",
        "Cache write-through to Postgres transaction ledger",
        "TTL expiration on unconfirmed held tickets"
      ],
      description: "High-speed in-memory store ensuring ticket tier counts remain strictly consistent under flash sales.",
      verification: null,
      blocker: null,
      started_at: "2026-10-16T21:00:00Z"
    },
    {
      key: "T-11",
      title: "Implement Telegram bot receipt notifications for buyers",
      status: "in_progress",
      owner_member_id: 4,
      block_id: 4,
      effort: 3,
      deadline: "2026-10-17T11:00:00Z",
      progress: 45,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Sends instant receipt message upon webhook event arrival",
        "Includes download link for QR ticket",
        "Supports inline refund status inquiry button"
      ],
      description: "Automated Telegram buyer messaging rail linking tickets directly to user Telegram accounts.",
      verification: null,
      blocker: null,
      started_at: "2026-10-16T22:00:00Z"
    },
    {
      key: "T-12",
      title: "Build refund and cancellation transaction handler",
      status: "todo",
      owner_member_id: 1,
      block_id: 1,
      effort: 5,
      deadline: "2026-10-17T14:00:00Z",
      progress: 0,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Lead-only approval endpoint for issuing refunds",
        "Calls Stripe refund API and reconciles internal balance",
        "Re-increments ticket inventory in Redis"
      ],
      description: "Financial reversal workflows for cancelled events or contested purchases.",
      verification: null,
      blocker: null
    },
    {
      key: "T-13",
      title: "Real-time SSE event stream for admissions gate scanners",
      status: "todo",
      owner_member_id: 2,
      block_id: 2,
      effort: 4,
      deadline: "2026-10-17T17:00:00Z",
      progress: 0,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Server-sent events pushing verified admissions within 200ms",
        "Offline synchronization for temporary network drops",
        "Double-entry prevention check on gate scan"
      ],
      description: "High concurrency live broadcast stream feeding scanner tablets at event entry doors.",
      verification: null,
      blocker: null
    },
    {
      key: "T-14",
      title: "End-to-end integration and load testing benchmark",
      status: "todo",
      owner_member_id: 4,
      block_id: 4,
      effort: 5,
      deadline: "2026-10-17T20:00:00Z",
      progress: 0,
      risk: "at_risk",
      is_milestone: false,
      acceptance_criteria: [
        "Sustain 250 concurrent checkouts without HTTP 500 errors",
        "P99 response time below 450ms across checkout pipeline",
        "Zero orphan charges without corresponding tickets"
      ],
      description: "Locust load testing suite validating flash sale resiliency across full stack.",
      verification: null,
      blocker: null
    },
    {
      key: "T-15",
      title: "Demo & Submission Milestone: Campus Live Presentation",
      status: "todo",
      owner_member_id: 1,
      block_id: 1,
      effort: 6,
      deadline: "2026-10-18T16:00:00Z",
      progress: 0,
      risk: "critical",
      is_milestone: true,
      acceptance_criteria: [
        "Live checkout executed from phone to verified admissions ledger",
        "Telegram bot check-in loop demonstrates unblocking flow",
        "All 4 builder contributions verified against GitHub commits"
      ],
      description: "Final Kurukshetra Hackathon submission and live demonstration milestone.",
      verification: null,
      blocker: null
    },
    {
      key: "T-16",
      title: "Audit logging and automated compliance export",
      status: "todo",
      owner_member_id: 3,
      block_id: 3,
      effort: 3,
      deadline: "2026-10-18T12:00:00Z",
      progress: 0,
      risk: "ok",
      is_milestone: false,
      acceptance_criteria: [
        "Export CSV of all financial transactions with SHA256 checksums",
        "Immutable audit table tracking every status override",
        "Faculty/judge export summary bundle"
      ],
      description: "Export module packaging project execution proofs for grading review.",
      verification: null,
      blocker: null
    }
  ],
  deps: [
    { from: "T-1", to: "T-2", kind: "hard" },
    { from: "T-2", to: "T-3", kind: "hard" },
    { from: "T-2", to: "T-4", kind: "hard" },
    { from: "T-3", to: "T-5", kind: "hard" },
    { from: "T-4", to: "T-6", kind: "hard" },
    { from: "T-7", to: "T-8", kind: "hard" },
    { from: "T-8", to: "T-9", kind: "handoff" },
    { from: "T-2", to: "T-10", kind: "hard" },
    { from: "T-8", to: "T-11", kind: "handoff" },
    { from: "T-3", to: "T-12", kind: "hard" },
    { from: "T-1", to: "T-13", kind: "hard" },
    { from: "T-6", to: "T-14", kind: "hard" },
    { from: "T-11", to: "T-14", kind: "handoff" },
    { from: "T-14", to: "T-15", kind: "hard" },
    { from: "T-9", to: "T-15", kind: "hard" },
    { from: "T-10", to: "T-16", kind: "handoff" }
  ],
  contradictions: [
    {
      id: 1,
      task_ids: ["T-4", "T-8"],
      member_ids: [1, 4],
      summary: "Kabir reported waiting on webhook credentials from Rohan, but Rohan stated in Telegram check-in that credentials were encrypted in repo .env.production.",
      status: "open"
    }
  ],
  commits: [
    {
      sha: "4a9f2bc",
      message: "[T-1] Add PostgreSQL schema migrations for ledger and tickets",
      author_login: "aarav-code",
      member_id: 2,
      files: ["migrations/001_initial_ledger.sql", "src/models/ticket.py"],
      additions: 184,
      deletions: 12,
      committed_at: "2026-10-16T11:32:00Z",
      task_id: "T-1"
    },
    {
      sha: "9b30c11",
      message: "[T-2] Setup asyncpg connection pool with healthcheck",
      author_login: "aarav-code",
      member_id: 2,
      files: ["src/db/pool.py", "tests/test_pool.py"],
      additions: 126,
      deletions: 8,
      committed_at: "2026-10-16T14:15:00Z",
      task_id: "T-2"
    },
    {
      sha: "1d4a8ef",
      message: "[T-3] Implement Stripe Checkout session creation endpoint",
      author_login: "kabir-dev",
      member_id: 1,
      files: ["src/api/checkout.py", "src/services/stripe.py"],
      additions: 210,
      deletions: 19,
      committed_at: "2026-10-16T17:05:00Z",
      task_id: "T-3"
    },
    {
      sha: "3c21a99",
      message: "[T-7] Implement HMAC SHA256 webhook signature security verification",
      author_login: "rohan-eng",
      member_id: 4,
      files: ["src/security/hmac.py", "tests/test_signatures.py"],
      additions: 98,
      deletions: 4,
      committed_at: "2026-10-16T14:50:00Z",
      task_id: "T-7"
    },
    {
      sha: "7f41b02",
      message: "[T-9] Initial PDF ticket template rendering engine",
      author_login: "priya-tech",
      member_id: 3,
      files: ["src/templates/ticket.html", "src/pdf/generator.py"],
      additions: 145,
      deletions: 22,
      committed_at: "2026-10-16T20:12:00Z",
      task_id: "T-9"
    }
  ],
  events: [
    {
      id: 101,
      ts: "2026-10-16T08:00:00Z",
      actor_member_id: 1,
      type: "project_created",
      task_id: null,
      payload: { code: "demo01", name: "PayFlow" }
    },
    {
      id: 102,
      ts: "2026-10-16T08:15:00Z",
      actor_member_id: 2,
      type: "member_joined",
      task_id: null,
      payload: { name: "Aarav", role: "member" }
    },
    {
      id: 103,
      ts: "2026-10-16T11:45:00Z",
      actor_member_id: null,
      type: "verification_done",
      task_id: "T-1",
      payload: { verdict: "verified", confidence: 0.94, reason: "Criteria verified against commit 4a9f2bc" }
    },
    {
      id: 104,
      ts: "2026-10-16T14:30:00Z",
      actor_member_id: null,
      type: "verification_done",
      task_id: "T-2",
      payload: { verdict: "verified", confidence: 0.91, reason: "Criteria verified against commit 9b30c11" }
    },
    {
      id: 105,
      ts: "2026-10-16T17:20:00Z",
      actor_member_id: null,
      type: "verification_done",
      task_id: "T-3",
      payload: { verdict: "verified", confidence: 0.88, reason: "Criteria verified against commit 1d4a8ef" }
    },
    {
      id: 106,
      ts: "2026-10-16T17:45:00Z",
      actor_member_id: 1,
      type: "blocker_opened",
      task_id: "T-4",
      payload: { description: "Waiting on public HTTPS webhook tunnel and Razorpay API key pair", routed_to: 4 }
    },
    {
      id: 107,
      ts: "2026-10-16T18:00:00Z",
      actor_member_id: null,
      type: "guide_note",
      task_id: "T-4",
      payload: { text: "Kabir is blocked on T-4 (Razorpay UPI). Downstream slip: 3.5 hrs. Demo milestone T-15 is at risk." }
    },
    {
      id: 108,
      ts: "2026-10-16T19:40:00Z",
      actor_member_id: 4,
      type: "blocker_opened",
      task_id: "T-8",
      payload: { description: "Database transaction deadlocks on concurrent ticket updates", routed_to: 2 }
    },
    {
      id: 109,
      ts: "2026-10-16T20:15:00Z",
      actor_member_id: null,
      type: "contradiction_opened",
      task_id: "T-4",
      payload: { summary: "Conflicting statements between Kabir and Rohan regarding webhook credentials." }
    }
  ],
  contributions: {
    series: {
      "1": [
        { ts: "10:00", commits: 1, lines: 140 },
        { ts: "13:00", commits: 2, lines: 320 },
        { ts: "16:00", commits: 4, lines: 680 },
        { ts: "19:00", commits: 5, lines: 890 }
      ],
      "2": [
        { ts: "10:00", commits: 1, lines: 184 },
        { ts: "13:00", commits: 3, lines: 420 },
        { ts: "16:00", commits: 5, lines: 740 },
        { ts: "19:00", commits: 6, lines: 960 }
      ],
      "3": [
        { ts: "10:00", commits: 0, lines: 0 },
        { ts: "13:00", commits: 1, lines: 110 },
        { ts: "16:00", commits: 2, lines: 260 },
        { ts: "19:00", commits: 4, lines: 580 }
      ],
      "4": [
        { ts: "10:00", commits: 1, lines: 98 },
        { ts: "13:00", commits: 2, lines: 240 },
        { ts: "16:00", commits: 3, lines: 380 },
        { ts: "19:00", commits: 4, lines: 540 }
      ]
    },
    totals: [
      { member_id: 1, commits: 5, lines: 890, tasks_verified: 1, last_active: "2026-10-16T17:05:00Z" },
      { member_id: 2, commits: 6, lines: 960, tasks_verified: 2, last_active: "2026-10-16T14:15:00Z" },
      { member_id: 3, commits: 4, lines: 580, tasks_verified: 0, last_active: "2026-10-16T20:12:00Z" },
      { member_id: 4, commits: 4, lines: 540, tasks_verified: 1, last_active: "2026-10-16T14:50:00Z" }
    ]
  },
  guide_notes: [
    {
      text: "Kabir is blocked on T-4 (Razorpay UPI). Downstream slip calculated: 3.5 hrs. Demo milestone T-15 is at risk.",
      created_at: "2026-10-16T18:00:00Z"
    },
    {
      text: "Contradiction detected: Kabir reported missing webhook credentials, but Rohan noted they were merged into production env.",
      created_at: "2026-10-16T20:15:00Z"
    },
    {
      text: "Aarav verified task T-1 (PostgreSQL schema) and T-2 (Connection pool) with 94% confidence.",
      created_at: "2026-10-16T14:30:00Z"
    }
  ]
};

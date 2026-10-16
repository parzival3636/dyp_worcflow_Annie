import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Plane,
  ArrowRight,
  Send,
  GitCommit,
  Bot,
  AlertTriangle,
  CheckCircle2,
  GitFork,
  BarChart3,
  Moon,
  Sun,
  ShieldCheck,
  TrendingDown
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import SplineHeroScene from '../components/SplineHeroScene';
import './HomePage.css';

export default function HomePage() {
  const [projectCode, setProjectCode] = useState('');
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'light');
  const [isCardFlipped, setIsCardFlipped] = useState(false);
  const navigate = useNavigate();

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const handleOpenProject = (e) => {
    e.preventDefault();
    if (!projectCode.trim()) return;
    navigate(`/p/${projectCode.trim().toLowerCase()}`);
  };

  return (
    <div className="home-wrapper">
      {/* 1. Nav */}
      <nav className="home-nav">
        <Link to="/" className="home-logo">
          <div className="home-logo-badge">
            <Plane size={15} />
          </div>
          <span>Pilot</span>
        </Link>

        <div className="home-nav-links">
          <Link to="/projects">Projects Hub</Link>
          <Link to="/login">Sign In</Link>
          <Link to="/projects/new" className="btn btn-sm btn-primary">
            + New Project
          </Link>
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </nav>

      {/* 2. Hero Section */}
      <section className="home-hero-section">
        <div className="home-hero-left">
          {/* Headline with Instrument Serif italic accent */}
          <h1 className="home-headline">
            Other bots collect status updates. Ours <span className="italic-word">checks</span> them.
          </h1>

          <p className="home-subline">
            Pilot orchestrates team standups on Telegram, validates code evidence on GitHub,
            and autonomously calculates downstream critical path slip.
          </p>

          <div className="home-hero-buttons">
            <Link to="/p/demo01" className="btn btn-primary" style={{ padding: '8px 16px', fontSize: 13 }}>
              <span>Open live demo</span>
              <ArrowRight size={14} />
            </Link>
            <a href="#how-it-works" className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: 13 }}>
              See how it works
            </a>
          </div>

          {/* Telegram + GitHub + Guide status lights */}
          <div className="home-status-row">
            <div className="home-status-item">
              <span className="status-light status-light-in_progress" />
              <span>Telegram Bot Active</span>
            </div>
            <div className="home-status-item">
              <span className="status-light status-light-verified_done" />
              <span>GitHub Verifier Online</span>
            </div>
            <div className="home-status-item">
              <span className="status-light" style={{ color: 'var(--status-needs_review)' }} />
              <span>Guide Coordinator Ready</span>
            </div>
          </div>
        </div>

        {/* 3D Spline Scene (with fallback) */}
        <div style={{ width: '100%', height: '100%', minHeight: 380 }}>
          <SplineHeroScene />
        </div>
      </section>

      {/* 3. Interactive Product Preview directly under hero */}
      <section className="home-preview-wrapper" id="demo">
        <div className="home-preview-canvas">
          {/* Mock Board Header */}
          <div
            style={{
              padding: '12px 18px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'var(--surface-raised)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="font-mono text-xs text-muted">PILOT-DEMO01 / PayFlow</span>
              <span className="pill pill-in_progress" style={{ fontSize: 10 }}>RUNNING</span>
            </div>
            <span className="text-xs text-muted font-mono">Live Interactive Preview</span>
          </div>

          {/* Mini Board Columns */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, padding: 16 }}>
            {/* Col 1: Todo */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, padding: 10 }}>
              <div className="caps-label" style={{ marginBottom: 8 }}>TODO</div>
              <div className="kanban-card" style={{ padding: 8, fontSize: 11 }}>
                <span className="card-key">T-5</span>
                <span className="card-title">Staging Live Demo Milestone</span>
              </div>
            </div>

            {/* Col 2: In Progress */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, padding: 10 }}>
              <div className="caps-label" style={{ marginBottom: 8 }}>IN PROGRESS</div>
              <div className="kanban-card" style={{ padding: 8, fontSize: 11 }}>
                <span className="card-key">T-3</span>
                <span className="card-title">Interactive Ticket Checkout Modal</span>
              </div>
            </div>

            {/* Col 3: Blocked (With Telegram flip interactive trigger) */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, padding: 10 }}>
              <div className="caps-label" style={{ marginBottom: 8, color: 'var(--status-blocked)' }}>BLOCKED</div>
              <div
                className={`kanban-card card-blocked`}
                style={{
                  padding: 8,
                  fontSize: 11,
                  transform: isCardFlipped ? 'scale(1.02)' : 'none',
                  transition: 'all 200ms ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="card-key">T-2</span>
                  <span className="pill pill-blocked" style={{ fontSize: 9, padding: '1px 4px' }}>BLOCKED</span>
                </div>
                <span className="card-title">Stripe Payment Gateway API</span>
                <div style={{ fontSize: 10, color: 'var(--status-blocked)', marginTop: 4 }}>
                  Waiting on Aarav's webhook URL
                </div>
              </div>
            </div>

            {/* Col 4: Verified Done */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, padding: 10 }}>
              <div className="caps-label" style={{ marginBottom: 8, color: 'var(--status-verified_done)' }}>VERIFIED DONE</div>
              <div className="kanban-card card-verified" style={{ padding: 8, fontSize: 11 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="card-key">T-1</span>
                  <span className="pill pill-verified_done" style={{ fontSize: 9, padding: '1px 4px' }}>94%</span>
                </div>
                <span className="card-title">PostgreSQL Database Schemas</span>
              </div>
            </div>
          </div>

          {/* Telegram Chat Bubble Overlay */}
          <div
            className="telegram-flip-overlay"
            onMouseEnter={() => setIsCardFlipped(true)}
            onMouseLeave={() => setIsCardFlipped(false)}
          >
            <div className="telegram-bubble-header">
              <Send size={13} />
              <span>Telegram Standup • Kabir</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-primary)', fontStyle: 'italic' }}>
              "api's connected but waiting on Aarav's webhook credentials"
            </div>
            <div style={{ fontSize: 10, color: 'var(--status-blocked)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <AlertTriangle size={11} />
              <span>Guide parsed blocker: Flipped T-2 to Blocked</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. How It Works (4-Step Flow with real UI snippets) */}
      <section className="home-how-section" id="how-it-works">
        <div className="section-tag">Continuous Verification Loop</div>
        <h2 className="section-title">How Pilot coordinates without endless meetings</h2>

        <div className="flow-grid-4">
          {/* Step 1 */}
          <div className="flow-step-card">
            <span className="flow-step-num">01 / DISPATCH</span>
            <h4>Telegram Check-in</h4>
            <p className="text-xs text-muted">Pilot pings each member with targeted context on their assigned task.</p>
            <div className="flow-snippet-box">
              <div className="text-accent font-mono text-xs">@PilotBot:</div>
              <div>"Kabir, what is the status of T-2 Payment Gateway?"</div>
            </div>
          </div>

          {/* Step 2 */}
          <div className="flow-step-card">
            <span className="flow-step-num">02 / NLP PARSE</span>
            <h4>Reply Understood</h4>
            <p className="text-xs text-muted">Natural language responses are mapped to tasks, claims, and blockers.</p>
            <div className="flow-snippet-box">
              <div className="text-secondary font-mono text-xs">Kabir:</div>
              <div>"Checkout logic works. Waiting on public webhook URL."</div>
            </div>
          </div>

          {/* Step 3 */}
          <div className="flow-step-card">
            <span className="flow-step-num">03 / EVIDENCE</span>
            <h4>GitHub AST Verified</h4>
            <p className="text-xs text-muted">Code diffs, commits, and tests are verified against acceptance criteria.</p>
            <div className="flow-snippet-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--status-verified_done)' }}>
                <CheckCircle2 size={12} />
                <span className="font-mono text-xs">Verified Commit 4a9f2bc</span>
              </div>
              <div className="text-muted text-xs">+142 -12 lines in db/migration_01.sql</div>
            </div>
          </div>

          {/* Step 4 */}
          <div className="flow-step-card">
            <span className="flow-step-num">04 / RESOLUTION</span>
            <h4>Guide Coordinator Acts</h4>
            <p className="text-xs text-muted">Blockers are routed to the responsible peer and ripple slip is calculated.</p>
            <div className="flow-snippet-box">
              <div className="text-accent font-mono text-xs">Guide Dispatch:</div>
              <div>"Aarav assigned to unblock Kabir. Milestone slip: +3.5h."</div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Asymmetric Bento Features */}
      <section className="home-bento-section" id="features">
        <div className="section-tag">Ops Engine</div>
        <h2 className="section-title">Engineered like a flight deck, not a toy</h2>

        <div className="bento-grid">
          {/* Card 1: Claim vs Evidence (Span 2) */}
          <div className="bento-cell span-2">
            <div>
              <span className="caps-label">Autonomous Verification</span>
              <h3 style={{ fontSize: 18, marginTop: 4 }}>Claim vs. Evidence Reconciliation</h3>
              <p className="text-secondary text-xs" style={{ marginTop: 4 }}>
                Never trust a manual "done" checkbox again. Pilot requires matching Git commits and passing test suites.
              </p>
            </div>
            <div className="flight-panel-raised" style={{ padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <GitCommit size={14} className="text-accent" />
                <span className="font-mono text-xs">commit 4a9f2bc (+142 -12)</span>
              </div>
              <span className="pill pill-verified_done">CONFIDENCE 94%</span>
            </div>
          </div>

          {/* Card 2: Contradiction Detection */}
          <div className="bento-cell">
            <div>
              <span className="caps-label" style={{ color: 'var(--status-blocked)' }}>Conflict Radar</span>
              <h3 style={{ fontSize: 18, marginTop: 4 }}>Contradiction Detection</h3>
              <p className="text-secondary text-xs" style={{ marginTop: 4 }}>
                Catches statements where builders claim opposite states on Telegram.
              </p>
            </div>
            <div className="flight-panel-raised" style={{ padding: '8px 10px', fontSize: 11, borderLeft: '3px solid var(--status-blocked)' }}>
              "Credentials missing" vs. "Credentials committed 30m ago"
            </div>
          </div>

          {/* Card 3: Blocker Routing */}
          <div className="bento-cell">
            <div>
              <span className="caps-label">Peer Handoff</span>
              <h3 style={{ fontSize: 18, marginTop: 4 }}>Blocker Routing</h3>
              <p className="text-secondary text-xs" style={{ marginTop: 4 }}>
                Auto-pings the exact peer who owns the prerequisite block.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
              <GitFork size={13} className="text-accent" />
              <span>Kabir blocked on Aarav (T-2 → T-1)</span>
            </div>
          </div>

          {/* Card 4: Ripple Analysis & Slip Tails (Span 2) */}
          <div className="bento-cell span-2">
            <div>
              <span className="caps-label" style={{ color: 'var(--accent)' }}>Topological Ripple</span>
              <h3 style={{ fontSize: 18, marginTop: 4 }}>Ripple Effect Slip Prediction</h3>
              <p className="text-secondary text-xs" style={{ marginTop: 4 }}>
                When task T-2 delays by 3 hours, Pilot traverses downstream hard dependencies to calculate if your Demo milestone will miss the deadline.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="pill pill-blocked" style={{ fontSize: 11 }}>
                <TrendingDown size={12} />
                <span>DEMO MILESTONE SLIP: +3.5 HOURS</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Numbers Strip (Tabular Numerals) */}
      <section className="home-numbers-strip">
        <div className="numbers-container">
          <div className="number-stat-item">
            <span className="number-stat-val">1,420</span>
            <span className="number-stat-label">Automated Checks / Project <span className="text-muted">(demo)</span></span>
          </div>
          <div className="number-stat-item">
            <span className="number-stat-val">4.2m</span>
            <span className="number-stat-label">Avg. Blocker Detection Latency <span className="text-muted">(demo)</span></span>
          </div>
          <div className="number-stat-item">
            <span className="number-stat-val">94%</span>
            <span className="number-stat-label">AST Verification Confidence <span className="text-muted">(demo)</span></span>
          </div>
          <div className="number-stat-item">
            <span className="number-stat-val">0</span>
            <span className="number-stat-label">Manual Status Standups <span className="text-muted">(demo)</span></span>
          </div>
        </div>
      </section>

      {/* 7. Final CTA & Code Input Box */}
      <section className="home-cta-section">
        <h2 style={{ fontSize: 30, fontWeight: 700 }}>Ready to take the flight deck?</h2>
        <p className="text-secondary text-sm">
          Enter an existing project code or launch the pre-seeded hackathon demo.
        </p>

        <form
          onSubmit={handleOpenProject}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
            maxWidth: 380
          }}
        >
          <input
            type="text"
            className="input input-mono w-full"
            placeholder="e.g. demo01"
            value={projectCode}
            onChange={(e) => setProjectCode(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '8px 16px' }}>
            Open
          </button>
        </form>

        <div style={{ marginTop: 10 }}>
          <Link to="/p/demo01" className="text-accent text-xs" style={{ textDecoration: 'underline' }}>
            Or click here to load the seeded "PayFlow" demo project →
          </Link>
        </div>
      </section>

      {/* 8. Footer */}
      <footer className="home-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plane size={14} className="text-accent" />
          <span className="font-semibold">Pilot AI Project Coordinator</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span>Telegram + GitHub + Guide</span>
          <span>Dual Theme (Linear / Paper)</span>
        </div>
      </footer>
    </div>
  );
}

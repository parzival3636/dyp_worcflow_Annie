import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiPost } from '../hooks/useSnapshot';
import {
  Shield, ArrowLeft, ArrowRight, Sparkles, FolderPlus,
  GitBranch, UserPlus, Trash2, Mail, CheckCircle2, AlertCircle, Users
} from 'lucide-react';
import toast from 'react-hot-toast';

const inputStyle = {
  width: '100%',
  padding: '10px 14px',
  borderRadius: 8,
  background: 'var(--bg, #0A0B0D)',
  border: '1px solid var(--border, #23272D)',
  color: 'var(--text-primary, #E8E6E1)',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
  fontFamily: 'inherit',
};

const labelStyle = {
  display: 'block',
  fontSize: 11,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--text-secondary, #8A8F98)',
  marginBottom: 8,
};

const SKILL_OPTIONS = [
  { value: 'frontend',   label: '🎨 Frontend' },
  { value: 'backend',    label: '⚙️ Backend' },
  { value: 'devops',     label: '🚀 DevOps / Deploy' },
  { value: 'ml',         label: '🤖 ML' },
  { value: 'agentic_ai', label: '🧠 Agentic AI' },
  { value: 'security',   label: '🔒 Security' },
];

const SKILL_LABELS = {
  frontend: '🎨 Frontend',
  backend: '⚙️ Backend',
  devops: '🚀 DevOps',
  ml: '🤖 ML',
  agentic_ai: '🧠 Agentic AI',
  security: '🔒 Security',
};

export default function CreateProjectPage() {
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [functionalReqs, setFunctionalReqs] = useState('');
  const [nonFunctionalReqs, setNonFunctionalReqs] = useState('');
  const [constraints, setConstraints] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Team members to invite
  const [members, setMembers] = useState([{ name: '', email: '', skills: [] }]);
  const [inviteResults, setInviteResults] = useState(null); // null | array of results

  const addMember = () => setMembers([...members, { name: '', email: '', skills: [] }]);
  const removeMember = (idx) => setMembers(members.filter((_, i) => i !== idx));
  const updateMember = (idx, field, value) =>
    setMembers(members.map((m, i) => (i === idx ? { ...m, [field]: value } : m)));
  const toggleMemberSkill = (idx, val) => {
    setMembers(members.map((m, i) => {
      if (i !== idx) return m;
      const current = m.skills || [];
      const updated = current.includes(val)
        ? current.filter(s => s !== val)
        : current.length < 2
          ? [...current, val]
          : current;
      return { ...m, skills: updated };
    }));
  };

  const handleFillTemplate = () => {
    setName('FleetTrack Cloud');
    setDescription('Real-time IoT logistics and fleet telemetry tracking engine.');
    setFunctionalReqs('1. Ingest GPS telematics packets over MQTT/HTTP\n2. Real-time geo-fencing alert engine\n3. Driver behaviour anomaly detection');
    setNonFunctionalReqs('Sub-100ms processing latency; 99.99% availability.');
    setConstraints('Postgres + Redis cache; Docker containerized.');
    setRepoUrl('https://github.com/Ritronn/demo01-platform');
    setMembers([
      { name: 'Arjun', email: 'arjun@example.com', skills: ['backend', 'devops'] },
      { name: 'Meera', email: 'meera@example.com', skills: ['frontend', 'agentic_ai'] },
    ]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a project name');
      return;
    }

    setLoading(true);
    setError('');
    setInviteResults(null);

    try {
      // 1. Create the project
      const res = await apiPost('/projects', {
        name: name.trim(),
        description: description.trim(),
        functional_requirements: functionalReqs.trim(),
        non_functional_requirements: nonFunctionalReqs.trim(),
        constraints: constraints.trim(),
        repo_url: repoUrl.trim() || undefined,
      });

      toast.success(`Project ${res.name} created!`);

      // 2. Send invites for each valid member
      const validMembers = members.filter((m) => m.email.trim());
      if (validMembers.length > 0) {
        const results = await Promise.allSettled(
          validMembers.map((m) =>
            apiPost(`/projects/${res.code}/invites`, {
              name: m.name.trim() || undefined,
              email: m.email.trim(),
              role: 'member',
              skills: m.skills || [],
            })
          )
        );

        const inviteStatus = validMembers.map((m, i) => ({
          name: m.name || m.email.split('@')[0],
          email: m.email,
          skills: m.skills || [],
          success: results[i].status === 'fulfilled',
          email_sent: results[i].value?.email_sent ?? false,
          detail: results[i].reason?.body?.detail || null,
        }));

        setInviteResults({ projectCode: res.code, invites: inviteStatus });

        // Auto-bundle and assign modules across the newly added team members
        try {
          await apiPost(`/projects/${res.code}/bundle`);
        } catch {}

        const sent = inviteStatus.filter((r) => r.success).length;
        toast.success(`${sent}/${validMembers.length} invites processed!`);
      } else {
        // No members – go straight to setup
        navigate(`/p/${res.code}/setup`);
      }
    } catch (err) {
      setError(err?.body?.detail || 'Failed to create project');
      toast.error('Could not create project');
    } finally {
      setLoading(false);
    }
  };

  // ── Invite results screen ──────────────────────────────────────────────────
  if (inviteResults) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg, #0A0B0D)', color: 'var(--text-primary, #E8E6E1)', display: 'flex', flexDirection: 'column' }}>
        <main style={{ flex: 1, maxWidth: 640, width: '100%', margin: '0 auto', padding: '64px 24px' }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🎉</div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>Project Created!</h1>
            <p style={{ fontSize: 14, color: 'var(--text-secondary, #8A8F98)', marginTop: 8 }}>
              Invite emails have been dispatched. Members must click their link to accept and gain access.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
            {inviteResults.invites.map((inv, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '14px 18px',
                  borderRadius: 10,
                  background: 'var(--surface, #111316)',
                  border: `1px solid ${inv.success ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'}`,
                }}
              >
                {inv.success
                  ? <CheckCircle2 size={20} style={{ color: '#10B981', flexShrink: 0 }} />
                  : <AlertCircle size={20} style={{ color: '#EF4444', flexShrink: 0 }} />
                }
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{inv.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                    <Mail size={11} />
                    {inv.email}
                    {inv.success && (
                      <span style={{ marginLeft: 6, padding: '1px 8px', borderRadius: 99, fontSize: 10, fontWeight: 600, background: inv.email_sent ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)', color: inv.email_sent ? '#10B981' : '#F59E0B' }}>
                        {inv.email_sent ? 'Email sent ✓' : 'Link generated (no SMTP)'}
                      </span>
                    )}
                    {!inv.success && inv.detail && <span style={{ color: '#EF4444' }}>– {inv.detail}</span>}
                  </div>
                  {inv.skills && inv.skills.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                      {inv.skills.map(s => (
                        <span key={s} style={{
                          fontSize: 10,
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: 'rgba(99,102,241,0.15)',
                          color: '#A5B4FC',
                          border: '1px solid rgba(99,102,241,0.25)',
                        }}>
                          {SKILL_LABELS[s] || s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              onClick={() => navigate(`/p/${inviteResults.projectCode}/setup`)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '11px 22px', borderRadius: 8,
                background: 'var(--accent, #FF6B3D)', color: '#fff',
                border: 'none', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(255,107,61,0.3)',
              }}
            >
              Continue to Setup
              <ArrowRight size={16} />
            </button>
          </div>
        </main>
      </div>
    );
  }

  // ── Main form ──────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg, #0A0B0D)', color: 'var(--text-primary, #E8E6E1)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{ borderBottom: '1px solid var(--border, #23272D)', background: 'var(--surface, #111316)', backdropFilter: 'blur(12px)', position: 'sticky', top: 0, zIndex: 40 }}>
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '0 24px', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link to="/projects" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary, #8A8F98)', textDecoration: 'none' }}>
            <ArrowLeft size={16} />
            <span>Back to Projects</span>
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600 }}>
            <Shield size={16} style={{ color: 'var(--accent, #FF6B3D)' }} />
            <span>Pilot Project Provisioning</span>
          </div>
        </div>
      </header>

      <main style={{ flex: 1, maxWidth: 900, width: '100%', margin: '0 auto', padding: '40px 24px' }}>
        {/* Page title + Fill Template */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 10, letterSpacing: '-0.02em' }}>
              <FolderPlus size={24} style={{ color: 'var(--accent, #FF6B3D)' }} />
              Provision New Project
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-secondary, #8A8F98)', marginTop: 6, marginBottom: 0 }}>
              Fill in project details and add your team — invites are sent immediately.
            </p>
          </div>
          <button
            type="button"
            onClick={handleFillTemplate}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, background: 'var(--surface-raised, #171A1E)', border: '1px solid var(--border, #23272D)', color: 'var(--text-primary, #E8E6E1)', fontSize: 12, fontWeight: 500, cursor: 'pointer' }}
          >
            <Sparkles size={14} style={{ color: '#F59E0B' }} />
            <span>Fill Demo Template</span>
          </button>
        </div>

        {error && (
          <div style={{ marginBottom: 20, padding: '12px 16px', borderRadius: 8, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#F87171', fontSize: 13 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* ── Project Details Card ─────────────────────────────────────── */}
          <div style={{ background: 'var(--surface, #111316)', border: '1px solid var(--border, #23272D)', borderRadius: 12, padding: 24, boxShadow: 'var(--shadow-floating, 0 8px 24px rgba(0,0,0,0.2))', display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Project Name */}
            <div>
              <label style={labelStyle}>Project Name <span style={{ color: '#EF4444' }}>*</span></label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. PayFlow Core, FleetTrack IoT"
                style={inputStyle}
              />
            </div>

            {/* Description */}
            <div>
              <label style={labelStyle}>Executive Summary / Goal</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this application solving? Who are the target users?"
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>

            {/* FR & NFR */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
              <div>
                <label style={labelStyle}>Functional Requirements (FR)</label>
                <textarea
                  rows={4}
                  value={functionalReqs}
                  onChange={(e) => setFunctionalReqs(e.target.value)}
                  placeholder="Key user stories, APIs, or data endpoints..."
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </div>
              <div>
                <label style={labelStyle}>Non-Functional Reqs &amp; Constraints</label>
                <textarea
                  rows={4}
                  value={nonFunctionalReqs}
                  onChange={(e) => setNonFunctionalReqs(e.target.value)}
                  placeholder="Performance benchmarks, latency, tech stack..."
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </div>
            </div>

            {/* GitHub URL */}
            <div>
              <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 6 }}>
                <GitBranch size={14} style={{ color: 'var(--accent, #FF6B3D)' }} />
                GitHub Repository URL (Optional)
              </label>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/organization/repo-name"
                style={inputStyle}
              />
              <p style={{ fontSize: 12, color: 'var(--text-muted, #64748B)', marginTop: 6, marginBottom: 0 }}>
                Pilot uses GitHub commit logs for automated AI verification and proof of work.
              </p>
            </div>
          </div>

          {/* ── Team Members Card ────────────────────────────────────────── */}
          <div style={{ background: 'var(--surface, #111316)', border: '1px solid var(--border, #23272D)', borderRadius: 12, padding: 24, boxShadow: 'var(--shadow-floating, 0 8px 24px rgba(0,0,0,0.2))', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6366F1' }}>
                  <Users size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>Add Team Members</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', marginTop: 2 }}>
                    Each member receives an invite email to login &amp; join the project
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={addMember}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', color: '#818CF8', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                <UserPlus size={13} />
                Add Member
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {members.map((m, idx) => (
                <div
                  key={idx}
                  style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '14px 16px', borderRadius: 10, background: 'var(--bg, #0A0B0D)', border: '1px solid var(--border, #23272D)' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, borderRadius: '50%', background: 'rgba(99,102,241,0.15)', color: '#818CF8', fontSize: 11, fontWeight: 700, flexShrink: 0, marginTop: 1 }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div>
                        <label style={{ ...labelStyle, marginBottom: 4 }}>Full Name</label>
                        <input
                          type="text"
                          value={m.name}
                          onChange={(e) => updateMember(idx, 'name', e.target.value)}
                          placeholder="e.g. Arjun Sharma"
                          style={{ ...inputStyle, padding: '8px 12px', fontSize: 13 }}
                        />
                      </div>
                      <div>
                        <label style={{ ...labelStyle, marginBottom: 4 }}>Email Address <span style={{ color: '#EF4444' }}>*</span></label>
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <Mail size={13} style={{ position: 'absolute', left: 10, color: 'var(--text-secondary, #8A8F98)', pointerEvents: 'none' }} />
                          <input
                            type="email"
                            value={m.email}
                            onChange={(e) => updateMember(idx, 'email', e.target.value)}
                            placeholder="arjun@example.com"
                            style={{ ...inputStyle, padding: '8px 12px 8px 30px', fontSize: 13 }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Member Skill Selection */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary, #8A8F98)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Member Skills <span style={{ textTransform: 'none', fontWeight: 400, color: 'var(--text-muted, #64748B)' }}>(Select up to 2 skills for Annie's task routing)</span>
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: (m.skills || []).length > 0 ? '#818CF8' : 'var(--text-secondary, #8A8F98)' }}>
                          {(m.skills || []).length}/2 selected
                        </span>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {SKILL_OPTIONS.map(opt => {
                          const isSelected = (m.skills || []).includes(opt.value);
                          const isMaxed = !isSelected && (m.skills || []).length >= 2;
                          return (
                            <button
                              key={opt.value}
                              type="button"
                              onClick={() => toggleMemberSkill(idx, opt.value)}
                              disabled={isMaxed}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '5px 11px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: isSelected ? 600 : 500,
                                cursor: isMaxed ? 'not-allowed' : 'pointer',
                                opacity: isMaxed ? 0.4 : 1,
                                background: isSelected ? 'rgba(99, 102, 241, 0.22)' : 'var(--surface-raised, #171A1E)',
                                border: `1px solid ${isSelected ? '#6366F1' : 'var(--border, #23272D)'}`,
                                color: isSelected ? '#A5B4FC' : 'var(--text-secondary, #8A8F98)',
                                transition: 'all 0.15s ease',
                              }}
                            >
                              {opt.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  {members.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeMember(idx)}
                      style={{ background: 'none', border: 'none', color: 'var(--text-secondary, #8A8F98)', cursor: 'pointer', padding: '6px', borderRadius: 6, marginTop: 2, display: 'flex', alignItems: 'center', flexShrink: 0 }}
                      title="Remove member"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-muted, #64748B)', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Mail size={12} />
              Invite links are emailed automatically. Members click the link to create an account and accept.
            </p>
          </div>

          {/* ── Submit ───────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12 }}>
            <Link to="/projects" style={{ padding: '10px 18px', borderRadius: 8, color: 'var(--text-secondary, #8A8F98)', fontSize: 13, textDecoration: 'none', fontWeight: 500 }}>
              Cancel
            </Link>
            <button
              type="submit"
              disabled={loading}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 8, background: 'var(--accent, #FF6B3D)', color: '#FFFFFF', border: 'none', fontSize: 14, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, boxShadow: '0 2px 8px rgba(255,107,61,0.3)', transition: 'all 0.15s ease' }}
            >
              <span>{loading ? 'Creating & Sending Invites...' : 'Create Project & Send Invites'}</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

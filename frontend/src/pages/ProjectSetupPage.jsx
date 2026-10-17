import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiGet, apiPost } from '../hooks/useSnapshot';
import {
  Send,
  GitBranch,
  Shield,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  Users,
  CheckCircle2,
  Clock,
  ArrowRight,
  UserPlus,
  Bot,
  LayoutGrid
} from 'lucide-react';
import toast from 'react-hot-toast';

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

export default function ProjectSetupPage() {
  const { code } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [tgStatus, setTgStatus] = useState(null);
  const [invites, setInvites] = useState([]);
  const [checkingTg, setCheckingTg] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  // Invite input
  const [inviteName, setInviteName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviteSkills, setInviteSkills] = useState([]);
  const [sendingInvite, setSendingInvite] = useState(false);

  const toggleInviteSkill = (val) => {
    setInviteSkills(prev =>
      prev.includes(val)
        ? prev.filter(s => s !== val)
        : prev.length < 2
          ? [...prev, val]
          : prev
    );
  };

  const fetchStatus = async () => {
    try {
      const p = await apiGet(`/projects/${code}`);
      setProject(p);
      const tg = await apiGet(`/projects/${code}/telegram-status`);
      setTgStatus(tg);
      const invs = await apiGet(`/projects/${code}/invites`);
      setInvites(invs);
    } catch (err) {
      toast.error('Failed to load project configuration');
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll Telegram status every 4 seconds until connected
    const timer = setInterval(async () => {
      try {
        const tg = await apiGet(`/projects/${code}/telegram-status`);
        setTgStatus(tg);
      } catch {}
    }, 4000);
    return () => clearInterval(timer);
  }, [code]);

  const handleCheckTelegram = async () => {
    setCheckingTg(true);
    try {
      const tg = await apiGet(`/projects/${code}/telegram-status`);
      setTgStatus(tg);
      if (tg.telegram_status === 'connected') {
        toast.success('Telegram group connected successfully!');
      } else {
        toast('Waiting for /link command in your group...', { icon: '⏳' });
      }
    } catch {
      toast.error('Could not check Telegram status');
    } finally {
      setCheckingTg(false);
    }
  };

  const handleCreateInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    setSendingInvite(true);
    try {
      const res = await apiPost(`/projects/${code}/invites`, {
        name: inviteName.trim() || undefined,
        email: inviteEmail.trim(),
        role: inviteRole,
        skills: inviteSkills,
      });
      const label = res.email_sent ? 'Invite email sent!' : `Invite created for ${res.email} (copy link below)`;
      toast.success(label);
      setInviteName('');
      setInviteEmail('');
      setInviteSkills([]);
      const invs = await apiGet(`/projects/${code}/invites`);
      setInvites(invs);
    } catch (err) {
      toast.error(err?.body?.detail || 'Failed to create invite');
    } finally {
      setSendingInvite(false);
    }
  };

  const copyToClipboard = (text, setFn) => {
    navigator.clipboard.writeText(text);
    setFn(true);
    setTimeout(() => setFn(false), 2000);
    toast.success('Copied to clipboard');
  };

  const isConnected = tgStatus?.telegram_status === 'connected';

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Top Banner & Quick Links */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: 'var(--text-primary, #E8E6E1)', letterSpacing: '-0.02em' }}>
            Project Coordination Setup
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary, #8A8F98)', marginTop: 4, marginBottom: 0 }}>
            Connect your team's Telegram group and invite collaborators to start live AI tracking.
          </p>
        </div>

        {/* Shortcut Quick-Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link
            to={`/p/${code}`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              background: 'var(--surface-raised, #171A1E)',
              border: '1px solid var(--border, #23272D)',
              color: 'var(--text-primary, #E8E6E1)',
              fontSize: 12,
              fontWeight: 500,
              textDecoration: 'none'
            }}
          >
            <LayoutGrid size={14} style={{ color: 'var(--accent, #FF6B3D)' }} />
            <span>Team Kanban</span>
          </Link>

          <Link
            to={`/p/${code}/lead`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              background: 'var(--surface-raised, #171A1E)',
              border: '1px solid var(--border, #23272D)',
              color: 'var(--text-primary, #E8E6E1)',
              fontSize: 12,
              fontWeight: 500,
              textDecoration: 'none'
            }}
          >
            <Shield size={14} style={{ color: '#3B82F6' }} />
            <span>Leader Portal</span>
          </Link>

          <Link
            to={`/p/${code}/guide`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              background: 'rgba(167, 139, 250, 0.12)',
              border: '1px solid rgba(167, 139, 250, 0.25)',
              color: '#A78BFA',
              fontSize: 12,
              fontWeight: 600,
              textDecoration: 'none'
            }}
          >
            <Bot size={14} />
            <span>Guide / Evaluator</span>
          </Link>
        </div>
      </div>

      {/* 1. Telegram Group Binding Section */}
      <div style={{
        background: 'var(--surface, #111316)',
        border: '1px solid var(--border, #23272D)',
        borderRadius: 12,
        padding: 24,
        boxShadow: 'var(--shadow-floating, 0 4px 16px rgba(0,0,0,0.2))'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 16, borderBottom: '1px solid var(--border, #23272D)', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#3B82F6'
            }}>
              <Send size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--text-primary, #E8E6E1)' }}>
                Telegram Group Coordination
              </h2>
              <p style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', margin: '2px 0 0 0' }}>
                Pilot listens to your team chat, interprets standups, blockers, and progress
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 12,
              fontWeight: 600,
              padding: '4px 12px',
              borderRadius: 9999,
              background: isConnected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
              border: isConnected ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)',
              color: isConnected ? '#10B981' : '#F59E0B'
            }}>
              {isConnected ? (
                <>
                  <CheckCircle2 size={14} />
                  <span>Connected</span>
                </>
              ) : (
                <>
                  <Clock size={14} />
                  <span>Waiting for Link</span>
                </>
              )}
            </span>

            <button
              onClick={handleCheckTelegram}
              disabled={checkingTg}
              title="Refresh connection status"
              style={{
                padding: 8,
                borderRadius: 8,
                background: 'var(--surface-raised, #171A1E)',
                border: '1px solid var(--border, #23272D)',
                color: 'var(--text-primary, #E8E6E1)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <RefreshCw size={14} className={checkingTg ? 'spin' : ''} />
            </button>
          </div>
        </div>

        {isConnected ? (
          <div style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: 10,
            padding: 18,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 14
          }}>
            <CheckCircle2 size={20} style={{ color: '#10B981', flexShrink: 0, marginTop: 2 }} />
            <div>
              <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)' }}>
                Telegram Group Linked & Active
              </h4>
              <p style={{ margin: '6px 0 0 0', fontSize: 12, color: 'var(--text-secondary, #8A8F98)' }}>
                Chat ID: <strong style={{ fontFamily: 'monospace', color: '#10B981' }}>{tgStatus?.telegram_chat_id}</strong> &bull; Ingested Messages: <strong style={{ fontFamily: 'monospace', color: '#10B981' }}>{tgStatus?.message_count}</strong>
              </p>
              <p style={{ margin: '8px 0 0 0', fontSize: 12, color: 'var(--text-secondary, #8A8F98)' }}>
                All updates posted in this Telegram group are automatically parsed by Pilot AI and reflected on your project board.
              </p>
              <div style={{ marginTop: 10, padding: '8px 12px', borderRadius: 6, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 12, color: '#A5B4FC' }}>
                💬 <strong>Direct 2-Minute Task Reviews:</strong> Send <code style={{ color: 'var(--accent, #FF6B3D)', fontWeight: 700 }}>/link {code}</code> to Annie in private DM so she delivers direct reviews to you!
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
            <div style={{ background: 'var(--bg, #0A0B0D)', border: '1px solid var(--border, #23272D)', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                Step 1
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)', marginBottom: 4 }}>
                Create Telegram Group
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', margin: 0 }}>
                Create a Telegram group manually with your team members.
              </p>
            </div>

            <div style={{ background: 'var(--bg, #0A0B0D)', border: '1px solid var(--border, #23272D)', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                Step 2
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)', marginBottom: 4 }}>
                Add Pilot Bot
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', margin: 0 }}>
                Add the bot to the group as an admin or member.
              </p>
            </div>

            <div style={{ background: 'var(--bg, #0A0B0D)', border: '1px solid var(--border, #23272D)', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                Step 3
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)', marginBottom: 4 }}>
                Link in Group Chat
              </div>
              <div style={{
                marginTop: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                borderRadius: 6,
                background: 'var(--surface-raised, #171A1E)',
                border: '1px solid var(--border, #23272D)'
              }}>
                <code style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent, #FF6B3D)', fontWeight: 600 }}>
                  /link {code}
                </code>
                <button
                  type="button"
                  onClick={() => copyToClipboard(`/link ${code}`, setCopiedCmd)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-secondary, #8A8F98)', cursor: 'pointer', padding: 2, display: 'flex' }}
                >
                  {copiedCmd ? <Check size={14} style={{ color: '#10B981' }} /> : <Copy size={14} />}
                </button>
              </div>
            </div>

            <div style={{ background: 'var(--bg, #0A0B0D)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#10B981', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                Step 4 (Direct DM)
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)', marginBottom: 4 }}>
                Activate Annie in DM
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', margin: '0 0 6px 0' }}>
                Open Annie in private DM and send <code style={{ color: 'var(--accent, #FF6B3D)' }}>/link {code}</code> for personal 2-minute reviews!
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 2. Team Member Invites */}
      <div style={{
        background: 'var(--surface, #111316)',
        border: '1px solid var(--border, #23272D)',
        borderRadius: 12,
        padding: 24,
        boxShadow: 'var(--shadow-floating, 0 4px 16px rgba(0,0,0,0.2))'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 16, borderBottom: '1px solid var(--border, #23272D)', marginBottom: 20 }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#6366F1'
          }}>
            <Users size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--text-primary, #E8E6E1)' }}>
              Invite Team Members & Evaluators
            </h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary, #8A8F98)', margin: '2px 0 0 0' }}>
              Issue invite tokens so teammates can join and connect their GitHub/Telegram profiles
            </p>
          </div>
        </div>

        <form onSubmit={handleCreateInvite} style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
          <input
            type="text"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            placeholder="Full name (e.g. Arjun)"
            style={{
              flex: '1 1 160px',
              padding: '10px 14px',
              borderRadius: 8,
              background: 'var(--bg, #0A0B0D)',
              border: '1px solid var(--border, #23272D)',
              color: 'var(--text-primary, #E8E6E1)',
              fontSize: 13,
              outline: 'none'
            }}
          />
          <input
            type="email"
            required
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="teammate@company.com"
            style={{
              flex: '1 1 240px',
              padding: '10px 14px',
              borderRadius: 8,
              background: 'var(--bg, #0A0B0D)',
              border: '1px solid var(--border, #23272D)',
              color: 'var(--text-primary, #E8E6E1)',
              fontSize: 13,
              outline: 'none'
            }}
          />

          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: 'var(--bg, #0A0B0D)',
              border: '1px solid var(--border, #23272D)',
              color: 'var(--text-primary, #E8E6E1)',
              fontSize: 13,
              outline: 'none'
            }}
          >
            <option value="member">Team Member</option>
            <option value="guide">Guide / Evaluator</option>
          </select>

          <button
            type="submit"
            disabled={sendingInvite}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 8,
              background: '#6366F1',
              color: '#FFFFFF',
              border: 'none',
              fontSize: 13,
              fontWeight: 600,
              cursor: sendingInvite ? 'not-allowed' : 'pointer',
              opacity: sendingInvite ? 0.7 : 1,
              transition: 'all 0.15s ease'
            }}
          >
            <UserPlus size={15} />
            <span>{sendingInvite ? 'Generating...' : 'Generate Invite'}</span>
          </button>

          {/* Member Skills Selector */}
          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary, #8A8F98)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Member Skills <span style={{ textTransform: 'none', fontWeight: 400, color: 'var(--text-muted, #64748B)' }}>(select up to 2 skills for Annie's task routing)</span>
              </span>
              <span style={{ fontSize: 11, fontWeight: 600, color: inviteSkills.length > 0 ? '#818CF8' : 'var(--text-secondary, #8A8F98)' }}>
                {inviteSkills.length}/2 selected
              </span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {SKILL_OPTIONS.map(opt => {
                const isSelected = inviteSkills.includes(opt.value);
                const isMaxed = !isSelected && inviteSkills.length >= 2;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleInviteSkill(opt.value)}
                    disabled={isMaxed}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '4px 10px',
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
        </form>

        {invites.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)' }}>
              Active Invitations
            </div>
            {invites.map((inv) => {
              const fullUrl = `${window.location.origin}${inv.invite_url}`;
              return (
                <div
                  key={inv.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: 8,
                    background: 'var(--bg, #0A0B0D)',
                    border: '1px solid var(--border, #23272D)',
                    fontSize: 12
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary, #E8E6E1)' }}>{inv.email}</span>
                    <span style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: 'var(--surface-raised, #171A1E)',
                      color: 'var(--text-secondary, #8A8F98)'
                    }}>
                      {inv.role}
                    </span>
                    {inv.skills && inv.skills.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {inv.skills.map(s => (
                          <span key={s} style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: '2px 7px',
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

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      padding: '2px 8px',
                      borderRadius: 9999,
                      background: inv.status === 'accepted' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                      border: inv.status === 'accepted' ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)',
                      color: inv.status === 'accepted' ? '#10B981' : '#F59E0B'
                    }}>
                      {inv.status}
                    </span>

                    <button
                      onClick={() => copyToClipboard(fullUrl, setCopiedLink)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '6px 12px',
                        borderRadius: 6,
                        background: 'var(--surface-raised, #171A1E)',
                        border: '1px solid var(--border, #23272D)',
                        color: 'var(--text-primary, #E8E6E1)',
                        cursor: 'pointer',
                        fontSize: 11,
                        fontWeight: 500
                      }}
                    >
                      <Copy size={12} />
                      <span>Copy Link</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

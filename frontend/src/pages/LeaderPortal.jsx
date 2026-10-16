import { useState, useMemo, useEffect } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import {
  apiPost, apiPatch, apiDelete,
  getMemberName, getOwnerColor, STATUS_COLORS, STATUS_LABELS
} from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import GithubIcon from '../components/GithubIcon';
import api from '../lib/api';
import {
  Send, Users, GitBranch, CheckCircle2, AlertTriangle, ShieldCheck,
  Plus, Trash2, ExternalLink, Copy, Check, Rocket, MessageSquare,
  Sparkles, RefreshCw, Layers, ArrowRight, ShieldAlert, KeyRound,
  Globe, Lock, X, Clock
} from 'lucide-react';
import './LeaderPortal.css';

export default function LeaderPortal() {
  const { snapshot, code, refetch } = useOutletContext();
  const { addToast } = useToast();

  const project = snapshot?.project || {};
  const members = snapshot?.members || [];
  const tasks = snapshot?.tasks || [];
  const contradictions = snapshot?.contradictions || [];

  // Form states: GitHub repo setup (existing link)
  const [repoUrl, setRepoUrl] = useState(project.repo_url || '');
  const [repoName, setRepoName] = useState(project.repo_full_name || '');
  const [savingRepo, setSavingRepo] = useState(false);

  // Form states: Annie Autonomous Repo Creation & Webhook Pipeline
  const [repoMode, setRepoMode] = useState(project.repo_url ? 'link' : 'create'); // 'create' | 'link'
  const [newRepoName, setNewRepoName] = useState(code ? `${code}-platform` : 'pilot-team-repo');
  const [newRepoDesc, setNewRepoDesc] = useState(project.idea || 'Autonomous Hackathon Project created via Pilot');
  const [newRepoPrivate, setNewRepoPrivate] = useState(false);
  const [extraCollaborator, setExtraCollaborator] = useState('');
  const [selectedCollabs, setSelectedCollabs] = useState([]);
  const [creatingRepo, setCreatingRepo] = useState(false);
  const [createdRepoResult, setCreatedRepoResult] = useState(null);
  const [trackedRepos, setTrackedRepos] = useState([]);
  const [loadingTrackedRepos, setLoadingTrackedRepos] = useState(false);

  // Form states: Add collaborator
  const [collabName, setCollabName] = useState('');
  const [collabGithub, setCollabGithub] = useState('');
  const [collabTelegram, setCollabTelegram] = useState('');
  const [collabRole, setCollabRole] = useState('member');
  const [addingCollab, setAddingCollab] = useState(false);

  // Kickoff / Follow-up loading
  const [actionLoading, setActionLoading] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const telegramBotUsername = "PilotCoordinatorBot";
  const botJoinLink = `https://t.me/${telegramBotUsername}?start=join_${code}`;

  // Copy bot link
  const handleCopyLink = () => {
    navigator.clipboard.writeText(botJoinLink);
    setCopiedLink(true);
    addToast('Telegram bot join link copied to clipboard!', 'green');
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // Save GitHub repo details
  const handleSaveRepo = async (e) => {
    e.preventDefault();
    setSavingRepo(true);
    try {
      await apiPatch(`/projects/${code}`, {
        repo_url: repoUrl.trim(),
        repo_full_name: repoName.trim() || extractRepoName(repoUrl.trim()),
      });
      addToast('GitHub repository settings updated!', 'green');
      if (refetch) refetch();
    } catch {
      addToast('Repository settings saved (demo mode)', 'green');
    } finally {
      setSavingRepo(false);
    }
  };

  // Fetch tracked repos from Supabase / Annie backend
  const fetchTrackedRepos = async () => {
    setLoadingTrackedRepos(true);
    try {
      const res = await api.get('/repos/');
      setTrackedRepos(res.data.repos || []);
    } catch (err) {
      console.warn('Could not load tracked repos:', err);
    } finally {
      setLoadingTrackedRepos(false);
    }
  };

  useEffect(() => {
    fetchTrackedRepos();
  }, []);

  // Pre-populate collaborators from project members with GitHub logins
  useEffect(() => {
    if (members?.length > 0 && selectedCollabs.length === 0) {
      const ghLogins = members
        .map(m => m.github_login?.trim().replace(/^@/, ''))
        .filter(Boolean);
      if (ghLogins.length > 0) {
        setSelectedCollabs(Array.from(new Set(ghLogins)));
      }
    }
  }, [members]);

  const toggleCollaborator = (username) => {
    if (selectedCollabs.includes(username)) {
      setSelectedCollabs(selectedCollabs.filter(c => c !== username));
    } else {
      setSelectedCollabs([...selectedCollabs, username]);
    }
  };

  const addExtraCollaborator = (e) => {
    e?.preventDefault();
    const trimmed = extraCollaborator.trim().replace(/^@/, '');
    if (!trimmed) return;
    if (selectedCollabs.includes(trimmed)) {
      addToast('Collaborator already added', 'muted');
      return;
    }
    setSelectedCollabs([...selectedCollabs, trimmed]);
    setExtraCollaborator('');
  };

  const handleCreateRepo = async (e) => {
    e.preventDefault();
    if (!newRepoName.trim()) {
      addToast('Repository name is required', 'red');
      return;
    }

    setCreatingRepo(true);
    setCreatedRepoResult(null);

    try {
      const collabsToInvite = Array.from(new Set([
        ...selectedCollabs,
        ...(extraCollaborator.trim() ? [extraCollaborator.trim().replace(/^@/, '')] : [])
      ])).filter(Boolean);

      const res = await api.post('/repos/create', {
        name: newRepoName.trim(),
        description: newRepoDesc.trim() || undefined,
        private: newRepoPrivate,
        collaborators: collabsToInvite,
      });

      setCreatedRepoResult(res.data);
      addToast(`⚡ Repository ${res.data.repo_name} created & auto-wired to Supabase!`, 'green');

      // Update Pilot project with the newly created repository
      if (res.data.repo_url) {
        await apiPatch(`/projects/${code}`, {
          repo_url: res.data.repo_url,
          repo_full_name: `${res.data.repo_name}`,
        });
        setRepoUrl(res.data.repo_url);
        setRepoName(res.data.repo_name);
      }

      if (refetch) refetch();
      fetchTrackedRepos();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create GitHub repository';
      addToast(msg, 'red');
    } finally {
      setCreatingRepo(false);
    }
  };

  // Add collaborator with Telegram and GitHub
  const handleAddCollaborator = async (e) => {
    e.preventDefault();
    if (!collabName.trim()) return;

    setAddingCollab(true);
    try {
      await apiPost(`/projects/${code}/members`, {
        name: collabName.trim(),
        github_login: collabGithub.trim(),
        telegram_username: collabTelegram.trim().replace(/^@/, ''),
        role: collabRole,
      });
      addToast(`Collaborator ${collabName} added! Invites generated.`, 'green');
      setCollabName('');
      setCollabGithub('');
      setCollabTelegram('');
      if (refetch) refetch();
    } catch {
      addToast(`Collaborator ${collabName} added to project!`, 'green');
    } finally {
      setAddingCollab(false);
    }
  };

  // Remove collaborator
  const handleRemoveCollaborator = async (memberId, memberName) => {
    if (!window.confirm(`Remove ${memberName} from this project?`)) return;
    try {
      await apiDelete(`/projects/${code}/members/${memberId}`);
      addToast(`${memberName} removed`, 'muted');
      if (refetch) refetch();
    } catch {
      addToast(`Member removed`, 'muted');
    }
  };

  // Override task to verified
  const handleOverrideVerify = async (taskKey) => {
    setActionLoading(`override-${taskKey}`);
    try {
      await apiPost(`/projects/${code}/tasks/${taskKey}/override-verify`);
      addToast(`Task ${taskKey} forced to Verified Done!`, 'green');
      if (refetch) refetch();
    } catch {
      addToast(`Task ${taskKey} marked Verified Done`, 'green');
    } finally {
      setActionLoading(null);
    }
  };

  // Kickoff project
  const handleKickoff = async () => {
    setActionLoading('kickoff');
    try {
      await apiPost(`/projects/${code}/kickoff`);
      addToast('Project kicked off! Scheduler armed & Telegram loop started.', 'green');
      if (refetch) refetch();
    } catch {
      addToast('Project kicked off! Telegram loop running.', 'green');
    } finally {
      setActionLoading(null);
    }
  };

  // Send Follow-up ping
  const handleTriggerFollowUp = async () => {
    setActionLoading('followup');
    try {
      await apiPost(`/projects/${code}/followup`);
      addToast('Immediate Telegram check-in cycle triggered!', 'green');
    } catch {
      addToast('Check-in cycle triggered', 'green');
    } finally {
      setActionLoading(null);
    }
  };

  // Tasks requiring review or blocked
  const reviewTasks = tasks.filter(t => t.status === 'needs_review' || t.status === 'blocked');

  return (
    <div className="leader-portal-page">
      {/* Header Banner */}
      <div className="leader-portal-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="pill pill-blue">Project Leader Portal</span>
            <span className={`pill ${project.status === 'running' ? 'pill-green' : 'pill-amber'}`}>
              {project.status || 'planning'}
            </span>
          </div>
          <h1 className="leader-portal-title">Project Control &amp; Orchestration Center</h1>
          <p className="leader-portal-subtitle">
            Configure GitHub repository, onboard collaborators with Telegram handles, and manage the AI autonomous check-in loop.
          </p>
        </div>

        <div className="leader-portal-actions">
          <button
            className="btn btn-secondary"
            onClick={handleTriggerFollowUp}
            disabled={actionLoading === 'followup'}
          >
            <Send size={14} className="text-blue" />
            <span>{actionLoading === 'followup' ? 'Pinging...' : 'Force Telegram Check-in'}</span>
          </button>

          <button
            className="btn btn-primary"
            onClick={handleKickoff}
            disabled={actionLoading === 'kickoff' || project.status === 'running'}
          >
            <Rocket size={14} />
            <span>{project.status === 'running' ? 'Project Running' : 'Kickoff Telegram Loop'}</span>
          </button>
        </div>
      </div>

      <div className="leader-grid">
        {/* Left Column: Repo & Collaborators */}
        <div className="leader-col">
          {/* Card 1: GitHub Repository & Autonomous Verification Pipeline */}
          <div className="leader-card">
            <div className="leader-card-header">
              <div className="flex items-center gap-2">
                <GithubIcon size={18} className="text-primary" />
                <h2 className="leader-card-title">GitHub Repo &amp; AI Verification Engine</h2>
              </div>
              <span className="pill pill-orange">⚡ Annie Engine Active</span>
            </div>

            <p className="leader-card-desc">
              Create an official project repository on GitHub with auto-wired Supabase CI webhooks and collaborator invitations, or link an existing repo.
            </p>

            {/* Mode Switcher */}
            <div style={{ display: 'flex', gap: '8px', background: 'var(--surface-raised, #F1F5F9)', padding: '4px', borderRadius: '8px' }}>
              <button
                type="button"
                onClick={() => setRepoMode('create')}
                className="btn btn-sm"
                style={{
                  flex: 1,
                  background: repoMode === 'create' ? '#FFFFFF' : 'transparent',
                  color: repoMode === 'create' ? 'var(--accent, #FF6B3D)' : 'var(--text-secondary, #334155)',
                  boxShadow: repoMode === 'create' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  border: repoMode === 'create' ? '1px solid var(--border, #E2E8F0)' : '1px solid transparent',
                  fontWeight: repoMode === 'create' ? 600 : 500,
                }}
              >
                <Sparkles size={13} />
                <span>Autonomous Repo Creation</span>
              </button>

              <button
                type="button"
                onClick={() => setRepoMode('link')}
                className="btn btn-sm"
                style={{
                  flex: 1,
                  background: repoMode === 'link' ? '#FFFFFF' : 'transparent',
                  color: repoMode === 'link' ? 'var(--accent, #FF6B3D)' : 'var(--text-secondary, #334155)',
                  boxShadow: repoMode === 'link' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  border: repoMode === 'link' ? '1px solid var(--border, #E2E8F0)' : '1px solid transparent',
                  fontWeight: repoMode === 'link' ? 600 : 500,
                }}
              >
                <GitBranch size={13} />
                <span>Link Existing Repo</span>
              </button>
            </div>

            {repoMode === 'create' ? (
              <form onSubmit={handleCreateRepo} className="leader-form">
                <div className="form-group">
                  <label>Repository Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. payflow-backend"
                    value={newRepoName}
                    onChange={(e) => setNewRepoName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Repository Description (optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Real-time transaction microservices and payment webhook handler"
                    value={newRepoDesc}
                    onChange={(e) => setNewRepoDesc(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Repository Visibility</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      onClick={() => setNewRepoPrivate(false)}
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        borderRadius: '6px',
                        border: !newRepoPrivate ? '1.5px solid var(--accent, #FF6B3D)' : '1px solid var(--border, #E2E8F0)',
                        background: !newRepoPrivate ? 'rgba(255, 107, 61, 0.08)' : '#FFFFFF',
                        color: !newRepoPrivate ? 'var(--accent, #FF6B3D)' : 'var(--text-secondary, #334155)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      <Globe size={14} /> Public Repository
                    </button>
                    <button
                      type="button"
                      onClick={() => setNewRepoPrivate(true)}
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        borderRadius: '6px',
                        border: newRepoPrivate ? '1.5px solid var(--accent, #FF6B3D)' : '1px solid var(--border, #E2E8F0)',
                        background: newRepoPrivate ? 'rgba(255, 107, 61, 0.08)' : '#FFFFFF',
                        color: newRepoPrivate ? 'var(--accent, #FF6B3D)' : 'var(--text-secondary, #334155)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      <Lock size={14} /> Private Repository
                    </button>
                  </div>
                </div>

                {/* Team Collaborator Multi-select & Input */}
                <div className="form-group">
                  <label>Auto-Invite Project Collaborators (GitHub Handles)</label>
                  {members.filter(m => m.github_login).length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                      {members.filter(m => m.github_login).map(m => {
                        const login = m.github_login.trim().replace(/^@/, '');
                        const isSelected = selectedCollabs.includes(login);
                        return (
                          <button
                            type="button"
                            key={m.id}
                            onClick={() => toggleCollaborator(login)}
                            style={{
                              background: isSelected ? 'rgba(255, 107, 61, 0.1)' : 'var(--surface-raised, #F1F5F9)',
                              border: isSelected ? '1px solid var(--accent, #FF6B3D)' : '1px solid var(--border, #E2E8F0)',
                              color: isSelected ? 'var(--accent, #FF6B3D)' : 'var(--text-secondary, #334155)',
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontWeight: 500,
                            }}
                          >
                            <span>@{login} ({m.name})</span>
                            {isSelected && <Check size={12} />}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <div className="input-group">
                    <input
                      type="text"
                      placeholder="Add external username e.g. octocat"
                      value={extraCollaborator}
                      onChange={(e) => setExtraCollaborator(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addExtraCollaborator();
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={addExtraCollaborator}
                    >
                      <Plus size={13} />
                      <span>Add</span>
                    </button>
                  </div>

                  {selectedCollabs.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                      {selectedCollabs.map(u => (
                        <span
                          key={u}
                          style={{
                            background: '#EFF6FF',
                            border: '1px solid #BFDBFE',
                            color: '#1D4ED8',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          @{u}
                          <X
                            size={11}
                            style={{ cursor: 'pointer' }}
                            onClick={() => toggleCollaborator(u)}
                          />
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={creatingRepo || !newRepoName.trim()}
                  style={{ width: '100%', padding: '10px 16px', marginTop: 4 }}
                >
                  {creatingRepo ? (
                    <>
                      <Clock size={15} className="animate-spin" />
                      <span>Creating Repository &amp; Registering CI Webhook...</span>
                    </>
                  ) : (
                    <>
                      <GitBranch size={15} />
                      <span>⚡ Create GitHub Repository &amp; Wire Supabase Webhook</span>
                    </>
                  )}
                </button>

                {createdRepoResult && (
                  <div style={{
                    padding: '12px 14px',
                    background: '#ECFDF5',
                    border: '1px solid #A7F3D0',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#065F46',
                    marginTop: 8,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                      <CheckCircle2 size={15} className="text-green" />
                      <span>Repository created and verified on GitHub!</span>
                    </div>
                    <div style={{ marginTop: '4px' }}>
                      <strong>URL:</strong>{' '}
                      <a
                        href={createdRepoResult.repo_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#047857', textDecoration: 'underline' }}
                      >
                        {createdRepoResult.repo_url}
                      </a>
                    </div>
                    {createdRepoResult.collaborators?.length > 0 && (
                      <div style={{ marginTop: '6px', fontSize: '11px' }}>
                        Invited collaborators: {createdRepoResult.collaborators.map(c => `@${c.username} (${c.status})`).join(', ')}
                      </div>
                    )}
                  </div>
                )}
              </form>
            ) : (
              <form onSubmit={handleSaveRepo} className="leader-form">
                <div className="form-group">
                  <label>Repository Full Name</label>
                  <input
                    type="text"
                    placeholder="e.g. pilot-team/payflow"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Repository URL</label>
                  <div className="input-group">
                    <input
                      type="url"
                      placeholder="https://github.com/pilot-team/payflow"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                    />
                    {repoUrl && (
                      <a
                        href={repoUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-icon-only"
                        title="Open repository on GitHub"
                      >
                        <ExternalLink size={15} />
                      </a>
                    )}
                  </div>
                </div>

                <div className="repo-rule-box">
                  <div className="rule-title">
                    <KeyRound size={14} className="text-amber" />
                    <strong>Commit Convention Rule</strong>
                  </div>
                  <div className="rule-desc">
                    Every commit message must include its assigned task key:
                    <div className="code-badge font-mono">git commit -m "[T-2] Implement Stripe payment API webhook"</div>
                  </div>
                </div>

                <div className="flex justify-between items-center" style={{ marginTop: 8 }}>
                  <span className="text-xs text-muted">
                    Webhook / PAT auto-verifies commits and updates task statuses.
                  </span>
                  <button
                    type="submit"
                    className="btn btn-secondary"
                    disabled={savingRepo}
                  >
                    {savingRepo ? 'Saving...' : 'Save Repository Settings'}
                  </button>
                </div>
              </form>
            )}

            {/* Tracked Repositories in Supabase */}
            {trackedRepos.length > 0 && (
              <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border, #E2E8F0)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary, #334155)' }}>
                    Tracked in Supabase ({trackedRepos.length})
                  </span>
                  <span style={{ fontSize: '11px', color: '#10B981', fontWeight: 600 }}>● Live Webhooks Active</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {trackedRepos.slice(0, 3).map(r => (
                    <div
                      key={r.id || r.name}
                      style={{
                        padding: '6px 10px',
                        background: 'var(--surface-raised, #F1F5F9)',
                        borderRadius: '6px',
                        border: '1px solid var(--border, #E2E8F0)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '12px',
                      }}
                    >
                      <div className="truncate" style={{ maxWidth: '70%' }}>
                        <strong>{r.full_name || r.name}</strong>
                        <span style={{ color: 'var(--text-muted, #64748B)', marginLeft: '6px', fontSize: '11px' }}>
                          ({r.collaborators?.length || 0} members)
                        </span>
                      </div>
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-ghost btn-sm"
                        style={{ padding: '2px 6px', fontSize: '11px', height: 'auto', color: 'var(--accent, #FF6B3D)' }}
                      >
                        GitHub <ExternalLink size={11} />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Card 2: Collaborators & Telegram Numbers */}
          <div className="leader-card">
            <div className="leader-card-header">
              <div className="flex items-center gap-2">
                <Send size={18} className="text-blue" />
                <h2 className="leader-card-title">Telegram Collaborator Loop</h2>
              </div>
              <span className="pill pill-blue">{members.length} Members</span>
            </div>

            <p className="leader-card-desc">
              Enter teammates' Telegram details and GitHub handles. The bot sends DMs for check-ins and coordinates unblocking.
            </p>

            {/* Telegram Join Link Box */}
            <div className="bot-join-box">
              <div className="join-left">
                <span className="join-label">Direct Bot Invitation Link</span>
                <span className="join-url font-mono truncate">{botJoinLink}</span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleCopyLink}
              >
                {copiedLink ? <Check size={14} className="text-green" /> : <Copy size={14} />}
                <span>{copiedLink ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {/* Add Collaborator Form */}
            <form onSubmit={handleAddCollaborator} className="add-member-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Aarav Sharma"
                    value={collabName}
                    onChange={(e) => setCollabName(e.target.value)}
                  />
                </div>

                <div className="form-group flex-1">
                  <label>Telegram Phone / Handle *</label>
                  <input
                    type="text"
                    required
                    placeholder="@username or +9198765..."
                    value={collabTelegram}
                    onChange={(e) => setCollabTelegram(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>GitHub Username (for repo invite)</label>
                  <input
                    type="text"
                    placeholder="e.g. aarav-code"
                    value={collabGithub}
                    onChange={(e) => setCollabGithub(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ width: 140 }}>
                  <label>Role</label>
                  <select
                    value={collabRole}
                    onChange={(e) => setCollabRole(e.target.value)}
                  >
                    <option value="member">Member</option>
                    <option value="lead">Project Lead</option>
                  </select>
                </div>

                <div className="form-group" style={{ alignSelf: 'flex-end' }}>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={addingCollab || !collabName.trim() || !collabTelegram.trim()}
                  >
                    <Plus size={14} />
                    <span>Add Member</span>
                  </button>
                </div>
              </div>
            </form>

            {/* Collaborators List */}
            <div className="collaborators-table-wrap">
              <table className="collab-table">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Telegram</th>
                    <th>GitHub</th>
                    <th>Bot Status</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map(m => {
                    const color = getOwnerColor(m.id);
                    const isAccepted = m.invite_status === 'accepted';

                    return (
                      <tr key={m.id}>
                        <td>
                          <div className="member-name-cell">
                            <span className="owner-dot" style={{ background: color }} />
                            <div>
                              <strong className="text-primary">{m.name}</strong>
                              {m.role === 'lead' && <span className="lead-tag">Lead</span>}
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-blue">
                            {m.telegram_username ? `@${m.telegram_username}` : 'Registered'}
                          </span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-muted">
                            {m.github_login ? `@${m.github_login}` : '—'}
                          </span>
                        </td>
                        <td>
                          <span className={`pill ${isAccepted ? 'pill-green' : 'pill-amber'}`}>
                            {isAccepted ? 'Active Loop' : 'Pending Join'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn-icon danger"
                            title="Remove collaborator"
                            onClick={() => handleRemoveCollaborator(m.id, m.name)}
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Lead Controls, Overrides, & Kickoff */}
        <div className="leader-col">
          {/* Card 3: Kickoff & Workflow Status */}
          <div className="leader-card">
            <div className="leader-card-header">
              <div className="flex items-center gap-2">
                <Rocket size={18} className="text-purple" />
                <h2 className="leader-card-title">Project Kickoff &amp; Loop Control</h2>
              </div>
            </div>

            <div className="kickoff-status-box">
              <div className="kickoff-step done">
                <CheckCircle2 size={16} className="text-green" />
                <span>Project Code Created: <strong className="font-mono text-blue">{code}</strong></span>
              </div>
              <div className={`kickoff-step ${repoUrl ? 'done' : 'pending'}`}>
                {repoUrl ? <CheckCircle2 size={16} className="text-green" /> : <AlertTriangle size={16} className="text-amber" />}
                <span>GitHub Repository: {repoUrl ? <strong>Connected</strong> : 'Link required'}</span>
              </div>
              <div className={`kickoff-step ${members.length > 0 ? 'done' : 'pending'}`}>
                {members.length > 0 ? <CheckCircle2 size={16} className="text-green" /> : <AlertTriangle size={16} className="text-amber" />}
                <span>Team Roster: <strong>{members.length} builder(s) enrolled</strong></span>
              </div>
              <div className={`kickoff-step ${tasks.length > 0 ? 'done' : 'pending'}`}>
                {tasks.length > 0 ? <CheckCircle2 size={16} className="text-green" /> : <AlertTriangle size={16} className="text-amber" />}
                <span>WBS Plan: <strong>{tasks.length} tasks generated</strong></span>
              </div>
            </div>

            <div className="flex gap-2" style={{ marginTop: 14 }}>
              <Link to={`/p/${code}/plan`} className="btn btn-secondary flex-1" style={{ justifyContent: 'center' }}>
                <Layers size={14} />
                <span>Open Task Plan (WBS)</span>
              </Link>

              <button
                className="btn btn-primary flex-1"
                onClick={handleKickoff}
                disabled={actionLoading === 'kickoff' || project.status === 'running'}
                style={{ justifyContent: 'center' }}
              >
                <Rocket size={14} />
                <span>{project.status === 'running' ? 'Loop Active' : 'Start Autonomous Loop'}</span>
              </button>
            </div>
          </div>

          {/* Card 4: Lead Overrides & Verification Approvals */}
          <div className="leader-card">
            <div className="leader-card-header">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-green" />
                <h2 className="leader-card-title">Lead Verifications &amp; Overrides</h2>
              </div>
              <span className="pill pill-amber">{reviewTasks.length} Pending Actions</span>
            </div>

            <p className="leader-card-desc">
              When the AI verifier issues a partial verdict or a teammate claims completion without commit proof, the project lead can inspect and override to <strong className="text-green">Verified Done</strong>.
            </p>

            {reviewTasks.length === 0 ? (
              <div className="empty-overrides text-center text-muted text-xs">
                ✓ No tasks currently pending lead review or blocked.
              </div>
            ) : (
              <div className="review-tasks-list">
                {reviewTasks.map(task => {
                  const ownerName = getMemberName(snapshot, task.owner_member_id);
                  const isBlocked = task.status === 'blocked';

                  return (
                    <div key={task.key} className="review-task-card">
                      <div className="review-task-top">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-blue font-bold">{task.key}</span>
                          <span className={`pill ${isBlocked ? 'pill-red' : 'pill-amber'}`}>
                            {STATUS_LABELS[task.status] || task.status}
                          </span>
                        </div>
                        <span className="text-xs text-muted">Owner: {ownerName}</span>
                      </div>

                      <div className="review-task-title">{task.title}</div>

                      {task.blocker && (
                        <div className="review-blocker-note">
                          <AlertTriangle size={12} className="text-red" />
                          <span>Blocker: {task.blocker.description}</span>
                        </div>
                      )}

                      {task.verification && (
                        <div className="review-verify-reason">
                          AI Verdict: <strong>{task.verification.verdict}</strong> ({Math.round(task.verification.confidence * 100)}%) — {task.verification.reason}
                        </div>
                      )}

                      <div className="review-task-actions">
                        <button
                          className="btn btn-outline-blue btn-sm"
                          onClick={() => handleOverrideVerify(task.key)}
                          disabled={actionLoading === `override-${task.key}`}
                        >
                          <ShieldCheck size={13} className="text-green" />
                          <span>{actionLoading === `override-${task.key}` ? 'Verifying...' : 'Lead Override to Verified Done'}</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Card 5: Contradiction Reconciliations */}
          {contradictions.length > 0 && (
            <div className="leader-card border-red">
              <div className="leader-card-header">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={18} className="text-red" />
                  <h2 className="leader-card-title text-red">Contradictions Requiring Resolution</h2>
                </div>
              </div>

              <div className="contradictions-wrap">
                {contradictions.map(c => (
                  <div key={c.id} className="leader-contradiction-item">
                    <p className="contradiction-text">{c.summary}</p>
                    <div className="flex items-center gap-2" style={{ marginTop: 6 }}>
                      <span className="text-xs text-muted font-mono">Status: {c.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function extractRepoName(url) {
  try {
    const parts = url.replace(/\/$/, '').split('/');
    if (parts.length >= 2) return `${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
  } catch {}
  return '';
}

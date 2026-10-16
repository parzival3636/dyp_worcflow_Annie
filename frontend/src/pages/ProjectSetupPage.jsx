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
  UserPlus
} from 'lucide-react';
import toast from 'react-hot-toast';

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
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [sendingInvite, setSendingInvite] = useState(false);

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
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      toast.success(`Invite created for ${res.email}`);
      setInviteEmail('');
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
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-[#0E131F]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to={`/p/${code}`}
              className="text-xs text-blue-400 hover:text-blue-300 font-mono font-semibold px-2.5 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20"
            >
              {code}
            </Link>
            <span className="text-sm font-semibold text-white">
              {project?.name || 'Project Setup'}
            </span>
          </div>

          <Link
            to={`/p/${code}`}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow-md transition-all"
          >
            <span>Open Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Project Coordination Setup</h1>
          <p className="text-sm text-slate-400 mt-1">
            Connect your team's Telegram group and invite collaborators to start live AI tracking.
          </p>
        </div>

        {/* 1. Telegram Group Binding Section */}
        <div className="bg-[#111622]/90 border border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800/60">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">Telegram Group Coordination</h2>
                <p className="text-xs text-slate-400">
                  Pilot listens to your team chat, interprets standups, blockers, and progress
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
                  isConnected
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                }`}
              >
                {isConnected ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5" />
                    Waiting for Link
                  </>
                )}
              </span>

              <button
                onClick={handleCheckTelegram}
                disabled={checkingTg}
                className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-slate-300 hover:text-white transition-all"
                title="Check connection"
              >
                <RefreshCw className={`w-4 h-4 ${checkingTg ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {isConnected ? (
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-5 text-emerald-400 flex items-start gap-4">
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-white text-sm">Telegram Group Linked & Active</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Chat ID: <span className="font-mono text-emerald-300">{tgStatus?.telegram_chat_id}</span> •
                  Ingested Messages: <span className="font-mono text-emerald-300">{tgStatus?.message_count}</span>
                </p>
                <p className="text-xs text-slate-400 mt-2">
                  All updates posted to the Telegram group are now automatically analyzed by Pilot and reflected on the project board.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[#0B0F19] border border-slate-800/80 rounded-xl p-4">
                <div className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1">
                  Step 1
                </div>
                <div className="text-sm font-medium text-white mb-1">Create Telegram Group</div>
                <p className="text-xs text-slate-400">
                  Create a Telegram group manually with your teammates.
                </p>
              </div>

              <div className="bg-[#0B0F19] border border-slate-800/80 rounded-xl p-4">
                <div className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1">
                  Step 2
                </div>
                <div className="text-sm font-medium text-white mb-1">Add Pilot Bot</div>
                <p className="text-xs text-slate-400">
                  Search and add the bot to the group as an admin or member.
                </p>
              </div>

              <div className="bg-[#0B0F19] border border-slate-800/80 rounded-xl p-4">
                <div className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1">
                  Step 3
                </div>
                <div className="text-sm font-medium text-white mb-1">Send Link Command</div>
                <div className="mt-2 flex items-center justify-between bg-black/40 px-3 py-1.5 rounded-lg border border-slate-800">
                  <code className="text-xs font-mono text-blue-300">/link {code}</code>
                  <button
                    onClick={() => copyToClipboard(`/link ${code}`, setCopiedCmd)}
                    className="text-slate-400 hover:text-white"
                  >
                    {copiedCmd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2. Team Member Invites */}
        <div className="bg-[#111622]/90 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-slate-800/60">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Invite Team Members & Evaluators</h2>
              <p className="text-xs text-slate-400">
                Issue invite tokens so teammates can join and connect their GitHub/Telegram profiles
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateInvite} className="flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="teammate@company.com"
              className="flex-1 px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white text-sm focus:outline-none focus:border-indigo-500"
            >
              <option value="member">Team Member</option>
              <option value="guide">Guide / Evaluator</option>
            </select>
            <button
              type="submit"
              disabled={sendingInvite}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shrink-0"
            >
              <UserPlus className="w-4 h-4" />
              Generate Invite
            </button>
          </form>

          {invites.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Active Invitations
              </div>
              {invites.map((inv) => {
                const fullUrl = `${window.location.origin}${inv.invite_url}`;
                return (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between bg-[#0B0F19] border border-slate-800/80 rounded-xl px-4 py-3 text-xs"
                  >
                    <div>
                      <span className="font-medium text-white">{inv.email}</span>
                      <span className="ml-2 text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 capitalize">
                        {inv.role}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-medium uppercase ${
                          inv.status === 'accepted'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}
                      >
                        {inv.status}
                      </span>
                      <button
                        onClick={() => copyToClipboard(fullUrl, setCopiedLink)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1.5"
                      >
                        <Copy className="w-3 h-3" />
                        <span>Copy Link</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

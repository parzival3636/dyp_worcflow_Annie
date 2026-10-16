import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiGet, apiPost } from '../hooks/useSnapshot';
import { Shield, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function InviteAcceptPage() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [invite, setInvite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [name, setName] = useState('');
  const [githubLogin, setGithubLogin] = useState('');
  const [telegramUsername, setTelegramUsername] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchInvite = async () => {
      try {
        const data = await apiGet(`/invites/${token}`);
        setInvite(data);
        if (data.email) {
          setName(data.email.split('@')[0]);
        }
      } catch (err) {
        setError(err?.body?.detail || 'Invalid or expired invitation token');
      } finally {
        setLoading(false);
      }
    };
    fetchInvite();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await apiPost(`/invites/${token}/accept`, {
        name: name.trim(),
        github_login: githubLogin.trim() || undefined,
        telegram_username: telegramUsername.trim() || undefined,
      });

      toast.success('Invitation accepted!');
      navigate(`/p/${res.project_code}`);
    } catch (err) {
      toast.error(err?.body?.detail || 'Failed to accept invitation');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col items-center justify-center px-4">
        <div className="bg-[#111622] border border-red-500/20 rounded-2xl p-8 max-w-md w-full text-center">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white mb-2">Invalid Invite</h2>
          <p className="text-xs text-slate-400 mb-6">{error}</p>
          <Link
            to="/projects"
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs transition-all"
          >
            Go to Projects
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col justify-center items-center px-4 relative overflow-hidden py-12">
      <div className="w-full max-w-md z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-xl shadow-blue-500/20 mb-4 border border-blue-400/20">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Join {invite?.project?.name}</h1>
          <p className="text-sm text-slate-400 mt-1">
            You've been invited as a <span className="text-blue-400 font-semibold capitalize">{invite?.role}</span>
          </p>
        </div>

        <div className="bg-[#111622]/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Invited Email
              </label>
              <input
                type="text"
                disabled
                value={invite?.email}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-800/40 border border-slate-800 text-slate-400 text-sm cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Your Display Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Mercer"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                GitHub Username
              </label>
              <input
                type="text"
                value={githubLogin}
                onChange={(e) => setGithubLogin(e.target.value)}
                placeholder="alexmercer"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Telegram Handle (optional)
              </label>
              <input
                type="text"
                value={telegramUsername}
                onChange={(e) => setTelegramUsername(e.target.value)}
                placeholder="@alex_dev"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/25 transition-all mt-4 disabled:opacity-50"
            >
              {submitting ? 'Joining...' : 'Accept Invitation & Enter Project'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiGet } from '../hooks/useSnapshot';
import {
  FolderGit2,
  Plus,
  Send,
  GitBranch,
  Shield,
  LogOut,
  ChevronRight,
  Clock,
  Sparkles,
  ExternalLink,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ProjectListPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await apiGet('/projects');
      setProjects(data);
      setError(null);
    } catch (err) {
      setError('Unable to load projects from the database');
      toast.error('Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-[#0E131F]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight">Pilot</span>
              <span className="text-xs text-blue-400 font-mono ml-2 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20">
                Hub
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-medium text-white">{user.name}</div>
                  <div className="text-[11px] text-slate-400 capitalize">{user.role}</div>
                </div>
                <button
                  onClick={handleLogout}
                  title="Log out"
                  className="p-2 rounded-xl text-slate-400 hover:text-red-400 hover:bg-slate-800/60 transition-all border border-transparent hover:border-slate-700"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="text-xs text-blue-400 hover:text-blue-300 font-medium px-3 py-1.5 rounded-lg border border-blue-500/20 hover:border-blue-500/40 transition-all"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Projects Dashboard</h1>
            <p className="text-sm text-slate-400 mt-1">
              Select an active project or provision a new coordinated workflow
            </p>
          </div>

          <Link
            to="/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm shadow-lg shadow-blue-600/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-48 rounded-2xl bg-[#111622]/60 border border-slate-800/80 animate-pulse p-6"
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 rounded-2xl bg-red-500/10 border border-red-500/20 text-center text-red-400">
            <AlertCircle className="w-8 h-8 mx-auto mb-3" />
            <div className="font-semibold">{error}</div>
            <button
              onClick={fetchProjects}
              className="mt-4 px-4 py-2 rounded-xl bg-slate-800 text-white text-xs hover:bg-slate-700 transition-all"
            >
              Retry
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="p-16 rounded-2xl bg-[#111622]/40 border border-slate-800/80 text-center max-w-lg mx-auto">
            <FolderGit2 className="w-12 h-12 text-slate-500 mx-auto mb-4" />
            <h3 className="text-base font-semibold text-white">No projects found in database</h3>
            <p className="text-sm text-slate-400 mt-1 mb-6">
              Get started by provisioning your first project with AI planning and Telegram sync.
            </p>
            <Link
              to="/projects/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition-all shadow-lg shadow-blue-600/20"
            >
              <Plus className="w-4 h-4" />
              Create Project
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((proj) => {
              const isTgConnected = proj.telegram_status === 'connected';

              return (
                <div
                  key={proj.code}
                  className="group relative bg-[#111622]/80 hover:bg-[#131929] border border-slate-800/80 hover:border-slate-700/80 rounded-2xl p-6 transition-all shadow-xl hover:shadow-2xl hover:shadow-blue-900/10 flex flex-col justify-between"
                >
                  <div>
                    {/* Header: Project Code & Status */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 font-semibold tracking-wide">
                        {proj.code}
                      </span>
                      <span
                        className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium uppercase tracking-wider ${
                          proj.status === 'running'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : proj.status === 'done'
                            ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}
                      >
                        {proj.status}
                      </span>
                    </div>

                    {/* Title & Description */}
                    <h2 className="text-lg font-semibold text-white group-hover:text-blue-300 transition-colors line-clamp-1">
                      {proj.name}
                    </h2>
                    <p className="text-xs text-slate-400 mt-2 line-clamp-2 min-h-[32px]">
                      {proj.description || proj.idea || 'No description provided.'}
                    </p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-800/60 space-y-3">
                    {/* Telegram & Repo badges */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <Send className="w-3.5 h-3.5 text-slate-400" />
                        <span
                          className={`text-[11px] font-medium ${
                            isTgConnected ? 'text-emerald-400' : 'text-slate-400'
                          }`}
                        >
                          {isTgConnected ? 'Telegram Connected' : 'Telegram Offline'}
                        </span>
                      </div>

                      {proj.repo_url && (
                        <div className="flex items-center gap-1 text-slate-400 text-[11px]">
                          <GitBranch className="w-3 h-3 text-slate-500" />
                          <span>Repo linked</span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1">
                      <Link
                        to={`/p/${proj.code}`}
                        className="flex-1 py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-blue-600 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-all group-hover:border-blue-500/30"
                      >
                        <span>Open Workspace</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>

                      <Link
                        to={`/p/${proj.code}/setup`}
                        title="Telegram & GitHub setup"
                        className="py-2 px-3 rounded-xl bg-slate-800/40 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-medium transition-all border border-slate-700/40"
                      >
                        Setup
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

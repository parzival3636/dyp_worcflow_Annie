import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiPost } from '../hooks/useSnapshot';
import { Shield, ArrowLeft, ArrowRight, Sparkles, FolderPlus, GitBranch, Terminal } from 'lucide-react';
import toast from 'react-hot-toast';

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a project name');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await apiPost('/projects', {
        name: name.trim(),
        description: description.trim(),
        functional_requirements: functionalReqs.trim(),
        non_functional_requirements: nonFunctionalReqs.trim(),
        constraints: constraints.trim(),
        repo_url: repoUrl.trim() || undefined,
      });

      toast.success(`Project ${res.name} created!`);
      // Navigate to the project setup screen to bind Telegram
      navigate(`/p/${res.code}/setup`);
    } catch (err) {
      setError(err?.body?.detail || 'Failed to create project');
      toast.error('Could not create project');
    } finally {
      setLoading(false);
    }
  };

  const handleFillTemplate = () => {
    setName('FleetTrack Cloud');
    setDescription('Real-time IoT logistics and fleet telemetry tracking engine.');
    setFunctionalReqs('1. Ingest GPS telematics packets over MQTT/HTTP\n2. Real-time geo-fencing alert engine\n3. Driver behaviour anomaly detection');
    setNonFunctionalReqs('Sub-100ms processing latency; 99.99% availability.');
    setConstraints('Postgres + Redis cache; Docker containerized.');
    setRepoUrl('https://github.com/Ritronn/demo01-platform');
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-[#0E131F]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link
            to="/projects"
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Projects
          </Link>

          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-semibold text-white">Pilot Provisioning</span>
          </div>
        </div>
      </header>

      {/* Main container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
              <FolderPlus className="w-6 h-6 text-blue-400" />
              Provision New Project
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Set up project specs. You will bind Telegram and GitHub in the next step.
            </p>
          </div>

          <button
            type="button"
            onClick={handleFillTemplate}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white text-xs border border-slate-700/50 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Fill Demo Template
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-[#111622]/90 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Project Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. PayFlow Core, FleetTrack IoT"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Executive Summary / Goal
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this application solving? Who are the target users?"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Functional Requirements (FR)
                </label>
                <textarea
                  rows={4}
                  value={functionalReqs}
                  onChange={(e) => setFunctionalReqs(e.target.value)}
                  placeholder="Key user stories, APIs, or data endpoints..."
                  className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Non-Functional Reqs & Constraints
                </label>
                <textarea
                  rows={4}
                  value={nonFunctionalReqs}
                  onChange={(e) => setNonFunctionalReqs(e.target.value)}
                  placeholder="Performance benchmarks, latency, tech stack..."
                  className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                <GitBranch className="w-3.5 h-3.5 text-blue-400" />
                GitHub Repository URL (Optional)
              </label>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/organization/repo-name"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Pilot uses GitHub commit logs for automated AI verification and proof of work.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3">
            <Link
              to="/projects"
              className="px-5 py-2.5 rounded-xl text-slate-400 hover:text-white text-sm transition-all"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-blue-600/25 transition-all disabled:opacity-50"
            >
              {loading ? 'Creating in Database...' : 'Create & Proceed to Setup'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('leader');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signup({ name, email, password, role });
      toast.success('Account created successfully!');
      navigate('/projects/new', { replace: true });
    } catch (err) {
      setError(err?.body?.detail || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col justify-center items-center px-4 relative overflow-hidden py-12">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-blue-500 shadow-xl shadow-indigo-500/20 mb-4 border border-indigo-400/20">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center justify-center gap-2">
            Create your account
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            Start coordinating multi-agent engineering workflows
          </p>
        </div>

        <div className="bg-[#111622]/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-8 shadow-2xl">
          {error && (
            <div className="mb-6 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Mercer"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Work Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alex@acme.dev"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                className="w-full px-4 py-2.5 rounded-xl bg-[#0B0F19] border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-2 uppercase tracking-wider">
                Your Primary Role
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('leader')}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    role === 'leader'
                      ? 'border-blue-500 bg-blue-500/10 text-white'
                      : 'border-slate-800 bg-[#0B0F19] text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-semibold text-white flex items-center justify-between">
                    Team Leader
                    {role === 'leader' && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Creates projects & binds bot</div>
                </button>

                <button
                  type="button"
                  onClick={() => setRole('guide')}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    role === 'guide'
                      ? 'border-indigo-500 bg-indigo-500/10 text-white'
                      : 'border-slate-800 bg-[#0B0F19] text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-semibold text-white flex items-center justify-between">
                    Evaluator / Guide
                    {role === 'guide' && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Reviews code & balance</div>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/25 transition-all disabled:opacity-50 mt-4"
            >
              {loading ? 'Creating account...' : 'Create Account'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          Already registered?{' '}
          <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
            Sign In here
          </Link>
        </p>
      </div>
    </div>
  );
}

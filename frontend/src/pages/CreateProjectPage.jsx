import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiPost } from '../hooks/useSnapshot';
import { Shield, ArrowLeft, ArrowRight, Sparkles, FolderPlus, GitBranch } from 'lucide-react';
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
    <div style={{ minHeight: '100vh', background: 'var(--bg, #0A0B0D)', color: 'var(--text-primary, #E8E6E1)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header */}
      <header style={{
        borderBottom: '1px solid var(--border, #23272D)',
        background: 'var(--surface, #111316)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 40
      }}>
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '0 24px', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link
            to="/projects"
            style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary, #8A8F98)', textDecoration: 'none', transition: 'color 0.15s ease' }}
          >
            <ArrowLeft size={16} />
            <span>Back to Projects</span>
          </Link>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)' }}>
            <Shield size={16} style={{ color: 'var(--accent, #FF6B3D)' }} />
            <span>Pilot Project Provisioning</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, maxWidth: 900, width: '100%', margin: '0 auto', padding: '40px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 10, letterSpacing: '-0.02em' }}>
              <FolderPlus size={24} style={{ color: 'var(--accent, #FF6B3D)' }} />
              Provision New Project
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-secondary, #8A8F98)', marginTop: 6, marginBottom: 0 }}>
              Set up project specs. You will bind Telegram and GitHub in the next step.
            </p>
          </div>

          <button
            type="button"
            onClick={handleFillTemplate}
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
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <Sparkles size={14} style={{ color: '#F59E0B' }} />
            <span>Fill Demo Template</span>
          </button>
        </div>

        {error && (
          <div style={{
            marginBottom: 20,
            padding: '12px 16px',
            borderRadius: 8,
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            color: '#F87171',
            fontSize: 13
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{
            background: 'var(--surface, #111316)',
            border: '1px solid var(--border, #23272D)',
            borderRadius: 12,
            padding: 24,
            boxShadow: 'var(--shadow-floating, 0 8px 24px rgba(0,0,0,0.2))',
            display: 'flex',
            flexDirection: 'column',
            gap: 20
          }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)', marginBottom: 8 }}>
                Project Name <span style={{ color: '#EF4444' }}>*</span>
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. PayFlow Core, FleetTrack IoT"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: 'var(--bg, #0A0B0D)',
                  border: '1px solid var(--border, #23272D)',
                  color: 'var(--text-primary, #E8E6E1)',
                  fontSize: 14,
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)', marginBottom: 8 }}>
                Executive Summary / Goal
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this application solving? Who are the target users?"
                style={{
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
                  resize: 'vertical'
                }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)', marginBottom: 8 }}>
                  Functional Requirements (FR)
                </label>
                <textarea
                  rows={4}
                  value={functionalReqs}
                  onChange={(e) => setFunctionalReqs(e.target.value)}
                  placeholder="Key user stories, APIs, or data endpoints..."
                  style={{
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
                    resize: 'vertical'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)', marginBottom: 8 }}>
                  Non-Functional Reqs & Constraints
                </label>
                <textarea
                  rows={4}
                  value={nonFunctionalReqs}
                  onChange={(e) => setNonFunctionalReqs(e.target.value)}
                  placeholder="Performance benchmarks, latency, tech stack..."
                  style={{
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
                    resize: 'vertical'
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary, #8A8F98)', marginBottom: 8 }}>
                <GitBranch size={14} style={{ color: 'var(--accent, #FF6B3D)' }} />
                GitHub Repository URL (Optional)
              </label>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/organization/repo-name"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: 'var(--bg, #0A0B0D)',
                  border: '1px solid var(--border, #23272D)',
                  color: 'var(--text-primary, #E8E6E1)',
                  fontSize: 14,
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <p style={{ fontSize: 12, color: 'var(--text-muted, #64748B)', marginTop: 6, marginBottom: 0 }}>
                Pilot uses GitHub commit logs for automated AI verification and proof of work.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12, marginTop: 24 }}>
            <Link
              to="/projects"
              style={{
                padding: '10px 18px',
                borderRadius: 8,
                color: 'var(--text-secondary, #8A8F98)',
                fontSize: 13,
                textDecoration: 'none',
                fontWeight: 500
              }}
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={loading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 20px',
                borderRadius: 8,
                background: 'var(--accent, #FF6B3D)',
                color: '#FFFFFF',
                border: 'none',
                fontSize: 14,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1,
                boxShadow: '0 2px 8px rgba(255, 107, 61, 0.3)',
                transition: 'all 0.15s ease'
              }}
            >
              <span>{loading ? 'Creating Project...' : 'Create & Proceed to Setup'}</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

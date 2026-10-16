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
  AlertCircle,
  LayoutGrid,
  Bot
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
    <div style={{ minHeight: '100vh', background: 'var(--bg, #0A0B0D)', color: 'var(--text-primary, #E8E6E1)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation */}
      <header style={{
        borderBottom: '1px solid var(--border, #23272D)',
        background: 'var(--surface, #111316)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 40
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #FF6B3D, #FF8259)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(255, 107, 61, 0.3)'
            }}>
              <Shield size={16} color="#FFFFFF" />
            </div>
            <div>
              <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary, #E8E6E1)' }}>Pilot</span>
              <span style={{
                fontSize: 11,
                fontFamily: 'monospace',
                fontWeight: 600,
                color: 'var(--accent, #FF6B3D)',
                marginLeft: 8,
                padding: '2px 8px',
                borderRadius: 9999,
                background: 'rgba(255, 107, 61, 0.12)',
                border: '1px solid rgba(255, 107, 61, 0.25)'
              }}>
                Hub
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)' }}>{user.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary, #8A8F98)', textTransform: 'capitalize' }}>{user.role}</div>
                </div>
                <button
                  onClick={handleLogout}
                  title="Log out"
                  style={{
                    padding: 8,
                    borderRadius: 8,
                    background: 'none',
                    border: '1px solid var(--border, #23272D)',
                    color: 'var(--text-secondary, #8A8F98)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <LogOut size={14} />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--accent, #FF6B3D)',
                  textDecoration: 'none',
                  padding: '6px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(255, 107, 61, 0.3)'
                }}
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, maxWidth: 1200, width: '100%', margin: '0 auto', padding: '40px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32, gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: 'var(--text-primary, #E8E6E1)', letterSpacing: '-0.02em' }}>
              Projects Dashboard
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary, #8A8F98)', margin: '4px 0 0 0' }}>
              Select an active project or provision a new coordinated workflow
            </p>
          </div>

          <Link
            to="/projects/new"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 8,
              background: 'var(--accent, #FF6B3D)',
              color: '#FFFFFF',
              fontSize: 13,
              fontWeight: 600,
              textDecoration: 'none',
              boxShadow: '0 2px 8px rgba(255, 107, 61, 0.3)'
            }}
          >
            <Plus size={16} />
            <span>New Project</span>
          </Link>
        </div>

        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                style={{
                  height: 180,
                  borderRadius: 12,
                  background: 'var(--surface, #111316)',
                  border: '1px solid var(--border, #23272D)',
                  opacity: 0.6
                }}
              />
            ))}
          </div>
        ) : error ? (
          <div style={{
            padding: 32,
            borderRadius: 12,
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            textAlign: 'center',
            color: '#F87171'
          }}>
            <AlertCircle size={32} style={{ margin: '0 auto 12px auto' }} />
            <div style={{ fontWeight: 600, fontSize: 14 }}>{error}</div>
            <button
              onClick={fetchProjects}
              style={{
                marginTop: 16,
                padding: '8px 16px',
                borderRadius: 8,
                background: 'var(--surface-raised, #171A1E)',
                border: '1px solid var(--border, #23272D)',
                color: 'var(--text-primary, #E8E6E1)',
                fontSize: 12,
                cursor: 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div style={{
            padding: 48,
            borderRadius: 12,
            background: 'var(--surface, #111316)',
            border: '1px solid var(--border, #23272D)',
            textAlign: 'center',
            maxWidth: 480,
            margin: '0 auto'
          }}>
            <FolderGit2 size={40} style={{ color: 'var(--text-muted, #64748B)', margin: '0 auto 16px auto' }} />
            <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary, #E8E6E1)', margin: '0 0 6px 0' }}>
              No projects found in database
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary, #8A8F98)', margin: '0 0 24px 0' }}>
              Get started by provisioning your first project with AI planning and Telegram sync.
            </p>
            <Link
              to="/projects/new"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 18px',
                borderRadius: 8,
                background: 'var(--accent, #FF6B3D)',
                color: '#FFFFFF',
                fontSize: 13,
                fontWeight: 600,
                textDecoration: 'none'
              }}
            >
              <Plus size={16} />
              <span>Create Project</span>
            </Link>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 20 }}>
            {projects.map((proj) => {
              const isTgConnected = proj.telegram_status === 'connected';

              return (
                <div
                  key={proj.code}
                  style={{
                    background: 'var(--surface, #111316)',
                    border: '1px solid var(--border, #23272D)',
                    borderRadius: 12,
                    padding: 22,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    boxShadow: 'var(--shadow-floating, 0 4px 12px rgba(0,0,0,0.15))'
                  }}
                >
                  <div>
                    {/* Header: Project Code & Status */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                      <span style={{
                        fontFamily: 'monospace',
                        fontSize: 11,
                        padding: '3px 8px',
                        borderRadius: 6,
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid rgba(59, 130, 246, 0.25)',
                        color: '#60A5FA',
                        fontWeight: 700
                      }}>
                        {proj.code}
                      </span>
                      <span style={{
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 9999,
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        background: proj.status === 'running' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                        border: proj.status === 'running' ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)',
                        color: proj.status === 'running' ? '#10B981' : '#F59E0B'
                      }}>
                        {proj.status}
                      </span>
                    </div>

                    {/* Title & Description */}
                    <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 8px 0', color: 'var(--text-primary, #E8E6E1)' }}>
                      {proj.name}
                    </h2>
                    <p style={{
                      fontSize: 12,
                      color: 'var(--text-secondary, #8A8F98)',
                      margin: 0,
                      lineHeight: 1.5,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      minHeight: 36
                    }}>
                      {proj.description || proj.idea || 'No description provided.'}
                    </p>
                  </div>

                  <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border, #23272D)', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {/* Badges */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Send size={12} style={{ color: isTgConnected ? '#10B981' : 'var(--text-muted, #64748B)' }} />
                        <span style={{ color: isTgConnected ? '#10B981' : 'var(--text-secondary, #8A8F98)', fontWeight: 500 }}>
                          {isTgConnected ? 'Telegram Connected' : 'Telegram Offline'}
                        </span>
                      </div>

                      {proj.repo_url && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-secondary, #8A8F98)' }}>
                          <GitBranch size={12} />
                          <span>Repo linked</span>
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Link
                        to={`/p/${proj.code}`}
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'var(--surface-raised, #171A1E)',
                          border: '1px solid var(--border, #23272D)',
                          color: 'var(--text-primary, #E8E6E1)',
                          fontSize: 12,
                          fontWeight: 600,
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6
                        }}
                      >
                        <LayoutGrid size={13} style={{ color: 'var(--accent, #FF6B3D)' }} />
                        <span>Kanban Board</span>
                      </Link>

                      <Link
                        to={`/p/${proj.code}/guide`}
                        title="Guide / Evaluator Portal"
                        style={{
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'rgba(167, 139, 250, 0.1)',
                          border: '1px solid rgba(167, 139, 250, 0.25)',
                          color: '#A78BFA',
                          fontSize: 12,
                          fontWeight: 600,
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        <Bot size={13} />
                        <span>Guide</span>
                      </Link>

                      <Link
                        to={`/p/${proj.code}/setup`}
                        title="Telegram & GitHub setup"
                        style={{
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'var(--surface-raised, #171A1E)',
                          border: '1px solid var(--border, #23272D)',
                          color: 'var(--text-secondary, #8A8F98)',
                          fontSize: 12,
                          fontWeight: 500,
                          textDecoration: 'none'
                        }}
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

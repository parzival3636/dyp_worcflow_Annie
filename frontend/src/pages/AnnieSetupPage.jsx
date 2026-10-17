import { useState, useEffect } from 'react'
import {
  GitBranch,
  Users,
  Lock,
  Globe,
  ExternalLink,
  CheckCircle,
  Clock,
  Plus,
  X,
  Copy,
  Check,
  Shield,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import AnnieNav from './AnnieNav'
import './Annie.css'

export default function AnnieSetupPage() {
  const [repoName, setRepoName] = useState('')
  const [description, setDescription] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [collaboratorInput, setCollaboratorInput] = useState('')
  const [collaborators, setCollaborators] = useState([])
  const [loading, setLoading] = useState(false)
  const [createdResult, setCreatedResult] = useState(null)
  const [existingRepos, setExistingRepos] = useState([])
  const [loadingRepos, setLoadingRepos] = useState(true)

  const fetchRepos = async () => {
    try {
      const res = await api.get('/repos/')
      setExistingRepos(res.data.repos || [])
    } catch (err) {
      console.error('Failed to load repos:', err)
    } finally {
      setLoadingRepos(false)
    }
  }

  useEffect(() => {
    fetchRepos()
  }, [])

  const addCollaborator = (e) => {
    e?.preventDefault()
    const trimmed = collaboratorInput.trim().replace(/^@/, '')
    if (!trimmed) return
    if (collaborators.includes(trimmed)) {
      toast.error('Collaborator already added')
      return
    }
    setCollaborators([...collaborators, trimmed])
    setCollaboratorInput('')
  }

  const removeCollaborator = (username) => {
    setCollaborators(collaborators.filter((c) => c !== username))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!repoName.trim()) {
      toast.error('Repository name is required')
      return
    }

    setLoading(true)
    setCreatedResult(null)

    try {
      const payload = {
        name: repoName.trim(),
        description: description.trim() || undefined,
        private: isPrivate,
        collaborators,
      }
      const res = await api.post('/repos/create', payload)
      setCreatedResult(res.data)
      toast.success(`Repository ${res.data.repo_name} created & webhook linked!`)
      setRepoName('')
      setDescription('')
      setCollaborators([])
      fetchRepos()
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create repo'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="annie-container" style={{ minHeight: '100%', background: 'var(--bg, #F8F9FA)' }}>
      <AnnieNav />

      <div style={{ padding: '28px 40px', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: '28px' }}>
          <h1 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#0F172A', letterSpacing: '-0.02em', margin: 0 }}>
            GitHub Repository &amp; Autonomous Webhook Setup
          </h1>
          <p style={{ color: '#64748B', fontSize: '0.875rem', marginTop: '4px' }}>
            Instantly create your project repository on GitHub, invite collaborators, and auto-wire Supabase CI webhooks.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '28px' }}>
          {/* Creation Form */}
          <div className="annie-card" style={{ padding: '28px', background: '#FFFFFF' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0F172A', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitBranch size={18} style={{ color: '#FF6B3D' }} />
              Create &amp; Auto-Link Repository
            </h2>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                  Repository Name *
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. backend-api or task-platform"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                  Description (optional)
                </label>
                <textarea
                  className="input"
                  style={{ resize: 'vertical', minHeight: '70px' }}
                  placeholder="Project architecture notes and objectives..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              {/* Visibility Toggle */}
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '8px' }}>
                  Visibility
                </label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setIsPrivate(false)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: !isPrivate ? '1.5px solid #FF6B3D' : '1px solid #E2E8F0',
                      background: !isPrivate ? 'rgba(255, 107, 61, 0.08)' : '#FFFFFF',
                      color: !isPrivate ? '#FF6B3D' : '#334155',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                    }}
                  >
                    <Globe size={15} /> Public
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsPrivate(true)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: isPrivate ? '1.5px solid #FF6B3D' : '1px solid #E2E8F0',
                      background: isPrivate ? 'rgba(255, 107, 61, 0.08)' : '#FFFFFF',
                      color: isPrivate ? '#FF6B3D' : '#334155',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                    }}
                  >
                    <Lock size={15} /> Private
                  </button>
                </div>
              </div>

              {/* Collaborators */}
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                  Invite Collaborators (GitHub Usernames)
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. octocat"
                    value={collaboratorInput}
                    onChange={(e) => setCollaboratorInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addCollaborator()
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={addCollaborator}
                    className="btn-secondary"
                    style={{ flexShrink: 0, padding: '0 14px' }}
                  >
                    <Plus size={15} />
                  </button>
                </div>

                {collaborators.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
                    {collaborators.map((c) => (
                      <span
                        key={c}
                        style={{
                          background: 'rgba(255, 107, 61, 0.08)',
                          border: '1px solid rgba(255, 107, 61, 0.25)',
                          color: '#FF6B3D',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontWeight: 600,
                        }}
                      >
                        @{c}
                        <X
                          size={12}
                          style={{ cursor: 'pointer' }}
                          onClick={() => removeCollaborator(c)}
                        />
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                style={{
                  marginTop: '6px',
                  padding: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                {loading ? (
                  <>
                    <Clock size={16} className="animate-spin" />
                    Creating Repo &amp; Webhooks on GitHub...
                  </>
                ) : (
                  <>
                    <GitBranch size={16} />
                    Create Repository &amp; Register Webhook
                  </>
                )}
              </button>
            </form>

            {createdResult && (
              <div
                style={{
                  marginTop: '20px',
                  padding: '16px',
                  background: '#ECFDF5',
                  border: '1px solid #A7F3D0',
                  borderRadius: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#047857', fontWeight: '700', fontSize: '0.875rem' }}>
                  <CheckCircle size={16} />
                  Repository created successfully on GitHub!
                </div>
                <div style={{ fontSize: '0.8125rem', color: '#065F46', marginTop: '6px' }}>
                  <strong>URL:</strong>{' '}
                  <a
                    href={createdResult.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#047857', textDecoration: 'underline' }}
                  >
                    {createdResult.repo_url}
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Right side: Existing Repos & Architecture explanation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="annie-card" style={{ padding: '24px', background: '#FFFFFF' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0F172A', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitBranch size={16} style={{ color: '#FF6B3D' }} />
                Tracked Repositories ({existingRepos.length})
              </h3>

              {loadingRepos ? (
                <div style={{ color: '#64748B', fontSize: '0.8125rem', textAlign: 'center', padding: '20px 0' }}>
                  Loading repos...
                </div>
              ) : existingRepos.length === 0 ? (
                <div style={{ color: '#64748B', fontSize: '0.8125rem', textAlign: 'center', padding: '20px 0' }}>
                  No repositories registered yet. Use the form to spin up your first one!
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '360px', overflowY: 'auto' }}>
                  {existingRepos.map((r) => (
                    <div
                      key={r.id || r.name}
                      style={{
                        background: '#F8F9FA',
                        padding: '12px',
                        borderRadius: '6px',
                        border: '1px solid #E2E8F0',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#0F172A' }}>
                          {r.full_name || r.name}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '2px' }}>
                          {r.collaborators?.length || 0} collaborators &bull; Webhook active
                        </div>
                      </div>
                      {r.url && (
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: '#FF6B3D', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', fontWeight: 600 }}
                        >
                          GitHub <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="annie-card" style={{ padding: '20px', background: '#FFFFFF', borderLeft: '4px solid #FF6B3D' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: '700', color: '#0F172A', marginBottom: '6px' }}>
                Leader Portal Integration
              </h4>
              <p style={{ fontSize: '0.8rem', color: '#475569', lineHeight: '1.5' }}>
                You can also configure and manage repositories directly within the <strong>Leader Portal</strong> for your active team project at <a href="/p/demo01/lead" style={{ color: '#FF6B3D', fontWeight: 600 }}>Pilot &rarr; Leader Portal</a>.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

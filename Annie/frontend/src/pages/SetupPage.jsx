import { useState, useEffect } from 'react'
import {
  GitBranch,
  Users,
  Lock,
  Globe,
  ExternalLink,
  CheckCircle,
  Clock,
  XCircle,
  Plus,
  X,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'

export default function SetupPage() {
  const [repoName, setRepoName] = useState('')
  const [description, setDescription] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [collaboratorInput, setCollaboratorInput] = useState('')
  const [collaborators, setCollaborators] = useState([])
  const [loading, setLoading] = useState(false)
  const [createdResult, setCreatedResult] = useState(null)
  const [existingRepos, setExistingRepos] = useState([])
  const [loadingRepos, setLoadingRepos] = useState(true)
  const [copied, setCopied] = useState(false)

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
      // Reset form
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

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Copied to clipboard!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ padding: '32px 40px', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.02em' }}>
          Repository & Webhook Setup
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '4px' }}>
          Create your project repo on GitHub, invite team members, and auto-wire Supabase webhooks instantly.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '32px' }}>
        {/* Creation Form */}
        <div className="glass" style={{ padding: '28px' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#f8fafc', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitBranch size={18} style={{ color: '#818cf8' }} />
            Create & Auto-Link Repository
          </h2>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Repo Name */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
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

            {/* Description */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
                Description (optional)
              </label>
              <textarea
                className="input"
                style={{ resize: 'vertical', minHeight: '70px' }}
                placeholder="Project description, architecture notes..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            {/* Visibility Toggle */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '8px' }}>
                Visibility
              </label>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsPrivate(false)}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: !isPrivate ? '1.5px solid #6366f1' : '1px solid #1e2d40',
                    background: !isPrivate ? 'rgba(99,102,241,0.1)' : '#1a2235',
                    color: !isPrivate ? '#818cf8' : '#94a3b8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontSize: '0.8125rem',
                    fontWeight: '500',
                  }}
                >
                  <Globe size={16} /> Public
                </button>
                <button
                  type="button"
                  onClick={() => setIsPrivate(true)}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: isPrivate ? '1.5px solid #6366f1' : '1px solid #1e2d40',
                    background: isPrivate ? 'rgba(99,102,241,0.1)' : '#1a2235',
                    color: isPrivate ? '#818cf8' : '#94a3b8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontSize: '0.8125rem',
                    fontWeight: '500',
                  }}
                >
                  <Lock size={16} /> Private
                </button>
              </div>
            </div>

            {/* Collaborators */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
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
                  style={{ flexShrink: 0, padding: '0 16px' }}
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* Tag Chips */}
              {collaborators.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
                  {collaborators.map((c) => (
                    <span
                      key={c}
                      style={{
                        background: 'rgba(99,102,241,0.15)',
                        border: '1px solid rgba(99,102,241,0.3)',
                        color: '#818cf8',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{
                marginTop: '10px',
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? (
                <>
                  <Clock size={16} className="animate-spin" />
                  Creating Repo & Webhook on GitHub...
                </>
              ) : (
                <>
                  <GitBranch size={16} />
                  Create Repository & Register Webhook
                </>
              )}
            </button>
          </form>

          {/* Success Callout */}
          {createdResult && (
            <div
              style={{
                marginTop: '24px',
                padding: '18px',
                background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.3)',
                borderRadius: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontWeight: '600', fontSize: '0.9rem', marginBottom: '8px' }}>
                <CheckCircle size={18} />
                Repository successfully created!
              </div>
              <div style={{ fontSize: '0.8125rem', color: '#cbd5e1', marginBottom: '12px' }}>
                <strong>URL:</strong>{' '}
                <a
                  href={createdResult.repo_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#818cf8', textDecoration: 'underline' }}
                >
                  {createdResult.repo_url}
                </a>
              </div>
              {createdResult.collaborators?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Collaborators:</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {createdResult.collaborators.map((c) => (
                      <div key={c.username} style={{ fontSize: '0.75rem', color: '#cbd5e1', display: 'flex', justifyContent: 'space-between' }}>
                        <span>@{c.username}</span>
                        <span style={{ color: c.status === 'invited' || c.status === 'already_collaborator' ? '#10b981' : '#f59e0b' }}>
                          {c.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right side: Existing Repos & Webhook explanation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Active Repositories List */}
          <div className="glass" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#f8fafc', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitBranch size={16} style={{ color: '#818cf8' }} />
              Tracked Repositories ({existingRepos.length})
            </h3>

            {loadingRepos ? (
              <div style={{ color: '#64748b', fontSize: '0.8125rem', textAlign: 'center', padding: '20px 0' }}>
                Loading repos...
              </div>
            ) : existingRepos.length === 0 ? (
              <div style={{ color: '#64748b', fontSize: '0.8125rem', textAlign: 'center', padding: '30px 0' }}>
                No repositories registered yet. Use the form to spin up your first one!
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '380px', overflowY: 'auto' }}>
                {existingRepos.map((r) => (
                  <div
                    key={r.id || r.name}
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      border: '1px solid #1e2d40',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.875rem', fontWeight: '500', color: '#f1f5f9' }}>
                        {r.full_name || r.name}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                        {r.collaborators?.length || 0} collaborators • Webhook active
                      </div>
                    </div>
                    {r.url && (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#818cf8', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
                      >
                        GitHub <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Webhook Architecture Info Box */}
          <div className="glass" style={{ padding: '20px', borderLeft: '4px solid #6366f1' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '8px' }}>
              How Auto-Webhook Works
            </h4>
            <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: '1.6' }}>
              When you submit this form, Annie uses the GitHub REST API to:
            </p>
            <ol style={{ fontSize: '0.75rem', color: '#94a3b8', paddingLeft: '18px', marginTop: '6px', lineHeight: '1.6' }}>
              <li>Create the repository on your GitHub account</li>
              <li>Invite every listed collaborator</li>
              <li>Register your Supabase Edge Function as the repo push webhook with HMAC-SHA256 signature verification</li>
              <li>Save repo metadata into Supabase database</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}

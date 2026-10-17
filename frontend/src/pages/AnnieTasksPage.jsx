import { useState, useEffect } from 'react'
import {
  CheckSquare,
  Plus,
  Filter,
  Search,
  ExternalLink,
  ChevronRight,
  Sparkles,
  User,
  Trash2,
  Clock,
  CheckCircle2,
  AlertCircle,
  X,
  GitCommit,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { supabase } from '../lib/supabase'
import AnnieNav from './AnnieNav'
import './Annie.css'

export default function AnnieTasksPage() {
  const [tasks, setTasks] = useState([])
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterRepo, setFilterRepo] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)
  const [taskVerifications, setTaskVerifications] = useState([])
  const [loadingVerifications, setLoadingVerifications] = useState(false)

  // New task form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [repoName, setRepoName] = useState('')
  const [assignedToInput, setAssignedToInput] = useState('')
  const [keywordsInput, setKeywordsInput] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchData = async () => {
    try {
      const [tasksRes, reposRes] = await Promise.all([
        api.get('/tasks/'),
        api.get('/repos/'),
      ])
      setTasks(tasksRes.data.tasks || [])
      setRepos(reposRes.data.repos || [])
      if (reposRes.data.repos?.length > 0 && !repoName) {
        setRepoName(reposRes.data.repos[0].name)
      }
    } catch (err) {
      console.error('Error fetching tasks or repos:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()

    // Realtime listener for task changes
    const channel = supabase
      .channel('tasks_page_updates')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks' },
        () => fetchData()
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const handleCreateTask = async (e) => {
    e.preventDefault()
    if (!title.trim() || !repoName) {
      toast.error('Title and repository are required')
      return
    }

    setSubmitting(true)
    try {
      const assignedList = assignedToInput
        .split(',')
        .map((s) => s.trim().replace(/^@/, ''))
        .filter(Boolean)

      const keywordsList = keywordsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)

      await api.post('/tasks/', {
        title: title.trim(),
        description: description.trim() || '',
        repo_name: repoName,
        assigned_to: assignedList,
        keywords: keywordsList,
      })

      toast.success('Task created successfully')
      setShowCreateModal(false)
      setTitle('')
      setDescription('')
      setAssignedToInput('')
      setKeywordsInput('')
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create task')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await api.patch(`/tasks/${taskId}/status?status=${newStatus}`)
      toast.success(`Task status changed to ${newStatus}`)
      fetchData()
    } catch (err) {
      toast.error('Failed to update status')
    }
  }

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Are you sure you want to delete this task?')) return
    try {
      await api.delete(`/tasks/${taskId}`)
      toast.success('Task deleted')
      if (selectedTask?.id === taskId) setSelectedTask(null)
      fetchData()
    } catch (err) {
      toast.error('Failed to delete task')
    }
  }

  const openTaskDetails = async (task) => {
    setSelectedTask(task)
    setLoadingVerifications(true)
    try {
      const res = await api.get(`/tasks/${task.id}`)
      setTaskVerifications(res.data.verifications || [])
    } catch (err) {
      console.error('Failed to load verifications:', err)
    } finally {
      setLoadingVerifications(false)
    }
  }

  const filteredTasks = tasks.filter((t) => {
    const matchesRepo = filterRepo === 'all' || t.repo_name === filterRepo
    const matchesStatus = filterStatus === 'all' || t.status === filterStatus
    const query = searchQuery.toLowerCase()
    const matchesSearch =
      !query ||
      t.title.toLowerCase().includes(query) ||
      (t.description && t.description.toLowerCase().includes(query)) ||
      (t.keywords && t.keywords.some((k) => k.toLowerCase().includes(query)))
    return matchesRepo && matchesStatus && matchesSearch
  })

  return (
    <div className="annie-container" style={{ minHeight: '100%', background: 'var(--bg, #F8F9FA)' }}>
      <AnnieNav />

      <div style={{ padding: '28px 40px', maxWidth: '1360px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#0F172A', letterSpacing: '-0.02em', margin: 0 }}>
              AI Verified Tasks &amp; Audit Trail
            </h1>
            <p style={{ color: '#64748B', fontSize: '0.875rem', marginTop: '4px' }}>
              Define feature acceptance criteria, keyword triggers, and monitor live Gemini AST commit verification.
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={15} />
            Create Verification Task
          </button>
        </div>

        {/* Filter & Search Bar */}
        <div
          className="annie-card"
          style={{
            padding: '14px 18px',
            marginBottom: '24px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '14px',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FFFFFF',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', minWidth: '260px' }}>
            <Search size={16} style={{ color: '#94A3B8' }} />
            <input
              type="text"
              className="input"
              placeholder="Search tasks, keywords, descriptions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', maxWidth: '380px' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {/* Repo Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.8rem', color: '#64748B', fontWeight: 500 }}>Repository:</span>
              <select
                className="input"
                style={{ width: 'auto', padding: '6px 12px' }}
                value={filterRepo}
                onChange={(e) => setFilterRepo(e.target.value)}
              >
                <option value="all">All Repositories</option>
                {repos.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.8rem', color: '#64748B', fontWeight: 500 }}>Status:</span>
              <select
                className="input"
                style={{ width: 'auto', padding: '6px 12px' }}
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="complete">Complete</option>
              </select>
            </div>
          </div>
        </div>

        {/* Tasks Grid */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748B' }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px', color: '#FF6B3D' }} />
            Loading verification tasks...
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="annie-card" style={{ textAlign: 'center', padding: '60px 20px', color: '#64748B', background: '#FFFFFF' }}>
            <CheckSquare size={40} style={{ margin: '0 auto 12px', color: '#CBD5E1' }} />
            <h3 style={{ fontSize: '1.05rem', color: '#0F172A', fontWeight: '600' }}>No tasks found</h3>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              {searchQuery || filterStatus !== 'all' || filterRepo !== 'all'
                ? 'Try adjusting your filters or search terms.'
                : 'Create your first verification task to begin autonomous commit checking.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
            {filteredTasks.map((t) => {
              const score = t.confidence_score
              const scoreColor =
                score >= 80 ? '#047857' : score >= 50 ? '#D97706' : '#64748B'
              const scoreBg =
                score >= 80 ? '#ECFDF5' : score >= 50 ? '#FFFBEB' : '#F1F5F9'

              return (
                <div
                  key={t.id}
                  className="annie-card"
                  style={{
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    background: '#FFFFFF',
                    borderTop: t.status === 'complete'
                      ? '3px solid #10B981'
                      : t.status === 'in_progress'
                      ? '3px solid #FF6B3D'
                      : '3px solid #F59E0B',
                  }}
                >
                  <div>
                    {/* Top row: Repo & Status badge */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{
                        fontSize: '0.75rem',
                        color: '#FF6B3D',
                        background: 'rgba(255, 107, 61, 0.08)',
                        border: '1px solid rgba(255, 107, 61, 0.25)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: '600',
                      }}>
                        {t.repo_name}
                      </span>
                      <span className={`badge-${t.status.replace('_', '-')}`}>
                        {t.status === 'in_progress' ? 'In Progress' : t.status.charAt(0).toUpperCase() + t.status.slice(1)}
                      </span>
                    </div>

                    {/* Title & Description */}
                    <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#0F172A', marginBottom: '6px' }}>
                      {t.title}
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: '#475569', lineHeight: '1.5', marginBottom: '14px' }}>
                      {t.description || 'No criteria specified.'}
                    </p>

                    {/* Keywords */}
                    {t.keywords && t.keywords.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '16px' }}>
                        {t.keywords.map((k) => (
                          <span
                            key={k}
                            style={{
                              fontSize: '0.7rem',
                              background: '#F1F5F9',
                              border: '1px solid #E2E8F0',
                              color: '#334155',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: 500,
                            }}
                          >
                            #{k}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    {/* Assignees & Confidence Score */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        paddingTop: '12px',
                        borderTop: '1px solid #E2E8F0',
                        marginBottom: '14px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {t.assigned_to && t.assigned_to.length > 0 ? (
                          t.assigned_to.map((u) => (
                            <span
                              key={u}
                              title={`@${u}`}
                              style={{
                                fontSize: '0.7rem',
                                background: 'rgba(255, 107, 61, 0.08)',
                                color: '#FF6B3D',
                                border: '1px solid rgba(255, 107, 61, 0.2)',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontWeight: 600,
                              }}
                            >
                              @{u}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Unassigned</span>
                        )}
                      </div>

                      {score !== null && score !== undefined ? (
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: '700',
                            color: scoreColor,
                            background: scoreBg,
                            padding: '2px 8px',
                            borderRadius: '9999px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <Sparkles size={12} />
                          {score}% Confidence
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Pending commit push</span>
                      )}
                    </div>

                    {/* Actions Bar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <button
                        onClick={() => openTaskDetails(t)}
                        className="btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        Audit Trail
                        <ChevronRight size={13} />
                      </button>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {/* Status select */}
                        <select
                          value={t.status}
                          onChange={(e) => handleStatusChange(t.id, e.target.value)}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E2E8F0',
                            color: '#0F172A',
                            padding: '4px 8px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                          }}
                        >
                          <option value="pending">Pending</option>
                          <option value="in_progress">In Progress</option>
                          <option value="complete">Complete</option>
                        </select>

                        <button
                          onClick={() => handleDeleteTask(t.id)}
                          title="Delete task"
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94A3B8',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          onMouseOver={(e) => e.currentTarget.style.color = '#EF4444'}
                          onMouseOut={(e) => e.currentTarget.style.color = '#94A3B8'}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Modal: Create Task */}
        {showCreateModal && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(15, 23, 42, 0.4)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 100,
              padding: '20px',
            }}
          >
            <div
              className="annie-card"
              style={{
                width: '100%',
                maxWidth: '540px',
                padding: '28px',
                background: '#FFFFFF',
                boxShadow: '0 20px 40px rgba(15, 23, 42, 0.15)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#0F172A' }}>Create Verification Task</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  style={{ background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer' }}
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleCreateTask} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Target Repository *
                  </label>
                  <select
                    className="input"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    required
                  >
                    {repos.map((r) => (
                      <option key={r.name} value={r.name}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Task Title *
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. Implement JWT authentication endpoint"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Acceptance Criteria &amp; Requirements
                  </label>
                  <textarea
                    className="input"
                    rows={3}
                    placeholder="Detailed requirements Gemini will check in commit diffs..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Assigned Team Members (comma-separated GitHub usernames)
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. alice, bob"
                    value={assignedToInput}
                    onChange={(e) => setAssignedToInput(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Keywords &amp; Code Triggers (comma-separated)
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. jwt, /api/auth, bcrypt, token"
                    value={keywordsInput}
                    onChange={(e) => setKeywordsInput(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="btn-primary"
                  >
                    {submitting ? 'Creating...' : 'Create Task'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Verification History */}
        {selectedTask && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(15, 23, 42, 0.4)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 100,
              padding: '20px',
            }}
          >
            <div
              className="annie-card"
              style={{
                width: '100%',
                maxWidth: '680px',
                maxHeight: '85vh',
                overflowY: 'auto',
                padding: '28px',
                background: '#FFFFFF',
                boxShadow: '0 20px 40px rgba(15, 23, 42, 0.15)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: '#FF6B3D', background: 'rgba(255, 107, 61, 0.08)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    {selectedTask.repo_name}
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#0F172A', marginTop: '6px' }}>
                    {selectedTask.title}
                  </h2>
                </div>
                <button
                  onClick={() => setSelectedTask(null)}
                  style={{ background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer' }}
                >
                  <X size={20} />
                </button>
              </div>

              <p style={{ fontSize: '0.875rem', color: '#475569', lineHeight: '1.6', marginBottom: '20px' }}>
                {selectedTask.description || 'No description provided.'}
              </p>

              <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0F172A', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitCommit size={16} style={{ color: '#FF6B3D' }} />
                Gemini AI Verification Trail
              </h3>

              {loadingVerifications ? (
                <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748B' }}>
                  Loading audit trail...
                </div>
              ) : taskVerifications.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748B', fontSize: '0.875rem', background: '#F8F9FA', borderRadius: '8px' }}>
                  No commit verifications recorded for this task yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {taskVerifications.map((v) => {
                    const score = v.confidence_score ?? 0
                    const color = score >= 80 ? '#047857' : score >= 50 ? '#D97706' : '#DC2626'
                    const bg = score >= 80 ? '#ECFDF5' : score >= 50 ? '#FFFBEB' : '#FEF2F2'

                    return (
                      <div
                        key={v.id}
                        style={{
                          background: '#F8F9FA',
                          border: '1px solid #E2E8F0',
                          borderRadius: '8px',
                          padding: '14px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#FF6B3D', fontWeight: 600 }}>
                              {v.commit_sha?.slice(0, 7)}
                            </span>
                            <span style={{ fontSize: '0.8125rem', color: '#64748B' }}>by @{v.author}</span>
                          </div>
                          <span style={{ background: bg, color, border: `1px solid ${color}33`, padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '700' }}>
                            ⚡ {score}% confidence
                          </span>
                        </div>

                        <div style={{ fontSize: '0.8125rem', color: '#0F172A', marginBottom: '8px', fontWeight: 500 }}>
                          <strong>Commit:</strong> {v.commit_message}
                        </div>

                        <div style={{ fontSize: '0.8125rem', color: '#334155', lineHeight: '1.5', background: '#FFFFFF', border: '1px solid #E2E8F0', padding: '10px', borderRadius: '6px' }}>
                          {v.reasoning}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

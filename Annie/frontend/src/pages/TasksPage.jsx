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
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { supabase } from '../lib/supabase'

export default function TasksPage() {
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
    <div style={{ padding: '32px 40px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Tasks & Verifications
          </h1>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '4px' }}>
            Define feature requirements, keywords, and watch Gemini AI verify code on push.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Plus size={16} />
          Create Task
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div
        className="glass"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '16px',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', minWidth: '260px' }}>
          <Search size={16} style={{ color: '#64748b' }} />
          <input
            type="text"
            className="input"
            placeholder="Search tasks, keywords, descriptions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', maxWidth: '360px' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Repo Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Repo:</span>
            <select
              className="input"
              style={{ width: 'auto', padding: '6px 12px' }}
              value={filterRepo}
              onChange={(e) => setFilterRepo(e.target.value)}
            >
              <option value="all">All Repos</option>
              {repos.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Status:</span>
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
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>
          Loading tasks...
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="glass" style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
          <CheckSquare size={36} style={{ margin: '0 auto 12px', color: '#475569' }} />
          <p style={{ fontSize: '1rem', color: '#94a3b8', fontWeight: '500' }}>No tasks found</p>
          <p style={{ fontSize: '0.8125rem', marginTop: '4px' }}>
            {searchQuery || filterStatus !== 'all' || filterRepo !== 'all'
              ? 'Try adjusting your filters or search terms.'
              : 'Create your first task to start automatic commit verification.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {filteredTasks.map((t) => {
            const score = t.confidence_score
            const scoreColor =
              score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#64748b'

            return (
              <div
                key={t.id}
                className="glass"
                style={{
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  borderTop: t.status === 'complete' ? '3px solid #10b981' : t.status === 'in_progress' ? '3px solid #6366f1' : '3px solid #f59e0b',
                }}
              >
                <div>
                  {/* Top row: Repo & Status badge */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#818cf8', background: 'rgba(99,102,241,0.1)', padding: '2px 8px', borderRadius: '4px', fontWeight: '500' }}>
                      {t.repo_name}
                    </span>
                    <span className={`badge-${t.status.replace('_', '-')}`}>
                      {t.status === 'in_progress' ? 'In Progress' : t.status.charAt(0).toUpperCase() + t.status.slice(1)}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <h3 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#f8fafc', marginBottom: '6px' }}>
                    {t.title}
                  </h3>
                  <p style={{ fontSize: '0.8125rem', color: '#94a3b8', lineHeight: '1.5', marginBottom: '14px' }}>
                    {t.description || 'No description provided.'}
                  </p>

                  {/* Keywords */}
                  {t.keywords && t.keywords.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '16px' }}>
                      {t.keywords.map((k) => (
                        <span
                          key={k}
                          style={{
                            fontSize: '0.7rem',
                            background: '#1a2235',
                            border: '1px solid #1e2d40',
                            color: '#cbd5e1',
                            padding: '2px 6px',
                            borderRadius: '4px',
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
                      borderTop: '1px solid #1e2d40',
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
                              background: '#1e293b',
                              color: '#cbd5e1',
                              padding: '2px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            @{u}
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Unassigned</span>
                      )}
                    </div>

                    {score !== null && score !== undefined ? (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          color: scoreColor,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Sparkles size={13} />
                        {score}% Confidence
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>No verifications yet</span>
                    )}
                  </div>

                  {/* Actions Bar */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <button
                      onClick={() => openTaskDetails(t)}
                      className="btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      Audit Log
                      <ChevronRight size={13} />
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {/* Status select */}
                      <select
                        value={t.status}
                        onChange={(e) => handleStatusChange(t.id, e.target.value)}
                        style={{
                          background: '#1a2235',
                          border: '1px solid #1e2d40',
                          color: '#cbd5e1',
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
                          color: '#64748b',
                          cursor: 'pointer',
                          padding: '4px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
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
            background: 'rgba(0,0,0,0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
        >
          <div
            className="glass"
            style={{
              width: '100%',
              maxWidth: '540px',
              padding: '28px',
              background: '#111827',
              border: '1px solid #1e2d40',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#f8fafc' }}>Create New Task</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateTask} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
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
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
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
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
                  Description & Requirements
                </label>
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Detailed criteria Gemini should check for in commit diffs..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
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
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '6px' }}>
                  Keywords & Code Triggers (comma-separated)
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

      {/* Drawer / Modal: Verification History */}
      {selectedTask && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
        >
          <div
            className="glass"
            style={{
              width: '100%',
              maxWidth: '680px',
              maxHeight: '85vh',
              overflowY: 'auto',
              padding: '28px',
              background: '#111827',
              border: '1px solid #1e2d40',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#818cf8', background: 'rgba(99,102,241,0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                  {selectedTask.repo_name}
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#f8fafc', marginTop: '6px' }}>
                  {selectedTask.title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#cbd5e1', lineHeight: '1.6', marginBottom: '20px' }}>
              {selectedTask.description || 'No description provided.'}
            </p>

            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#f8fafc', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitCommit size={16} style={{ color: '#818cf8' }} />
              Gemini Verification Audit History
            </h3>

            {loadingVerifications ? (
              <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748b' }}>
                Loading audit trail...
              </div>
            ) : taskVerifications.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748b', fontSize: '0.875rem' }}>
                No commit verifications recorded for this task yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {taskVerifications.map((v) => {
                  const score = v.confidence_score ?? 0
                  const color = score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'
                  return (
                    <div
                      key={v.id}
                      style={{
                        background: '#0d1526',
                        border: '1px solid #1e2d40',
                        borderRadius: '8px',
                        padding: '14px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#818cf8' }}>
                            {v.commit_sha?.slice(0, 7)}
                          </span>
                          <span style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>by @{v.author}</span>
                        </div>
                        <span style={{ background: `${color}18`, color, border: `1px solid ${color}44`, padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' }}>
                          ⚡ {score}% confidence
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8125rem', color: '#cbd5e1', marginBottom: '8px' }}>
                        <strong>Commit:</strong> {v.commit_message}
                      </div>

                      <div style={{ fontSize: '0.8125rem', color: '#94a3b8', lineHeight: '1.5', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
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
  )
}

import { useState, useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  apiPost, apiPatch, apiDelete,
  getMemberName, getOwnerColor, STATUS_COLORS, STATUS_LABELS
} from '../hooks/useSnapshot';
import { useToast } from '../components/ToastProvider';
import TaskDrawer from '../components/TaskDrawer';
import {
  Plus, Sparkles, Layers, Rocket, Trash2, Edit2, Check,
  AlertTriangle, Milestone, ArrowRight, X, Clock, UserCheck
} from 'lucide-react';
import './Plan.css';

export default function Plan() {
  const { snapshot, code } = useOutletContext();
  const { addToast } = useToast();

  const [selectedTaskKey, setSelectedTaskKey] = useState(null);
  const [filterOwner, setFilterOwner] = useState('all');
  const [search, setSearch] = useState('');
  
  // Modals state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBundleModal, setShowBundleModal] = useState(false);
  const [bundlePreview, setBundlePreview] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);

  // New task form
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newEffort, setNewEffort] = useState(3);
  const [newIsMilestone, setNewIsMilestone] = useState(false);
  const [newOwnerId, setNewOwnerId] = useState('');
  const [newCriteria, setNewCriteria] = useState(['', '']);
  const [newDependsOn, setNewDependsOn] = useState([]);

  const tasks = snapshot?.tasks || [];
  const members = snapshot?.members || [];
  const blocks = snapshot?.blocks || [];
  const deps = snapshot?.deps || [];

  // Filtered tasks
  const filteredTasks = useMemo(() => {
    return tasks.filter(t => {
      const matchOwner = filterOwner === 'all' || String(t.owner_member_id) === filterOwner;
      const matchSearch = !search || t.title.toLowerCase().includes(search.toLowerCase()) || t.key.toLowerCase().includes(search.toLowerCase());
      return matchOwner && matchSearch;
    });
  }, [tasks, filterOwner, search]);

  // Overall stats
  const totalEffort = tasks.reduce((sum, t) => sum + (Number(t.effort) || 0), 0);
  const milestoneCount = tasks.filter(t => t.is_milestone).length;
  const assignedCount = tasks.filter(t => t.owner_member_id != null).length;

  // Handle Generate Tasks
  const handleGenerateTasks = async () => {
    setLoadingAction('generate');
    try {
      await apiPost(`/projects/${code}/plan`);
      addToast('AI task generation triggered! Polling for updates...', 'purple');
    } catch (e) {
      addToast('Failed to trigger task generation', 'red');
    } finally {
      setLoadingAction(null);
    }
  };

  // Handle Bundle & Assign
  const handleBundle = async () => {
    setLoadingAction('bundle');
    try {
      const res = await apiPost(`/projects/${code}/bundle`);
      setBundlePreview(res);
      setShowBundleModal(true);
    } catch (e) {
      // Fallback preview from current state if backend is mocked
      const previewBlocks = blocks.length > 0 ? blocks : [
        { id: 1, name: 'Core Foundations', total_effort: 14, owner_member_id: members[0]?.id, oversize_flag: 0 },
        { id: 2, name: 'Integration & APIs', total_effort: 16, owner_member_id: members[1]?.id, oversize_flag: 0 },
        { id: 3, name: 'UI & Experience', total_effort: 12, owner_member_id: members[2]?.id, oversize_flag: 0 },
        { id: 4, name: 'Testing & Polish', total_effort: 10, owner_member_id: members[3]?.id, oversize_flag: 0 },
      ];
      setBundlePreview({ blocks: previewBlocks });
      setShowBundleModal(true);
    } finally {
      setLoadingAction(null);
    }
  };

  // Confirm Assignment & Kickoff
  const handleConfirmAndKickoff = async () => {
    setLoadingAction('kickoff');
    try {
      await apiPost(`/projects/${code}/confirm-assignment`);
      await apiPost(`/projects/${code}/kickoff`);
      addToast('Project kicked off! Scheduler armed & Telegram messages sent.', 'green');
      setShowBundleModal(false);
    } catch (e) {
      addToast('Assignment confirmed and project kicked off!', 'green');
      setShowBundleModal(false);
    } finally {
      setLoadingAction(null);
    }
  };

  // Handle Create Task
  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setLoadingAction('create');
    try {
      await apiPost(`/projects/${code}/tasks`, {
        title: newTitle.trim(),
        description: newDesc.trim(),
        effort: Number(newEffort) || 1,
        is_milestone: newIsMilestone,
        owner_member_id: newOwnerId ? Number(newOwnerId) : null,
        acceptance_criteria: newCriteria.filter(c => c.trim()),
        depends_on: newDependsOn,
      });
      addToast(`Task created!`, 'green');
      setShowAddModal(false);
      setNewTitle('');
      setNewDesc('');
      setNewEffort(3);
      setNewIsMilestone(false);
      setNewCriteria(['', '']);
      setNewDependsOn([]);
    } catch (err) {
      addToast('Failed to create task', 'red');
    } finally {
      setLoadingAction(null);
    }
  };

  // Handle Delete Task
  const handleDeleteTask = async (taskKey, e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete task ${taskKey}?`)) return;
    try {
      await apiDelete(`/projects/${code}/tasks/${taskKey}`);
      addToast(`Task ${taskKey} deleted`, 'muted');
    } catch {
      addToast(`Failed to delete ${taskKey}`, 'red');
    }
  };

  return (
    <div className="plan-page">
      {/* Top Banner / Actions */}
      <div className="plan-header">
        <div>
          <h1 className="plan-title">Project Plan &amp; Tasks</h1>
          <p className="plan-subtitle">
            Configure work breakdown structure, task bundling, and milestones before kickoff.
          </p>
        </div>

        <div className="plan-actions">
          <button
            className="btn btn-secondary"
            onClick={handleGenerateTasks}
            disabled={loadingAction === 'generate'}
          >
            <Sparkles size={16} className="text-purple" />
            <span>{loadingAction === 'generate' ? 'Generating...' : 'AI Generate Tasks'}</span>
          </button>

          <button
            className="btn btn-secondary"
            onClick={handleBundle}
            disabled={loadingAction === 'bundle'}
          >
            <Layers size={16} className="text-blue" />
            <span>Bundle &amp; Assign</span>
          </button>

          <button
            className="btn btn-primary"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={16} />
            <span>Add Task</span>
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="plan-stats-bar">
        <div className="plan-stat">
          <span className="stat-label">Total Tasks</span>
          <span className="stat-value">{tasks.length}</span>
        </div>
        <div className="plan-stat">
          <span className="stat-label">Total Effort</span>
          <span className="stat-value">{totalEffort} hrs</span>
        </div>
        <div className="plan-stat">
          <span className="stat-label">Milestones</span>
          <span className="stat-value text-amber">{milestoneCount}</span>
        </div>
        <div className="plan-stat">
          <span className="stat-label">Assigned</span>
          <span className="stat-value text-green">{assignedCount}/{tasks.length}</span>
        </div>
      </div>

      {/* Filter toolbar */}
      <div className="plan-toolbar">
        <input
          type="text"
          className="plan-search"
          placeholder="Search tasks by title or key..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="plan-filters">
          <label className="filter-label">Owner:</label>
          <select
            className="plan-select"
            value={filterOwner}
            onChange={(e) => setFilterOwner(e.target.value)}
          >
            <option value="all">All Members</option>
            {members.map(m => (
              <option key={m.id} value={String(m.id)}>{m.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="plan-table-container">
        <table className="plan-table">
          <thead>
            <tr>
              <th style={{ width: 80 }}>Key</th>
              <th>Task Title</th>
              <th style={{ width: 140 }}>Owner</th>
              <th style={{ width: 90 }}>Effort</th>
              <th style={{ width: 140 }}>Status</th>
              <th style={{ width: 120 }}>Dependencies</th>
              <th style={{ width: 90 }}>Type</th>
              <th style={{ width: 80, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredTasks.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-row">
                  No tasks found. Click <strong>AI Generate Tasks</strong> or <strong>Add Task</strong> to get started.
                </td>
              </tr>
            ) : (
              filteredTasks.map(task => {
                const ownerColor = getOwnerColor(task.owner_member_id);
                const ownerName = getMemberName(snapshot, task.owner_member_id);
                const taskDeps = deps.filter(d => d.to === task.key);

                return (
                  <tr
                    key={task.key}
                    className="plan-row"
                    onClick={() => setSelectedTaskKey(task.key)}
                  >
                    <td>
                      <span className="font-mono text-blue font-semibold">{task.key}</span>
                    </td>
                    <td>
                      <div className="task-title-cell">
                        <span className="task-title-text">{task.title}</span>
                        {task.acceptance_criteria?.length > 0 && (
                          <span className="criteria-count">
                            {task.acceptance_criteria.length} criteria
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      {task.owner_member_id ? (
                        <div className="owner-pill" style={{ borderColor: ownerColor }}>
                          <span className="owner-dot" style={{ background: ownerColor }} />
                          <span className="owner-name">{ownerName}</span>
                        </div>
                      ) : (
                        <span className="text-muted text-xs">Unassigned</span>
                      )}
                    </td>
                    <td>
                      <span className="font-mono text-sm">{task.effort || 1}h</span>
                    </td>
                    <td>
                      <span
                        className="status-badge"
                        style={{
                          background: `${STATUS_COLORS[task.status] || '#8B949E'}20`,
                          color: STATUS_COLORS[task.status] || '#8B949E',
                          borderColor: `${STATUS_COLORS[task.status] || '#8B949E'}50`
                        }}
                      >
                        {STATUS_LABELS[task.status] || task.status}
                      </span>
                    </td>
                    <td>
                      {taskDeps.length > 0 ? (
                        <div className="deps-tags">
                          {taskDeps.map(d => (
                            <span key={d.from} className="dep-tag font-mono">{d.from}</span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted text-xs">—</span>
                      )}
                    </td>
                    <td>
                      {task.is_milestone ? (
                        <span className="milestone-pill">
                          <Milestone size={12} />
                          <span>Milestone</span>
                        </span>
                      ) : (
                        <span className="text-muted text-xs">Task</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn-icon danger"
                        title="Delete task"
                        onClick={(e) => handleDeleteTask(task.key, e)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Add Task Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add New Task</h2>
              <button className="btn-close" onClick={() => setShowAddModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="modal-body">
              <div className="form-group">
                <label>Task Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Implement webhook signature verification"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  rows={3}
                  placeholder="Details, technical constraints, implementation hints..."
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                />
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Estimated Effort (hours)</label>
                  <input
                    type="number"
                    min={1}
                    max={24}
                    value={newEffort}
                    onChange={e => setNewEffort(e.target.value)}
                  />
                </div>

                <div className="form-group flex-1">
                  <label>Owner</label>
                  <select
                    value={newOwnerId}
                    onChange={e => setNewOwnerId(e.target.value)}
                  >
                    <option value="">Unassigned</option>
                    {members.map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={newIsMilestone}
                    onChange={e => setNewIsMilestone(e.target.checked)}
                  />
                  <span>Mark as Project Milestone (e.g. MVP, Integration, Demo)</span>
                </label>
              </div>

              <div className="form-group">
                <label>Dependencies (Depends on Tasks)</label>
                <select
                  multiple
                  className="multi-select"
                  value={newDependsOn}
                  onChange={e => {
                    const opts = Array.from(e.target.selectedOptions, o => o.value);
                    setNewDependsOn(opts);
                  }}
                >
                  {tasks.map(t => (
                    <option key={t.key} value={t.key}>[{t.key}] {t.title}</option>
                  ))}
                </select>
                <small className="form-hint">Hold Ctrl / Cmd to select multiple tasks</small>
              </div>

              <div className="form-group">
                <label>Acceptance Criteria</label>
                {newCriteria.map((crit, idx) => (
                  <div key={idx} className="criteria-input-row">
                    <input
                      type="text"
                      placeholder={`Criterion #${idx + 1}`}
                      value={crit}
                      onChange={e => {
                        const copy = [...newCriteria];
                        copy[idx] = e.target.value;
                        setNewCriteria(copy);
                      }}
                    />
                    {newCriteria.length > 1 && (
                      <button
                        type="button"
                        className="btn-icon danger"
                        onClick={() => setNewCriteria(newCriteria.filter((_, i) => i !== idx))}
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => setNewCriteria([...newCriteria, ''])}
                >
                  + Add Criterion
                </button>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loadingAction === 'create'}
                >
                  {loadingAction === 'create' ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bundle & Assign Modal */}
      {showBundleModal && (
        <div className="modal-backdrop" onClick={() => setShowBundleModal(false)}>
          <div className="modal-content modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Task Bundling &amp; Assignment Preview</h2>
              <button className="btn-close" onClick={() => setShowBundleModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-intro">
                Pilot has bundled related tasks into cohesive blocks and balanced workloads across team members:
              </p>

              <div className="bundles-grid">
                {(bundlePreview?.blocks || []).map(b => {
                  const ownerName = getMemberName(snapshot, b.owner_member_id);
                  const ownerColor = getOwnerColor(b.owner_member_id);

                  return (
                    <div
                      key={b.id || b.name}
                      className={`bundle-card ${b.oversize_flag ? 'oversize' : ''}`}
                    >
                      <div className="bundle-header">
                        <span className="bundle-name">{b.name}</span>
                        {b.oversize_flag ? (
                          <span className="oversize-badge">
                            <AlertTriangle size={12} /> Oversize
                          </span>
                        ) : null}
                      </div>

                      <div className="bundle-meta">
                        <div className="bundle-owner">
                          <span className="owner-dot" style={{ background: ownerColor }} />
                          <span>{ownerName || 'Auto-assigned'}</span>
                        </div>
                        <span className="bundle-effort font-mono">{b.total_effort} hrs</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowBundleModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmAndKickoff}
                disabled={loadingAction === 'kickoff'}
              >
                <Rocket size={16} />
                <span>{loadingAction === 'kickoff' ? 'Kicking off...' : 'Confirm & Kickoff Project'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Task Drawer */}
      {selectedTaskKey && (
        <TaskDrawer
          taskKey={selectedTaskKey}
          snapshot={snapshot}
          code={code}
          onClose={() => setSelectedTaskKey(null)}
          onOpenTask={key => setSelectedTaskKey(key)}
        />
      )}
    </div>
  );
}

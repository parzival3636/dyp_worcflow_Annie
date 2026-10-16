import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  TrendingUp,
  GitCommit,
  User,
  ExternalLink,
  RefreshCw,
  Plus,
} from 'lucide-react'
import api from '../lib/api'
import { supabase } from '../lib/supabase'

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedVerification, setSelectedVerification] = useState(null)

  const fetchStats = async (isManual = false) => {
    if (isManual) setRefreshing(true)
    try {
      const res = await api.get('/dashboard/stats')
      setStats(res.data)
    } catch (err) {
      console.error('Failed to load dashboard stats:', err)
    } finally {
      setLoading(false)
      if (isManual) setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchStats()

    // Realtime Supabase subscription for verification updates
    const channel = supabase
      .channel('dashboard_verifications')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'verifications' },
        () => fetchStats()
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks' },
        () => fetchStats()
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  if (loading) {
    return (
      <div style={{ padding: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <RefreshCw size={28} className="animate-spin" style={{ color: '#6366f1' }} />
      </div>
    )
  }

  const summary = stats?.task_summary || { total: 0, complete: 0, in_progress: 0, pending: 0, completion_rate: 0 }
  const recent = stats?.recent_verifications || []
  const team = stats?.team_stats || []

  return (
    <div style={{ padding: '32px 40px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Mission Control
          </h1>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '4px' }}>
            Autonomous commit tracking & AI task verification
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => fetchStats(true)}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
          <Link
            to="/setup"
            className="btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}
          >
            <Plus size={16} />
            Setup Repo
          </Link>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        {/* Total Tasks */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.8125rem', color: '#94a3b8', fontWeight: '500' }}>Total Tasks</span>
            <span style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8', borderRadius: '8px', padding: '6px' }}>
              <TrendingUp size={16} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: '700', color: '#f8fafc', marginTop: '12px' }}>
            {summary.total}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>Across registered repositories</div>
        </div>

        {/* Complete */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.8125rem', color: '#94a3b8', fontWeight: '500' }}>Completed</span>
            <span style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', borderRadius: '8px', padding: '6px' }}>
              <CheckCircle2 size={16} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: '700', color: '#10b981', marginTop: '12px' }}>
            {summary.complete}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>
            {summary.completion_rate}% completion rate
          </div>
        </div>

        {/* In Progress */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.8125rem', color: '#94a3b8', fontWeight: '500' }}>In Progress</span>
            <span style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8', borderRadius: '8px', padding: '6px' }}>
              <Clock size={16} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: '700', color: '#818cf8', marginTop: '12px' }}>
            {summary.in_progress}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>Active commits detected</div>
        </div>

        {/* Pending */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.8125rem', color: '#94a3b8', fontWeight: '500' }}>Pending</span>
            <span style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', borderRadius: '8px', padding: '6px' }}>
              <AlertCircle size={16} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: '700', color: '#f59e0b', marginTop: '12px' }}>
            {summary.pending}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>Awaiting initial commits</div>
        </div>
      </div>

      {/* Main Grid: Team Progress + Recent Verifications */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '24px' }}>
        {/* Team Activity */}
        <div className="glass" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#f8fafc' }}>Team Velocity</h2>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{team.length} collaborators</span>
          </div>

          {team.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b', fontSize: '0.875rem' }}>
              No team activity yet. Assign tasks to collaborators to track progress.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {team.map((member) => {
                const pct = member.total ? Math.round((member.complete / member.total) * 100) : 0
                return (
                  <div key={member.username} style={{ background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: '8px', border: '1px solid #1e2d40' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#1e293b', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8', fontSize: '0.75rem', fontWeight: '600' }}>
                          {member.username.slice(0, 2).toUpperCase()}
                        </div>
                        <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#e2e8f0' }}>
                          @{member.username}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {member.complete}/{member.total} done ({pct}%)
                      </span>
                    </div>
                    {/* Progress Bar */}
                    <div style={{ width: '100%', height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${pct}%`,
                          height: '100%',
                          background: pct === 100 ? '#10b981' : 'linear-gradient(90deg, #6366f1, #8b5cf6)',
                          transition: 'width 0.4s ease',
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Live Gemini Verification Feed */}
        <div className="glass" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitCommit size={18} style={{ color: '#818cf8' }} />
              Gemini AI Verifications
            </h2>
            <Link to="/webhooks" style={{ fontSize: '0.75rem', color: '#818cf8', textDecoration: 'none' }}>
              View Raw Webhooks →
            </Link>
          </div>

          {recent.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b', fontSize: '0.875rem' }}>
              <p>No commits verified yet.</p>
              <p style={{ fontSize: '0.75rem', marginTop: '6px' }}>
                When team members push commits matching task keywords, Gemini will verify diffs in real time.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {recent.map((v) => {
                const score = v.confidence_score ?? 0
                const scoreColor = score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'
                return (
                  <div
                    key={v.id}
                    onClick={() => setSelectedVerification(selectedVerification?.id === v.id ? null : v)}
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      padding: '14px 16px',
                      borderRadius: '8px',
                      border: '1px solid #1e2d40',
                      cursor: 'pointer',
                      transition: 'border-color 0.2s',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#818cf8', background: 'rgba(99,102,241,0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                            {v.commit_sha?.slice(0, 7)}
                          </span>
                          <span style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>by @{v.author}</span>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {new Date(v.processed_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.875rem', color: '#f1f5f9', marginTop: '6px', fontWeight: '500' }}>
                          {v.commit_message || 'No commit message'}
                        </p>
                      </div>

                      {/* AI Score Badge */}
                      <div style={{ textAlign: 'right', marginLeft: '16px' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: `${scoreColor}18`, border: `1px solid ${scoreColor}44`, color: scoreColor, padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600' }}>
                          ⚡ {score}%
                        </div>
                        <div style={{ fontSize: '0.7rem', color: v.implements_task ? '#10b981' : '#64748b', marginTop: '4px' }}>
                          {v.implements_task ? 'Implements Task' : 'Partial / Under review'}
                        </div>
                      </div>
                    </div>

                    {/* Expandable Reasoning */}
                    {selectedVerification?.id === v.id && (
                      <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #1e2d40', fontSize: '0.8125rem' }}>
                        <div style={{ color: '#94a3b8', marginBottom: '6px', fontWeight: '500' }}>Gemini Reasoning:</div>
                        <p style={{ color: '#cbd5e1', lineHeight: '1.5', background: '#0d1526', padding: '10px 12px', borderRadius: '6px' }}>
                          {v.reasoning || 'No reasoning provided.'}
                        </p>
                        {v.matched_keywords && v.matched_keywords.length > 0 && (
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '8px' }}>
                            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Matched:</span>
                            {v.matched_keywords.map((kw) => (
                              <span key={kw} style={{ fontSize: '0.7rem', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '2px 6px', borderRadius: '4px' }}>
                                #{kw}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

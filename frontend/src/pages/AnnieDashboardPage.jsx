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
  Shield,
  Layers
} from 'lucide-react'
import api from '../lib/api'
import { supabase } from '../lib/supabase'
import AnnieNav from './AnnieNav'
import './Annie.css'

export default function AnnieDashboardPage() {
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

  const summary = stats?.task_summary || { total: 0, complete: 0, in_progress: 0, pending: 0, completion_rate: 0 }
  const recent = stats?.recent_verifications || []
  const team = stats?.team_stats || []

  return (
    <div className="annie-container" style={{ minHeight: '100%', background: 'var(--bg, #F8F9FA)' }}>
      <AnnieNav />

      {loading ? (
        <div style={{ padding: '80px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
          <RefreshCw size={28} className="animate-spin" style={{ color: '#FF6B3D' }} />
          <span style={{ fontSize: '13px', color: '#64748B' }}>Loading Mission Control...</span>
        </div>
      ) : (
        <div style={{ padding: '28px 40px', maxWidth: '1360px', margin: '0 auto' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
            <div>
              <h1 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#0F172A', letterSpacing: '-0.02em', margin: 0 }}>
                Mission Control &amp; AI CI Telemetry
              </h1>
              <p style={{ color: '#64748B', fontSize: '0.875rem', marginTop: '4px' }}>
                Autonomous commit tracking, verification confidence scores, and team execution metrics.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => fetchStats(true)}
                className="btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                Refresh Telemetry
              </button>
              <Link
                to="/p/demo01/lead"
                className="btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}
              >
                <Shield size={14} />
                Configure in Leader Portal
              </Link>
            </div>
          </div>

          {/* KPI Stats Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
            {/* Total Tasks */}
            <div className="annie-card" style={{ padding: '20px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.8125rem', color: '#64748B', fontWeight: '600' }}>Total Tasks</span>
                <span style={{ background: 'rgba(255, 107, 61, 0.08)', color: '#FF6B3D', borderRadius: '6px', padding: '6px' }}>
                  <TrendingUp size={16} />
                </span>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#0F172A', marginTop: '8px' }}>
                {summary.total}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px' }}>Across registered repositories</div>
            </div>

            {/* Complete */}
            <div className="annie-card" style={{ padding: '20px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.8125rem', color: '#64748B', fontWeight: '600' }}>AI Verified Complete</span>
                <span style={{ background: '#ECFDF5', color: '#047857', borderRadius: '6px', padding: '6px' }}>
                  <CheckCircle2 size={16} />
                </span>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#047857', marginTop: '8px' }}>
                {summary.complete}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#059669', marginTop: '4px', fontWeight: 600 }}>
                {summary.completion_rate}% completion rate
              </div>
            </div>

            {/* In Progress */}
            <div className="annie-card" style={{ padding: '20px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.8125rem', color: '#64748B', fontWeight: '600' }}>In Progress (Commits Detected)</span>
                <span style={{ background: 'rgba(255, 107, 61, 0.08)', color: '#FF6B3D', borderRadius: '6px', padding: '6px' }}>
                  <Clock size={16} />
                </span>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#FF6B3D', marginTop: '8px' }}>
                {summary.in_progress}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px' }}>Active development commits</div>
            </div>

            {/* Pending */}
            <div className="annie-card" style={{ padding: '20px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.8125rem', color: '#64748B', fontWeight: '600' }}>Pending Verification</span>
                <span style={{ background: '#FFFBEB', color: '#D97706', borderRadius: '6px', padding: '6px' }}>
                  <AlertCircle size={16} />
                </span>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#D97706', marginTop: '8px' }}>
                {summary.pending}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px' }}>Awaiting initial push events</div>
            </div>
          </div>

          {/* Main Grid: Team Progress + Recent Verifications */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '24px' }}>
            {/* Team Velocity */}
            <div className="annie-card" style={{ padding: '24px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#0F172A', margin: 0 }}>Team Velocity</h2>
                <span style={{ fontSize: '0.75rem', color: '#64748B', background: '#F1F5F9', padding: '2px 8px', borderRadius: '4px' }}>
                  {team.length} collaborators
                </span>
              </div>

              {team.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748B', fontSize: '0.875rem' }}>
                  No team activity yet. Assign tasks to collaborators to track progress.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {team.map((member) => {
                    const pct = member.total ? Math.round((member.complete / member.total) * 100) : 0
                    return (
                      <div key={member.username} style={{ background: '#F8F9FA', padding: '14px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(255, 107, 61, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#FF6B3D', fontSize: '0.75rem', fontWeight: '700' }}>
                              {member.username.slice(0, 2).toUpperCase()}
                            </div>
                            <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#0F172A' }}>
                              @{member.username}
                            </span>
                          </div>
                          <span style={{ fontSize: '0.75rem', color: '#64748B', fontWeight: 500 }}>
                            {member.complete}/{member.total} verified ({pct}%)
                          </span>
                        </div>
                        {/* Progress Bar */}
                        <div style={{ width: '100%', height: '6px', background: '#E2E8F0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${pct}%`,
                              height: '100%',
                              background: pct === 100 ? '#10B981' : 'linear-gradient(90deg, #FF6B3D, #FF9066)',
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
            <div className="annie-card" style={{ padding: '24px', background: '#FFFFFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                  <GitCommit size={18} style={{ color: '#FF6B3D' }} />
                  Gemini AI Verifications
                </h2>
                <Link to="/annie/webhooks" style={{ fontSize: '0.75rem', color: '#FF6B3D', textDecoration: 'none', fontWeight: 600 }}>
                  View Raw Webhook Queue &rarr;
                </Link>
              </div>

              {recent.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748B', fontSize: '0.875rem' }}>
                  <p>No commits verified yet.</p>
                  <p style={{ fontSize: '0.75rem', marginTop: '6px' }}>
                    When team members push commits matching task keywords, Gemini will verify diffs in real time.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {recent.map((v) => {
                    const score = v.confidence_score ?? 0
                    const scoreColor = score >= 80 ? '#047857' : score >= 50 ? '#D97706' : '#DC2626'
                    const scoreBg = score >= 80 ? '#ECFDF5' : score >= 50 ? '#FFFBEB' : '#FEF2F2'
                    return (
                      <div
                        key={v.id}
                        onClick={() => setSelectedVerification(selectedVerification?.id === v.id ? null : v)}
                        style={{
                          background: '#F8F9FA',
                          padding: '14px 16px',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          cursor: 'pointer',
                          transition: 'border-color 0.2s',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#FF6B3D', background: 'rgba(255, 107, 61, 0.08)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                {v.commit_sha?.slice(0, 7)}
                              </span>
                              <span style={{ fontSize: '0.8125rem', color: '#64748B' }}>by @{v.author}</span>
                              <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>
                                {new Date(v.processed_at).toLocaleTimeString()}
                              </span>
                            </div>
                            <p style={{ fontSize: '0.875rem', color: '#0F172A', marginTop: '6px', fontWeight: '600' }}>
                              {v.commit_message || 'No commit message'}
                            </p>
                          </div>

                          {/* AI Score Badge */}
                          <div style={{ textAlign: 'right', marginLeft: '16px' }}>
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: scoreBg, border: `1px solid ${scoreColor}33`, color: scoreColor, padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '700' }}>
                              ⚡ {score}%
                            </div>
                            <div style={{ fontSize: '0.7rem', color: v.implements_task ? '#047857' : '#64748B', marginTop: '4px', fontWeight: 500 }}>
                              {v.implements_task ? 'Task Implemented' : 'Partial / Under Review'}
                            </div>
                          </div>
                        </div>

                        {/* Expandable Reasoning */}
                        {selectedVerification?.id === v.id && (
                          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #E2E8F0', fontSize: '0.8125rem' }}>
                            <div style={{ color: '#475569', marginBottom: '6px', fontWeight: '600' }}>Gemini Reasoning:</div>
                            <p style={{ color: '#0F172A', lineHeight: '1.5', background: '#FFFFFF', border: '1px solid #E2E8F0', padding: '10px 12px', borderRadius: '6px' }}>
                              {v.reasoning || 'No reasoning provided.'}
                            </p>
                            {v.matched_keywords && v.matched_keywords.length > 0 && (
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '8px' }}>
                                <span style={{ fontSize: '0.75rem', color: '#64748B' }}>Matched Keywords:</span>
                                {v.matched_keywords.map((kw) => (
                                  <span key={kw} style={{ fontSize: '0.7rem', background: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
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
      )}
    </div>
  )
}

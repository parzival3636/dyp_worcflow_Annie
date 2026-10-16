import { useState, useEffect } from 'react'
import {
  Activity,
  CheckCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  GitCommit,
  ChevronDown,
  ChevronRight,
  Code2,
} from 'lucide-react'
import api from '../lib/api'
import { supabase } from '../lib/supabase'

export default function WebhookLogPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('all')
  const [expandedEventId, setExpandedEventId] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchEvents = async (manual = false) => {
    if (manual) setRefreshing(true)
    try {
      const url = filterStatus === 'all'
        ? '/dashboard/webhook-events'
        : `/dashboard/webhook-events?status=${filterStatus}`
      const res = await api.get(url)
      setEvents(res.data.events || [])
    } catch (err) {
      console.error('Failed to load webhook events:', err)
    } finally {
      setLoading(false)
      if (manual) setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchEvents()

    // Realtime Supabase listener for webhook events
    const channel = supabase
      .channel('webhook_events_live')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'webhook_events' },
        () => fetchEvents()
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [filterStatus])

  const toggleExpand = (id) => {
    setExpandedEventId(expandedEventId === id ? null : id)
  }

  return (
    <div style={{ padding: '32px 40px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Webhook Telemetry Log
          </h1>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '4px' }}>
            Live event pipeline: GitHub → Supabase Edge Function → Annie Backend Queue.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <select
            className="input"
            style={{ width: 'auto', padding: '6px 14px' }}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending Queue</option>
            <option value="processed">Processed</option>
            <option value="failed">Failed</option>
          </select>
          <button
            onClick={() => fetchEvents(true)}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Events Table / List */}
      <div className="glass" style={{ padding: '24px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>
            Loading webhook events...
          </div>
        ) : events.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
            <Activity size={36} style={{ margin: '0 auto 12px', color: '#475569' }} />
            <p style={{ fontSize: '1rem', color: '#94a3b8', fontWeight: '500' }}>No webhook events recorded</p>
            <p style={{ fontSize: '0.8125rem', marginTop: '4px' }}>
              Whenever GitHub triggers a push event to your Supabase Edge Function, it appears here in real time.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {events.map((evt) => {
              const isExpanded = expandedEventId === evt.id
              const status = evt.status || 'pending'
              const statusColor =
                status === 'processed' ? '#10b981' : status === 'pending' ? '#f59e0b' : '#ef4444'

              return (
                <div
                  key={evt.id}
                  style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid #1e2d40',
                    borderRadius: '8px',
                    padding: '16px',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                      <button
                        onClick={() => toggleExpand(evt.id)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#64748b',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </button>

                      {/* Event Type & Repo */}
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              color: '#818cf8',
                              background: 'rgba(99,102,241,0.1)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            {evt.event_type || 'push'}
                          </span>
                          <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#f1f5f9' }}>
                            {evt.repo_name || 'unknown-repo'}
                          </span>
                          {evt.commit_sha && (
                            <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#64748b' }}>
                              #{evt.commit_sha.slice(0, 7)}
                            </span>
                          )}
                        </div>

                        <div style={{ fontSize: '0.8125rem', color: '#94a3b8', marginTop: '4px' }}>
                          {evt.commit_message || (evt.payload?.head_commit?.message) || 'No message'}
                        </div>
                      </div>
                    </div>

                    {/* Status & Timestamp */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          {new Date(evt.created_at).toLocaleTimeString()}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
                          {new Date(evt.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      <span
                        style={{
                          background: `${statusColor}18`,
                          color: statusColor,
                          border: `1px solid ${statusColor}44`,
                          padding: '3px 10px',
                          borderRadius: '999px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                        }}
                      >
                        {status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #1e2d40' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '0.75rem', marginBottom: '8px' }}>
                        <Code2 size={14} />
                        Raw Supabase Webhook Payload (JSON):
                      </div>
                      <pre
                        style={{
                          background: '#0a0f1e',
                          border: '1px solid #1e2d40',
                          borderRadius: '6px',
                          padding: '12px',
                          fontSize: '0.75rem',
                          color: '#a5b4fc',
                          overflowX: 'auto',
                          maxHeight: '260px',
                        }}
                      >
                        {JSON.stringify(evt.payload || evt, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

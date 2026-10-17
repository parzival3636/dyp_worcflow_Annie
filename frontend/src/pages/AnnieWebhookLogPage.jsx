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
import AnnieNav from './AnnieNav'
import './Annie.css'

export default function AnnieWebhookLogPage() {
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
    <div className="annie-container" style={{ minHeight: '100%', background: 'var(--bg, #F8F9FA)' }}>
      <AnnieNav />

      <div style={{ padding: '28px 40px', maxWidth: '1360px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#0F172A', letterSpacing: '-0.02em', margin: 0 }}>
              Webhook Telemetry Log
            </h1>
            <p style={{ color: '#64748B', fontSize: '0.875rem', marginTop: '4px' }}>
              Live event ingestion pipeline: GitHub &rarr; Supabase Webhooks &rarr; Background Worker Queue.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
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
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Events Table / List */}
        <div className="annie-card" style={{ padding: '24px', background: '#FFFFFF' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748B' }}>
              <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px', color: '#FF6B3D' }} />
              Loading webhook events...
            </div>
          ) : events.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748B' }}>
              <Activity size={40} style={{ margin: '0 auto 12px', color: '#CBD5E1' }} />
              <h3 style={{ fontSize: '1.05rem', color: '#0F172A', fontWeight: '600' }}>No webhook events recorded</h3>
              <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
                Whenever GitHub triggers a push event to your webhook, it appears here in real time.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {events.map((evt) => {
                const isExpanded = expandedEventId === evt.id
                const status = evt.status || 'pending'
                const statusColor =
                  status === 'processed' ? '#047857' : status === 'pending' ? '#D97706' : '#DC2626'
                const statusBg =
                  status === 'processed' ? '#ECFDF5' : status === 'pending' ? '#FFFBEB' : '#FEF2F2'

                return (
                  <div
                    key={evt.id}
                    style={{
                      background: '#F8F9FA',
                      border: '1px solid #E2E8F0',
                      borderRadius: '8px',
                      padding: '16px',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                        <button
                          onClick={() => toggleExpand(evt.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#64748B',
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
                                fontWeight: '700',
                                color: '#FF6B3D',
                                background: 'rgba(255, 107, 61, 0.08)',
                                border: '1px solid rgba(255, 107, 61, 0.25)',
                                padding: '2px 8px',
                                borderRadius: '4px',
                              }}
                            >
                              {evt.event_type || 'push'}
                            </span>
                            <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#0F172A' }}>
                              {evt.repo_name || 'unknown-repo'}
                            </span>
                            {evt.commit_sha && (
                              <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#64748B' }}>
                                #{evt.commit_sha.slice(0, 7)}
                              </span>
                            )}
                          </div>

                          <div style={{ fontSize: '0.8125rem', color: '#334155', marginTop: '4px' }}>
                            {evt.commit_message || (evt.raw_payload?.head_commit?.message) || 'No commit message'}
                          </div>
                        </div>
                      </div>

                      {/* Status & Timestamp */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '0.75rem', color: '#0F172A', fontWeight: 500 }}>
                            {new Date(evt.created_at).toLocaleTimeString()}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '2px' }}>
                            {new Date(evt.created_at).toLocaleDateString()}
                          </div>
                        </div>

                        <span
                          style={{
                            background: statusBg,
                            color: statusColor,
                            border: `1px solid ${statusColor}33`,
                            padding: '3px 10px',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: '700',
                          }}
                        >
                          {status.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid #E2E8F0' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748B', fontSize: '0.75rem', marginBottom: '8px', fontWeight: 600 }}>
                          <Code2 size={14} />
                          Raw Webhook Payload JSON:
                        </div>
                        <pre
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E2E8F0',
                            borderRadius: '6px',
                            padding: '12px',
                            fontSize: '0.75rem',
                            color: '#1E293B',
                            overflowX: 'auto',
                            maxHeight: '260px',
                            fontFamily: 'monospace',
                          }}
                        >
                          {JSON.stringify(evt.raw_payload || evt, null, 2)}
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
    </div>
  )
}

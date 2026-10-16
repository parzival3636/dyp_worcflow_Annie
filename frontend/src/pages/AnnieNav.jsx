import { NavLink } from 'react-router-dom'
import { LayoutDashboard, GitBranch, CheckSquare, Activity, ArrowLeft } from 'lucide-react'

const navItems = [
  { to: '/annie',          icon: LayoutDashboard, label: 'Mission Control' },
  { to: '/annie/setup',    icon: GitBranch,       label: 'Setup Repo & Webhook' },
  { to: '/annie/tasks',    icon: CheckSquare,     label: 'Verified Tasks' },
  { to: '/annie/webhooks', icon: Activity,        label: 'Webhook Telemetry' },
]

export default function AnnieNav() {
  return (
    <div style={{
      background: '#FFFFFF',
      borderBottom: '1px solid #E2E8F0',
      padding: '12px 32px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 40,
      boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '1.25rem',
            fontWeight: '800',
            background: 'linear-gradient(135deg, #FF6B3D, #FF8F6B)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}>
            ⚡ Annie
          </span>
          <span style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            background: 'rgba(255, 107, 61, 0.08)',
            border: '1px solid rgba(255, 107, 61, 0.25)',
            borderRadius: '9999px',
            color: '#FF6B3D',
            fontWeight: 600,
          }}>
            GitHub & AI Verification
          </span>
        </div>

        <nav style={{ display: 'flex', gap: '6px' }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                borderRadius: '6px',
                color: isActive ? '#FF6B3D' : '#475569',
                background: isActive ? 'rgba(255, 107, 61, 0.08)' : 'transparent',
                border: isActive ? '1px solid rgba(255, 107, 61, 0.3)' : '1px solid transparent',
                textDecoration: 'none',
                fontSize: '0.85rem',
                fontWeight: isActive ? 600 : 500,
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <a
          href="/p/demo01"
          style={{
            fontSize: '0.8125rem',
            color: '#64748B',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontWeight: 500,
            padding: '6px 12px',
            borderRadius: '6px',
            border: '1px solid #E2E8F0',
            background: '#FFFFFF',
            transition: 'all 0.15s ease',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.color = '#0F172A'
            e.currentTarget.style.borderColor = '#CBD5E1'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.color = '#64748B'
            e.currentTarget.style.borderColor = '#E2E8F0'
          }}
        >
          <ArrowLeft size={13} />
          Return to Pilot Flight Deck
        </a>
      </div>
    </div>
  )
}

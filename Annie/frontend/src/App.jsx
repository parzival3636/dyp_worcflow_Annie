import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LayoutDashboard, GitBranch, CheckSquare, Activity } from 'lucide-react'
import SetupPage from './pages/SetupPage'
import TasksPage from './pages/TasksPage'
import DashboardPage from './pages/DashboardPage'
import WebhookLogPage from './pages/WebhookLogPage'
import './index.css'

const navItems = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard'   },
  { to: '/setup',     icon: GitBranch,       label: 'Setup Repo'  },
  { to: '/tasks',     icon: CheckSquare,     label: 'Tasks'       },
  { to: '/webhooks',  icon: Activity,        label: 'Webhook Log' },
]

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#111827',
            color: '#e2e8f0',
            border: '1px solid #1e2d40',
          },
        }}
      />
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Sidebar */}
        <nav style={{
          width: '220px',
          background: '#0d1424',
          borderRight: '1px solid #1e2d40',
          padding: '24px 0',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          flexShrink: 0,
        }}>
          {/* Logo */}
          <div style={{ padding: '0 20px 24px', borderBottom: '1px solid #1e2d40', marginBottom: '8px' }}>
            <div style={{
              fontSize: '1.25rem',
              fontWeight: '700',
              background: 'linear-gradient(135deg, #6366f1, #a78bfa)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              ⚡ Annie
            </div>
            <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
              Task Verification System
            </div>
          </div>

          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 20px',
                color: isActive ? '#818cf8' : '#94a3b8',
                background: isActive ? 'rgba(99,102,241,0.1)' : 'transparent',
                borderRight: isActive ? '2px solid #6366f1' : '2px solid transparent',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: isActive ? '500' : '400',
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Main content */}
        <main style={{ flex: 1, overflow: 'auto', background: '#0a0f1e' }}>
          <Routes>
            <Route path="/"         element={<DashboardPage />} />
            <Route path="/setup"    element={<SetupPage />} />
            <Route path="/tasks"    element={<TasksPage />} />
            <Route path="/webhooks" element={<WebhookLogPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

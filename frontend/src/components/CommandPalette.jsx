import React, { useEffect } from 'react';
import { Command } from 'cmdk';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Search,
  LayoutGrid,
  ListTodo,
  Calendar,
  GitFork,
  BarChart3,
  Clock,
  Send,
  Sun,
  Moon,
  Shield,
  Bot,
  Activity,
  FileCheck2
} from 'lucide-react';
import './CommandPalette.css';

export default function CommandPalette({
  open,
  onClose,
  tasks = [],
  theme,
  onToggleTheme,
  onTriggerFollowUp,
  onSelectTask
}) {
  const navigate = useNavigate();
  const { code } = useParams();

  // Keyboard shortcut for Cmd+K and G-then-X
  useEffect(() => {
    let lastKey = '';
    let lastKeyTime = 0;

    const handleKeyDown = (e) => {
      // Toggle palette on Cmd+K / Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (open) onClose();
        else onClose(false); // flip
      }

      // If user is not typing in an input
      const target = e.target;
      if (['INPUT', 'TEXTAREA'].includes(target.tagName) || target.isContentEditable) {
        return;
      }

      const now = Date.now();
      if (e.key === 'g' || e.key === 'G') {
        lastKey = 'g';
        lastKeyTime = now;
        return;
      }

      if (lastKey === 'g' && now - lastKeyTime < 1000) {
        const k = e.key.toLowerCase();
        if (k === 'b') { e.preventDefault(); navigate(`/p/${code}`); }
        else if (k === 'o') { e.preventDefault(); navigate(`/p/${code}/overview`); }
        else if (k === 'p') { e.preventDefault(); navigate(`/p/${code}/plan`); }
        else if (k === 't') { e.preventDefault(); navigate(`/p/${code}/timeline`); }
        else if (k === 'd' || k === 'g') { e.preventDefault(); navigate(`/p/${code}/graph`); }
        else if (k === 'c') { e.preventDefault(); navigate(`/p/${code}/contributions`); }
        else if (k === 'a') { e.preventDefault(); navigate(`/p/${code}/activity`); }
        else if (k === 'l') { e.preventDefault(); navigate(`/p/${code}/lead`); }
        else if (k === 'r') { e.preventDefault(); navigate(`/p/${code}/guide`); }
        lastKey = '';
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose, navigate, code]);

  if (!open) return null;

  return (
    <div className="cmdk-overlay" onClick={onClose}>
      <div className="cmdk-dialog" onClick={(e) => e.stopPropagation()}>
        <Command label="Pilot Ops Command Palette">
          <div className="cmdk-header">
            <Search size={16} className="text-muted" />
            <Command.Input
              placeholder="Type a command or search tasks (e.g. T-2)..."
              className="cmdk-input"
              autoFocus
            />
          </div>

          <Command.List className="cmdk-list">
            <Command.Empty className="cmdk-empty">
              No matching commands or tasks found.
            </Command.Empty>

            {/* Navigation Group */}
            <Command.Group heading="Views & Portals" className="cmdk-group-heading">
              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/overview`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <Activity size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Executive Overview</span>
                </div>
                <span className="cmdk-item-shortcut">G O</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <LayoutGrid size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Kanban Board</span>
                </div>
                <span className="cmdk-item-shortcut">G B</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/plan`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <ListTodo size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Backlog & Plan</span>
                </div>
                <span className="cmdk-item-shortcut">G P</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/timeline`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <Calendar size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Timeline Gantt</span>
                </div>
                <span className="cmdk-item-shortcut">G T</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/graph`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <GitFork size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Dependency DAG</span>
                </div>
                <span className="cmdk-item-shortcut">G G</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/contributions`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <BarChart3 size={14} className="text-secondary" />
                  <span className="cmdk-item-title">Go to Contributions</span>
                </div>
                <span className="cmdk-item-shortcut">G C</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/lead`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <Shield size={14} className="text-accent" />
                  <span className="cmdk-item-title">Open Project Leader Portal</span>
                </div>
                <span className="cmdk-item-shortcut">G L</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { navigate(`/p/${code}/guide`); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <Bot size={14} style={{ color: 'var(--status-needs_review)' }} />
                  <span className="cmdk-item-title">Open Guide Coordinator Radar</span>
                </div>
                <span className="cmdk-item-shortcut">G R</span>
              </Command.Item>
            </Command.Group>

            {/* Quick Actions */}
            <Command.Group heading="Actions" className="cmdk-group-heading">
              <Command.Item
                className="cmdk-item"
                onSelect={() => { onTriggerFollowUp?.(); onClose(); }}
              >
                <div className="cmdk-item-left">
                  <Send size={14} className="text-accent" />
                  <span className="cmdk-item-title">Run Telegram check-in follow-up now</span>
                </div>
                <span className="cmdk-item-shortcut">↵</span>
              </Command.Item>

              <Command.Item
                className="cmdk-item"
                onSelect={() => { onToggleTheme?.(); onClose(); }}
              >
                <div className="cmdk-item-left">
                  {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
                  <span className="cmdk-item-title">
                    Switch to {theme === 'dark' ? 'Warm Paper' : 'Flight Deck Dark'} theme
                  </span>
                </div>
                <span className="cmdk-item-shortcut">Theme</span>
              </Command.Item>
            </Command.Group>

            {/* Tasks jump list */}
            {tasks.length > 0 && (
              <Command.Group heading="Jump to Task" className="cmdk-group-heading">
                {tasks.map(t => (
                  <Command.Item
                    key={t.key}
                    className="cmdk-item"
                    onSelect={() => {
                      onSelectTask?.(t.key);
                      onClose();
                    }}
                  >
                    <div className="cmdk-item-left">
                      <span className="font-mono text-xs text-accent">{t.key}</span>
                      <span className="cmdk-item-title">{t.title}</span>
                    </div>
                    <span className={`pill pill-${t.status}`}>
                      {t.status.replace('_', ' ')}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>

          <div className="cmdk-footer">
            <span>Navigate with ↑ ↓ and ↵</span>
            <span>ESC to close</span>
          </div>
        </Command>
      </div>
    </div>
  );
}

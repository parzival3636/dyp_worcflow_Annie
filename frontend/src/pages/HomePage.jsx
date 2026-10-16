import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Plane, Send, Zap } from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import { apiGet } from '../hooks/useSnapshot';
import './HomePage.css';

export default function HomePage() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiGet('/projects')
      .then(data => {
        const list = Array.isArray(data) ? data : data?.projects || [];
        setRecentProjects(list.slice(0, 3));
      })
      .catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setError('');
    setLoading(true);
    try {
      await apiGet(`/projects/${code.trim()}`);
      navigate(`/p/${code.trim()}`);
    } catch (err) {
      if (err.status === 404) {
        setError('Project not found');
        setShaking(true);
        setTimeout(() => setShaking(false), 500);
      } else {
        setError('Cannot reach backend');
      }
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status) => {
    if (status === 'running') return 'pill-green';
    if (status === 'done') return 'pill-muted';
    return 'pill-blue';
  };

  return (
    <div className="homepage dot-grid-bg">
      <div className="homepage-content">
        {/* Hero */}
        <div className="homepage-hero">
          <div className="homepage-logo">
            <div className="homepage-logo-icon">
              <Plane size={28} />
            </div>
            <span className="homepage-logo-text">Pilot</span>
          </div>
          <p className="homepage-tagline">
            Other bots collect status updates. Ours checks them.
          </p>
        </div>

        {/* Entry card */}
        <div className={`homepage-card ${shaking ? 'animate-shake' : ''}`}>
          <form onSubmit={handleSubmit}>
            <label className="homepage-label">Enter project code</label>
            <input
              type="text"
              className="input input-mono homepage-input"
              placeholder="PILOT-XXXX"
              value={code}
              onChange={(e) => { setCode(e.target.value.toUpperCase()); setError(''); }}
              autoFocus
            />
            {error && <p className="homepage-error">{error}</p>}
            <button type="submit" className="btn btn-primary w-full homepage-submit" disabled={loading || !code.trim()}>
              {loading ? (
                <span className="homepage-spinner" />
              ) : (
                <>Open Project <ArrowRight size={16} /></>
              )}
            </button>
          </form>

          {recentProjects.length > 0 ? (
            <>
              <div className="homepage-divider">
                <span>or</span>
              </div>
              <div className="homepage-recent">
                <p className="homepage-label" style={{ marginBottom: 8 }}>Recent projects</p>
                {recentProjects.map(p => (
                  <button
                    key={p.code}
                    className="homepage-recent-item"
                    onClick={() => navigate(`/p/${p.code}`)}
                  >
                    <div className="flex-1">
                      <div className="font-medium text-base">{p.name || p.code}</div>
                      <div className="flex items-center gap-2" style={{ marginTop: 2 }}>
                        <span className="font-mono text-xs text-muted">{p.code}</span>
                        <span className={`pill ${statusColor(p.status)}`}>{p.status}</span>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-muted" />
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <button
                type="button"
                className="btn btn-secondary w-full"
                onClick={() => navigate('/p/demo01')}
                style={{ justifyContent: 'center' }}
              >
                <span>Explore Live Demo (demo01)</span>
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="homepage-footer">
          <span>Powered by</span>
          <span className="flex items-center gap-1"><Zap size={12} /> OpenCode</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Send size={12} /> Telegram</span>
          <span>·</span>
          <span className="flex items-center gap-1"><GithubIcon size={12} /> GitHub</span>
        </div>
      </div>
    </div>
  );
}

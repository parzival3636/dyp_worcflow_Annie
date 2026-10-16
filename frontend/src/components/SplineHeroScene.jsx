import React, { Suspense, lazy, useState, useEffect, useRef } from 'react';

// Lazy load Spline only if needed
const Spline = lazy(() => import('@splinetool/react-spline'));

export default function SplineHeroScene() {
  const splineUrl = import.meta.env.VITE_SPLINE_SCENE_URL;
  const [useFallback, setUseFallback] = useState(!splineUrl);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);
    const handler = (e) => setReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  if (splineUrl && !useFallback && !reducedMotion) {
    return (
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Suspense fallback={<ConstellationFallback />}>
          <Spline
            scene={splineUrl}
            onError={() => setUseFallback(true)}
            style={{ width: '100%', height: '100%' }}
          />
        </Suspense>
      </div>
    );
  }

  return <ConstellationFallback reducedMotion={reducedMotion} />;
}

// Fallback interactive constellation
function ConstellationFallback({ reducedMotion }) {
  const containerRef = useRef(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e) => {
    if (reducedMotion || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMousePos({ x, y });
  };

  const transformStyle = reducedMotion
    ? {}
    : {
        transform: `perspective(1000px) rotateY(${mousePos.x * 12}deg) rotateX(${-mousePos.y * 12}deg)`,
        transition: 'transform 180ms ease-out'
      };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      style={{
        width: '100%',
        height: '100%',
        minHeight: 380,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
          ...transformStyle
        }}
      >
        <svg width="100%" height="100%" viewBox="0 0 540 380" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="planeGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#FF6B3D" />
              <stop offset="100%" stopColor="#FF855F" />
            </linearGradient>
            <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glowRed" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Thin Constellation Gridlines */}
          <line x1="80" y1="120" x2="210" y2="90" stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="3 3" />
          <line x1="210" y1="90" x2="350" y2="140" stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="3 3" />
          <line x1="350" y1="140" x2="460" y2="80" stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="3 3" />
          <line x1="210" y1="90" x2="260" y2="240" stroke="var(--border-strong)" strokeWidth="1" />
          <line x1="260" y1="240" x2="380" y2="280" stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="3 3" />
          <line x1="350" y1="140" x2="380" y2="280" stroke="var(--border-strong)" strokeWidth="1" />

          {/* Animated Flight Path */}
          <path
            d="M 60 180 Q 180 60 260 240 T 480 120"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeDasharray="6 4"
            opacity="0.8"
          />

          {/* Verified Task Node 1 (Green) */}
          <circle cx="80" cy="120" r="10" fill="var(--surface)" stroke="var(--status-verified_done)" strokeWidth="2" filter="url(#glowGreen)" />
          <circle cx="80" cy="120" r="4" fill="var(--status-verified_done)" />
          <text x="70" y="145" fill="var(--text-secondary)" fontSize="10" fontWeight="600" fontFamily="Geist Mono">T-1 VERIFIED</text>

          {/* Verified Task Node 2 (Green) */}
          <circle cx="210" cy="90" r="9" fill="var(--surface)" stroke="var(--status-verified_done)" strokeWidth="2" filter="url(#glowGreen)" />
          <circle cx="210" cy="90" r="4" fill="var(--status-verified_done)" />
          <text x="200" y="75" fill="var(--text-secondary)" fontSize="10" fontWeight="600" fontFamily="Geist Mono">T-3</text>

          {/* Critical Blocked Task Node (Glowing Red Reroute target) */}
          <circle cx="260" cy="240" r="14" fill="var(--surface)" stroke="var(--status-blocked)" strokeWidth="2.5" filter="url(#glowRed)">
            <animate attributeName="r" values="12;16;12" dur="2s" repeatCount="indefinite" />
          </circle>
          <circle cx="260" cy="240" r="6" fill="var(--status-blocked)" />
          <text x="220" y="272" fill="var(--status-blocked)" fontSize="10" fontWeight="600" fontFamily="Geist Mono">
            T-2 BLOCKED (Rerouting)
          </text>

          {/* In Progress Task Node (Blue) */}
          <circle cx="350" cy="140" r="10" fill="var(--surface)" stroke="var(--status-in_progress)" strokeWidth="2" />
          <circle cx="350" cy="140" r="4" fill="var(--status-in_progress)" />
          <text x="365" y="145" fill="var(--text-secondary)" fontSize="10" fontWeight="600" fontFamily="Geist Mono">T-4</text>

          {/* Milestone Diamond (Demo) */}
          <rect x="450" y="70" width="18" height="18" fill="var(--accent)" transform="rotate(45 459 79)" stroke="#fff" strokeWidth="1.5" />
          <text x="440" y="108" fill="var(--accent)" fontSize="9" fontWeight="600" fontFamily="Geist Mono">
            MILESTONE T-5
          </text>

          {/* Stylized Pilot Aircraft / Paper Plane */}
          <g transform="translate(240, 195) rotate(-35)">
            <polygon points="0,-18 14,14 0,7 -14,14" fill="url(#planeGrad)" stroke="#FFFFFF" strokeWidth="1.5" />
            <polygon points="0,-18 0,7 14,14" fill="#FF855F" />
            <circle cx="0" cy="0" r="2" fill="#fff" />
          </g>
        </svg>

        {/* Backdrop Glow */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 320,
            height: 220,
            background: 'radial-gradient(circle, rgba(255, 107, 61, 0.08) 0%, transparent 70%)',
            pointerEvents: 'none',
            zIndex: -1
          }}
        />
      </div>
    </div>
  );
}

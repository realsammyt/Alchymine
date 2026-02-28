'use client';

import { useState, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────

interface SystemRecommendation {
  system: string;
  score: number;
  reason: string;
  entry_action: string;
  priority: number;
}

interface SpiralRouteResult {
  primary_system: string;
  recommendations: SystemRecommendation[];
  for_you_today: string;
  evidence_level: string;
  calculation_type: string;
  methodology: string;
}

// ── Constants ─────────────────────────────────────────────────────

const INTENTIONS = [
  { key: 'career', label: 'Career', icon: '💼' },
  { key: 'love', label: 'Love', icon: '❤️' },
  { key: 'purpose', label: 'Purpose', icon: '🧭' },
  { key: 'money', label: 'Money', icon: '💰' },
  { key: 'health', label: 'Health', icon: '🌿' },
  { key: 'family', label: 'Family', icon: '👨‍👩‍👧‍👦' },
  { key: 'business', label: 'Business', icon: '🚀' },
  { key: 'legacy', label: 'Legacy', icon: '🏛️' },
];

const SYSTEM_META: Record<string, { label: string; color: string; icon: string; path: string }> = {
  intelligence: { label: 'Personalized Intelligence', color: '#6366f1', icon: '🔮', path: '/intelligence' },
  healing: { label: 'Ethical Healing', color: '#10b981', icon: '🌱', path: '/healing' },
  wealth: { label: 'Generational Wealth', color: '#f59e0b', icon: '💎', path: '/wealth' },
  creative: { label: 'Creative Development', color: '#ec4899', icon: '🎨', path: '/creative' },
  perspective: { label: 'Perspective Enhancement', color: '#8b5cf6', icon: '🔭', path: '/perspective' },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Component ─────────────────────────────────────────────────────

export default function SpiralHub() {
  const [selectedIntention, setSelectedIntention] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<SpiralRouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getRoute = useCallback(async (intention: string) => {
    setSelectedIntention(intention);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/spiral/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SpiralRouteResult = await res.json();
      setRouteResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get routing');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          The Alchemical Spiral
        </h1>
        <p style={{ color: '#9ca3af', maxWidth: 520, margin: '0 auto' }}>
          Choose what matters most to you right now, and we'll guide you to the highest-leverage system for your growth.
        </p>
      </div>

      {/* Intention selection */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', color: '#9ca3af', textAlign: 'center', marginBottom: '1rem' }}>
          What&apos;s your primary intention?
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '0.75rem',
          }}
        >
          {INTENTIONS.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => getRoute(key)}
              style={{
                background: selectedIntention === key ? '#6366f133' : '#1e1e2e',
                border: selectedIntention === key ? '2px solid #6366f1' : '1px solid #333',
                borderRadius: 12,
                padding: '1rem',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s',
                color: '#e5e7eb',
              }}
            >
              <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>{icon}</div>
              <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
          Calculating your optimal path...
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ color: '#ef4444', background: '#1e1e2e', padding: '0.75rem 1rem', borderRadius: 8, marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Route results */}
      {routeResult && !loading && (
        <div>
          {/* For You Today */}
          <div
            style={{
              background: `linear-gradient(135deg, ${SYSTEM_META[routeResult.primary_system]?.color || '#6366f1'}22, #1e1e2e)`,
              borderRadius: 16,
              padding: '1.5rem',
              marginBottom: '1.5rem',
              border: `1px solid ${SYSTEM_META[routeResult.primary_system]?.color || '#6366f1'}44`,
            }}
          >
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>
              For You Today
            </h3>
            <p style={{ fontSize: '1.1rem', lineHeight: 1.6, color: '#e5e7eb' }}>
              {routeResult.for_you_today}
            </p>
          </div>

          {/* System rankings */}
          <h3 style={{ fontSize: '1rem', color: '#9ca3af', marginBottom: '1rem' }}>
            Your Systems, Ranked
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {routeResult.recommendations.map((rec) => {
              const meta = SYSTEM_META[rec.system];
              if (!meta) return null;
              const isPrimary = rec.priority === 1;
              return (
                <div
                  key={rec.system}
                  style={{
                    background: isPrimary ? `${meta.color}11` : '#1e1e2e',
                    borderRadius: 12,
                    padding: '1rem 1.25rem',
                    borderLeft: `4px solid ${meta.color}`,
                    border: isPrimary ? `2px solid ${meta.color}66` : undefined,
                    borderLeftWidth: 4,
                    borderLeftStyle: 'solid',
                    borderLeftColor: meta.color,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>{meta.icon}</span>
                      <span style={{ fontWeight: 600 }}>
                        {isPrimary && '★ '}
                        {meta.label}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {/* Score bar */}
                      <div style={{ width: 60, height: 6, background: '#374151', borderRadius: 3 }}>
                        <div
                          style={{
                            width: `${rec.score}%`,
                            height: '100%',
                            background: meta.color,
                            borderRadius: 3,
                          }}
                        />
                      </div>
                      <span style={{ fontSize: '0.75rem', color: '#9ca3af', minWidth: 32 }}>
                        {rec.score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <p style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                    {rec.reason}
                  </p>
                  <a
                    href={meta.path}
                    style={{
                      display: 'inline-block',
                      fontSize: '0.8rem',
                      color: meta.color,
                      textDecoration: 'none',
                      fontWeight: 500,
                    }}
                  >
                    {rec.entry_action} →
                  </a>
                </div>
              );
            })}
          </div>

          {/* Methodology */}
          <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#111827', borderRadius: 8, fontSize: '0.75rem', color: '#6b7280' }}>
            <strong>Methodology:</strong> {routeResult.methodology}
            <br />
            <span>Evidence: {routeResult.evidence_level} | Calculation: {routeResult.calculation_type}</span>
          </div>
        </div>
      )}
    </div>
  );
}

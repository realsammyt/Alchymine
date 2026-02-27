'use client';

import { useState } from 'react';
import Link from 'next/link';
import Button from '@/components/shared/Button';
import Card from '@/components/shared/Card';
import ProgressBar from '@/components/shared/ProgressBar';

const WEALTH_LEVERS = [
  {
    name: 'EARN',
    icon: '💼',
    description: 'Optimize active and passive income streams',
    color: 'gold' as const,
    examples: ['Salary negotiation', 'Side income', 'Freelancing', 'Content monetization'],
  },
  {
    name: 'KEEP',
    icon: '🛡️',
    description: 'Reduce expenses and protect against wealth erosion',
    color: 'teal' as const,
    examples: ['Tax optimization', 'Expense audit', 'Insurance review', 'Debt management'],
  },
  {
    name: 'GROW',
    icon: '📈',
    description: 'Invest and compound your wealth over time',
    color: 'gold' as const,
    examples: ['Index investing', 'Real estate', 'Business equity', 'Skill investment'],
  },
  {
    name: 'PROTECT',
    icon: '🏰',
    description: 'Safeguard wealth from risks and unexpected events',
    color: 'purple' as const,
    examples: ['Emergency fund', 'Estate planning', 'Asset protection', 'Insurance'],
  },
  {
    name: 'TRANSFER',
    icon: '🤝',
    description: 'Build and share generational wealth',
    color: 'teal' as const,
    examples: ['Trust structures', 'Education funds', 'Family governance', 'Charitable giving'],
  },
];

const WEALTH_ARCHETYPES_PREVIEW = [
  { name: 'The Builder', description: 'Systematic wealth accumulation through structure and discipline', icon: '🏗️' },
  { name: 'The Innovator', description: 'Creative wealth generation through new ideas and ventures', icon: '💡' },
  { name: 'The Sage Investor', description: 'Evidence-based wealth growth through deep research', icon: '📚' },
  { name: 'The Connector', description: 'Relationship-driven wealth through networks and community', icon: '🤝' },
  { name: 'The Warrior', description: 'Ambitious wealth building through decisive action', icon: '⚔️' },
  { name: 'The Mystic Trader', description: 'Intuition-guided wealth with impact investing focus', icon: '🔮' },
];

export default function WealthPage() {
  const [selectedLever, setSelectedLever] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-white/5 bg-surface/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-gradient-gold font-bold text-xl">
            Alchymine
          </Link>
          <span className="text-text/50 text-sm">Wealth Engine</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-gradient-gold mb-4">
            Wealth Engine
          </h1>
          <p className="text-text/60 text-lg max-w-2xl mx-auto">
            Six-domain generational wealth strategy. All calculations are deterministic —
            no AI guesswork with your finances.
          </p>
          <div className="mt-4 inline-block bg-surface/50 border border-primary/20 rounded-full px-4 py-2">
            <span className="text-xs text-text/40">
              Not financial advice. All strategies require professional review.
            </span>
          </div>
        </div>

        {/* Five Wealth Levers */}
        <h2 className="text-2xl font-bold mb-6">Five Wealth Levers</h2>
        <div className="grid md:grid-cols-5 gap-4 mb-12">
          {WEALTH_LEVERS.map((lever) => (
            <div
              key={lever.name}
              onClick={() => setSelectedLever(selectedLever === lever.name ? null : lever.name)}
              className={`card-surface p-4 cursor-pointer transition-all ${
                selectedLever === lever.name ? 'glow-gold ring-1 ring-primary/30' : 'hover:glow-gold'
              }`}
            >
              <div className="text-3xl mb-2">{lever.icon}</div>
              <h3 className="font-bold text-sm mb-1">{lever.name}</h3>
              <p className="text-text/40 text-xs">{lever.description}</p>
            </div>
          ))}
        </div>

        {/* Selected Lever Detail */}
        {selectedLever && (
          <div className="card-surface p-6 mb-12">
            <h3 className="text-xl font-bold text-primary mb-4">
              {WEALTH_LEVERS.find((l) => l.name === selectedLever)?.icon}{' '}
              {selectedLever} Strategies
            </h3>
            <div className="grid sm:grid-cols-2 gap-3">
              {WEALTH_LEVERS.find((l) => l.name === selectedLever)?.examples.map((ex) => (
                <div key={ex} className="flex items-center gap-2 text-text/70 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                  {ex}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Wealth Archetypes Preview */}
        <h2 className="text-2xl font-bold mb-6">Wealth Archetypes</h2>
        <p className="text-text/50 mb-6">
          Your wealth archetype is derived from your numerology Life Path and Jungian archetype.
          Complete your profile to discover yours.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {WEALTH_ARCHETYPES_PREVIEW.map((archetype) => (
            <div key={archetype.name} className="card-surface p-4">
              <div className="text-2xl mb-2">{archetype.icon}</div>
              <h3 className="font-semibold text-sm text-primary">{archetype.name}</h3>
              <p className="text-text/40 text-xs mt-1">{archetype.description}</p>
            </div>
          ))}
        </div>

        {/* 90-Day Plan Preview */}
        <Card
          title="90-Day Activation Plan"
          subtitle="Your personalized wealth-building roadmap"
          badge="Phase 2"
        >
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-text/60">Phase 1: Foundation (Days 1-30)</span>
                <span className="text-primary">EARN</span>
              </div>
              <ProgressBar value={100} color="gold" size="sm" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-text/60">Phase 2: Building (Days 31-60)</span>
                <span className="text-secondary">KEEP</span>
              </div>
              <ProgressBar value={60} color="purple" size="sm" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-text/60">Phase 3: Acceleration (Days 61-90)</span>
                <span className="text-accent">GROW</span>
              </div>
              <ProgressBar value={20} color="teal" size="sm" />
            </div>
          </div>
        </Card>

        {/* CTA */}
        <div className="text-center mt-12">
          <Link href="/discover/intake">
            <Button variant="primary" size="lg">
              Discover Your Wealth Archetype
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}

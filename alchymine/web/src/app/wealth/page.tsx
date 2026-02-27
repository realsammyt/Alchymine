'use client';

import { useState } from 'react';
import Link from 'next/link';
import Button from '@/components/shared/Button';
import Card from '@/components/shared/Card';
import ProgressBar from '@/components/shared/ProgressBar';
import MethodologyPanel from '@/components/shared/MethodologyPanel';

const WEALTH_LEVERS = [
  {
    name: 'EARN',
    icon: '\u{1F4BC}',
    description: 'Optimize active and passive income streams',
    color: 'gold' as const,
    examples: ['Salary negotiation', 'Side income', 'Freelancing', 'Content monetization'],
  },
  {
    name: 'KEEP',
    icon: '\u{1F6E1}\u{FE0F}',
    description: 'Reduce expenses and protect against wealth erosion',
    color: 'teal' as const,
    examples: ['Tax optimization', 'Expense audit', 'Insurance review', 'Debt management'],
  },
  {
    name: 'GROW',
    icon: '\u{1F4C8}',
    description: 'Invest and compound your wealth over time',
    color: 'gold' as const,
    examples: ['Index investing', 'Real estate', 'Business equity', 'Skill investment'],
  },
  {
    name: 'PROTECT',
    icon: '\u{1F3F0}',
    description: 'Safeguard wealth from risks and unexpected events',
    color: 'purple' as const,
    examples: ['Emergency fund', 'Estate planning', 'Asset protection', 'Insurance'],
  },
  {
    name: 'TRANSFER',
    icon: '\u{1F91D}',
    description: 'Build and share generational wealth',
    color: 'teal' as const,
    examples: ['Trust structures', 'Education funds', 'Family governance', 'Charitable giving'],
  },
];

const WEALTH_ARCHETYPES_PREVIEW = [
  { name: 'The Builder', description: 'Systematic wealth accumulation through structure and discipline', icon: '\u{1F3D7}\u{FE0F}' },
  { name: 'The Innovator', description: 'Creative wealth generation through new ideas and ventures', icon: '\u{1F4A1}' },
  { name: 'The Sage Investor', description: 'Evidence-based wealth growth through deep research', icon: '\u{1F4DA}' },
  { name: 'The Connector', description: 'Relationship-driven wealth through networks and community', icon: '\u{1F91D}' },
  { name: 'The Warrior', description: 'Ambitious wealth building through decisive action', icon: '\u{2694}\u{FE0F}' },
  { name: 'The Mystic Trader', description: 'Intuition-guided wealth with impact investing focus', icon: '\u{1F52E}' },
];

export default function WealthPage() {
  const [selectedLever, setSelectedLever] = useState<string | null>(null);

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Generational Wealth</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Five-lever generational wealth strategy. All calculations are deterministic —
            no AI guesswork with your finances.
          </p>
          <div className="mt-4 inline-block bg-surface/50 border border-primary/20 rounded-full px-4 py-2">
            <span className="text-xs text-text/40">
              Not financial advice. All strategies require professional review.
            </span>
          </div>
        </header>

        {/* Five Wealth Levers */}
        <section className="mb-12" aria-labelledby="levers-heading">
          <h2 id="levers-heading" className="text-2xl font-bold mb-6">Five Wealth Levers</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            {WEALTH_LEVERS.map((lever) => (
              <button
                key={lever.name}
                onClick={() => setSelectedLever(selectedLever === lever.name ? null : lever.name)}
                aria-pressed={selectedLever === lever.name}
                className={`card-surface p-4 text-left transition-all ${
                  selectedLever === lever.name ? 'glow-gold ring-1 ring-primary/30' : 'hover:glow-gold'
                }`}
              >
                <div className="text-3xl mb-2" aria-hidden="true">{lever.icon}</div>
                <h3 className="font-bold text-sm mb-1">{lever.name}</h3>
                <p className="text-text/40 text-xs">{lever.description}</p>
              </button>
            ))}
          </div>

          {/* Selected Lever Detail */}
          {selectedLever && (
            <div className="card-surface p-6 mb-6 animate-fade-in">
              <h3 className="text-xl font-bold text-primary mb-4">
                {WEALTH_LEVERS.find((l) => l.name === selectedLever)?.icon}{' '}
                {selectedLever} Strategies
              </h3>
              <div className="grid sm:grid-cols-2 gap-3">
                {WEALTH_LEVERS.find((l) => l.name === selectedLever)?.examples.map((ex) => (
                  <div key={ex} className="flex items-center gap-2 text-text/70 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary" aria-hidden="true" />
                    {ex}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Wealth Archetypes Preview */}
        <section className="mb-12" aria-labelledby="archetypes-heading">
          <h2 id="archetypes-heading" className="text-2xl font-bold mb-3">Wealth Archetypes</h2>
          <p className="text-text/50 mb-6 text-sm">
            Your wealth archetype is derived from your numerology Life Path and Jungian archetype.
            Complete your profile to discover yours.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {WEALTH_ARCHETYPES_PREVIEW.map((archetype) => (
              <div key={archetype.name} className="card-surface p-4">
                <div className="text-2xl mb-2" aria-hidden="true">{archetype.icon}</div>
                <h3 className="font-semibold text-sm text-primary">{archetype.name}</h3>
                <p className="text-text/40 text-xs mt-1">{archetype.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Debt Payoff Section */}
        <section className="mb-12" aria-labelledby="debt-heading">
          <h2 id="debt-heading" className="text-2xl font-bold mb-6">Debt Payoff Calculator</h2>
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
                <ProgressBar value={100} variant="gold" size="sm" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text/60">Phase 2: Building (Days 31-60)</span>
                  <span className="text-secondary">KEEP</span>
                </div>
                <ProgressBar value={60} variant="purple" size="sm" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text/60">Phase 3: Acceleration (Days 61-90)</span>
                  <span className="text-accent">GROW</span>
                </div>
                <ProgressBar value={20} variant="teal" size="sm" />
              </div>
            </div>
          </Card>
        </section>

        {/* Methodology Panel */}
        <section className="mb-12">
          <MethodologyPanel
            title="Wealth Engine"
            methodology="All financial calculations in the Wealth Engine use deterministic mathematical formulas. Debt payoff uses the avalanche method (highest interest first) or snowball method (lowest balance first) with standard amortization formulas. Compound growth projections use the formula A = P(1 + r/n)^(nt). Wealth archetype mapping is derived from numerology Life Path numbers cross-referenced with Jungian archetype theory. No financial data is ever sent to an LLM."
            evidenceLevel="strong"
            calculationType="deterministic"
            sources={[
              'Standard amortization and compound interest formulas (mathematical constants)',
              'Avalanche vs. Snowball debt payoff methods - Gathergood (2012) \"Self-control, financial literacy and consumer over-indebtedness\"',
              'Five Wealth Levers framework adapted from Kiyosaki, Ramsey, and Sethi personal finance methodologies',
              'Financial data classification: Sensitive (encrypted, isolated, never sent to LLM) per ADR-002',
            ]}
          />
        </section>

        {/* CTA */}
        <div className="text-center">
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

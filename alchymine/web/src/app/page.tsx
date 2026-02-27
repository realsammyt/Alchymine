import Link from 'next/link';

const SYSTEMS = [
  {
    name: 'Identity',
    icon: '🪞',
    description:
      'Numerology, astrology, archetypes, and personality mapping — the foundation of who you are.',
    color: 'from-primary-dark to-primary',
  },
  {
    name: 'Healing',
    icon: '🌿',
    description:
      'Personalized modalities for emotional and somatic healing, matched to your unique profile.',
    color: 'from-accent-dark to-accent',
  },
  {
    name: 'Wealth',
    icon: '💰',
    description:
      'Deterministic financial strategies across five wealth levers: Earn, Keep, Grow, Protect, Transfer.',
    color: 'from-primary-dark to-primary',
  },
  {
    name: 'Creative',
    icon: '🎨',
    description:
      'Guilford-based creative assessment, your Creative DNA, and tools for sustained creative output.',
    color: 'from-secondary-dark to-secondary',
  },
  {
    name: 'Perspective',
    icon: '🔭',
    description:
      'Kegan stages, mental models, cognitive reframing, and strategic clarity for how you see the world.',
    color: 'from-accent-dark to-accent',
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center min-h-screen px-6 overflow-hidden">
        {/* Background gradient effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-bg via-bg to-surface/30" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-secondary/5 blur-[100px]" />

        <div className="relative z-10 max-w-4xl mx-auto text-center">
          {/* Alchymine wordmark */}
          <p className="text-sm uppercase tracking-[0.3em] text-primary mb-6 animate-fade-in">
            Personal Transformation Operating System
          </p>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold mb-6 animate-fade-in">
            Discover Who You{' '}
            <span className="text-gradient-gold">Truly Are</span>
          </h1>

          {/* Subtext */}
          <p className="text-lg sm:text-xl text-text/70 max-w-2xl mx-auto mb-10 animate-slide-up">
            Five integrated systems — Identity, Healing, Wealth, Creative, and
            Perspective — powered by deterministic engines and ethical AI to
            guide your personal transformation.
          </p>

          {/* CTA */}
          <div className="animate-slide-up animation-delay-200">
            <Link
              href="/discover/intake"
              className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-primary-dark to-primary text-bg font-semibold rounded-xl text-lg transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.3)] hover:scale-105 active:scale-100"
            >
              Begin Your Journey
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-text/30"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
      </section>

      {/* Five Systems Overview */}
      <section className="relative px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Five Systems,{' '}
              <span className="text-gradient-gold">One Profile</span>
            </h2>
            <p className="text-text/60 max-w-xl mx-auto">
              Each system contributes a unique layer to your unified profile,
              building a complete map of who you are and who you are becoming.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {SYSTEMS.map((system, index) => (
              <div
                key={system.name}
                className={`card-surface p-6 transition-all duration-300 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5 ${
                  index === 4 ? 'sm:col-span-2 lg:col-span-1' : ''
                }`}
              >
                <div className="text-3xl mb-4">{system.icon}</div>
                <h3 className="text-xl font-semibold mb-2">
                  <span
                    className={`bg-gradient-to-r ${system.color} bg-clip-text text-transparent`}
                  >
                    {system.name}
                  </span>
                </h3>
                <p className="text-text/60 text-sm leading-relaxed">
                  {system.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="relative px-6 py-24 bg-surface/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-12">
            How It <span className="text-gradient-gold">Works</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              {
                step: '01',
                title: 'Intake',
                desc: 'Share your name, birth date, and intention.',
              },
              {
                step: '02',
                title: 'Assessment',
                desc: '27 questions across personality, attachment, and risk.',
              },
              {
                step: '03',
                title: 'Generation',
                desc: 'Deterministic engines calculate your profile.',
              },
              {
                step: '04',
                title: 'Report',
                desc: 'Explore your multi-system identity profile.',
              },
            ].map((item) => (
              <div key={item.step} className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-primary-dark to-primary flex items-center justify-center text-bg font-bold text-sm mb-4">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                <p className="text-text/60 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-12">
            <Link
              href="/discover/intake"
              className="inline-flex items-center gap-2 px-6 py-3 border border-primary/30 text-primary font-medium rounded-xl transition-all duration-300 hover:bg-primary/10 hover:border-primary/50"
            >
              Start Discovery
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-text/40">
            Alchymine — Open Source, Ethics First
          </div>
          <div className="text-sm text-text/40">
            Licensed under CC-BY-NC-SA 4.0
          </div>
        </div>
      </footer>
    </main>
  );
}

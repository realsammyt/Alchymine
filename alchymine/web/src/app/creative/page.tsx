import MethodologyPanel from '@/components/shared/MethodologyPanel';

const CREATIVE_DIMENSIONS = [
  {
    name: 'Divergent Thinking',
    description: 'Ability to generate multiple ideas, explore possibilities, and make unexpected connections.',
    traits: ['Fluency', 'Flexibility', 'Originality', 'Elaboration'],
  },
  {
    name: 'Convergent Thinking',
    description: 'Ability to evaluate ideas, find optimal solutions, and refine concepts into actionable plans.',
    traits: ['Analysis', 'Synthesis', 'Evaluation', 'Decision-making'],
  },
  {
    name: 'Creative Temperament',
    description: 'Personality traits that support creative expression, including openness, tolerance for ambiguity, and intrinsic motivation.',
    traits: ['Openness', 'Persistence', 'Risk tolerance', 'Curiosity'],
  },
];

const STYLE_PROFILES = [
  {
    name: 'The Architect',
    description: 'Structured creativity through careful planning, systems design, and methodical execution.',
    icon: '\u{1F3DB}\u{FE0F}',
  },
  {
    name: 'The Explorer',
    description: 'Creativity through experimentation, boundary-pushing, and embracing the unknown.',
    icon: '\u{1F9ED}',
  },
  {
    name: 'The Connector',
    description: 'Creativity through synthesizing ideas from different domains and building bridges between concepts.',
    icon: '\u{1F517}',
  },
  {
    name: 'The Alchemist',
    description: 'Creativity through transformation, taking raw materials and transmuting them into something entirely new.',
    icon: '\u{2697}\u{FE0F}',
  },
];

const PROJECT_TYPES = [
  {
    name: 'Solo Projects',
    description: 'Individual creative works matched to your style profile and strengths.',
    status: 'available',
  },
  {
    name: 'Collaborative Works',
    description: 'Team projects that pair complementary creative styles for maximum output.',
    status: 'coming-soon',
  },
  {
    name: 'Creative Challenges',
    description: 'Time-boxed prompts and constraints designed to stretch your creative abilities.',
    status: 'coming-soon',
  },
];

export default function CreativePage() {
  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Creative Development</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Guilford-based creative assessment to discover your Creative DNA,
            style profile, and tools for sustained creative output.
          </p>
        </header>

        {/* Creative Assessment Section */}
        <section className="mb-12" aria-labelledby="assessment-heading">
          <h2 id="assessment-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F9EA}'}
            </span>
            Creative Assessment
          </h2>
          <p className="text-text/50 text-sm mb-6">
            The assessment measures three dimensions of creativity based on J.P. Guilford&apos;s
            Structure of Intellect model. Each dimension reveals different aspects of your
            creative potential.
          </p>

          <div className="grid sm:grid-cols-3 gap-4 mb-4">
            {CREATIVE_DIMENSIONS.map((dimension) => (
              <div key={dimension.name} className="card-surface p-5">
                <h3 className="text-sm font-semibold text-secondary mb-2">{dimension.name}</h3>
                <p className="text-sm text-text/50 leading-relaxed mb-3">{dimension.description}</p>
                <div className="flex flex-wrap gap-1.5">
                  {dimension.traits.map((trait) => (
                    <span
                      key={trait}
                      className="px-2 py-0.5 bg-secondary/10 text-secondary/70 text-[10px] font-medium rounded-full"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <MethodologyPanel
            title="Creative Assessment"
            methodology="The creative assessment is based on J.P. Guilford's Structure of Intellect (SOI) model, specifically the divergent production operations. Assessment items measure fluency (quantity of ideas), flexibility (category shifts), originality (statistical rarity of responses), and elaboration (detail and development). Scoring uses normative data from published creativity research. The Creative DNA profile synthesizes assessment results with personality data (Big Five Openness) from the Intelligence system."
            evidenceLevel="strong"
            calculationType="hybrid"
            sources={[
              'Guilford, J.P. (1967) \"The Nature of Human Intelligence\" - foundational creativity model',
              'Torrance, E.P. (1974) \"Torrance Tests of Creative Thinking\" - validated assessment methodology',
              'Runco, M.A. & Acar, S. (2012) \"Divergent Thinking as an Indicator of Creative Potential\" - meta-analysis',
              'Big Five Openness to Experience as creativity predictor - Kaufman et al. (2016)',
            ]}
          />
        </section>

        {/* Style Profile Section */}
        <section className="mb-12" aria-labelledby="style-heading">
          <h2 id="style-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F3A8}'}
            </span>
            Creative Style Profiles
          </h2>
          <p className="text-text/50 text-sm mb-6">
            Your creative style profile is derived from your assessment results,
            personality data, and preferred modes of expression.
          </p>

          <div className="grid sm:grid-cols-2 gap-4">
            {STYLE_PROFILES.map((profile) => (
              <div key={profile.name} className="card-surface p-5">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl" aria-hidden="true">{profile.icon}</span>
                  <h3 className="text-sm font-semibold text-primary">{profile.name}</h3>
                </div>
                <p className="text-sm text-text/50 leading-relaxed">{profile.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Projects & Collaboration Section */}
        <section className="mb-12" aria-labelledby="projects-heading">
          <h2 id="projects-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F4DD}'}
            </span>
            Projects & Collaboration
          </h2>

          <div className="grid sm:grid-cols-3 gap-4">
            {PROJECT_TYPES.map((project) => (
              <div
                key={project.name}
                className={`card-surface p-5 ${project.status === 'coming-soon' ? 'opacity-60' : ''}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-text">{project.name}</h3>
                  {project.status === 'coming-soon' && (
                    <span className="px-2 py-0.5 bg-secondary/10 text-secondary/60 text-[10px] font-medium rounded-full">
                      Coming Soon
                    </span>
                  )}
                </div>
                <p className="text-sm text-text/50 leading-relaxed">{project.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <a
            href="/discover/intake"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-secondary-dark to-secondary text-white font-semibold rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-100"
          >
            Discover Your Creative DNA
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12h14" />
              <path d="m12 5 7 7-7 7" />
            </svg>
          </a>
        </div>
      </div>
    </main>
  );
}

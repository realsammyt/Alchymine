import MethodologyPanel from '@/components/shared/MethodologyPanel';

const KEGAN_STAGES = [
  {
    stage: 2,
    name: 'Imperial Mind',
    description: 'Self-focused perspective. Needs and interests drive decision-making. Relationships are transactional.',
    focus: 'Personal advantage and concrete reciprocity',
  },
  {
    stage: 3,
    name: 'Socialized Mind',
    description: 'Defined by relationships and social roles. Values loyalty and belonging. Seeks external validation.',
    focus: 'Social acceptance and shared norms',
  },
  {
    stage: 4,
    name: 'Self-Authoring Mind',
    description: 'Self-directed perspective. Creates own value system. Can evaluate and manage relationships from a personal framework.',
    focus: 'Internal standards and self-authored identity',
  },
  {
    stage: 5,
    name: 'Self-Transforming Mind',
    description: 'Holds multiple frameworks simultaneously. Sees limitations of any single system. Embraces paradox and complexity.',
    focus: 'Interconnection and dialectical thinking',
  },
];

const COGNITIVE_BIASES = [
  {
    name: 'Confirmation Bias',
    description: 'Tendency to seek and interpret information that confirms existing beliefs.',
    mitigation: 'Actively seek disconfirming evidence. Practice steel-manning opposing views.',
    category: 'Information Processing',
  },
  {
    name: 'Anchoring Effect',
    description: 'Over-reliance on the first piece of information encountered when making decisions.',
    mitigation: 'Generate multiple reference points. Consider the decision from different starting conditions.',
    category: 'Decision Making',
  },
  {
    name: 'Availability Heuristic',
    description: 'Judging probability based on how easily examples come to mind rather than actual frequency.',
    mitigation: 'Check base rates. Consult data rather than relying on memorable anecdotes.',
    category: 'Probability Assessment',
  },
  {
    name: 'Sunk Cost Fallacy',
    description: 'Continuing to invest in something because of previously invested resources, not future value.',
    mitigation: 'Evaluate decisions based only on future costs and benefits. Practice the "fresh start" reframe.',
    category: 'Decision Making',
  },
  {
    name: 'Dunning-Kruger Effect',
    description: 'Overestimating competence in areas of low expertise while underestimating it in areas of high expertise.',
    mitigation: 'Seek calibrated feedback. Compare self-assessment with objective measures.',
    category: 'Self-Assessment',
  },
  {
    name: 'Framing Effect',
    description: 'Different conclusions from the same information depending on how it is presented.',
    mitigation: 'Restate the problem in multiple frames. Ask: "How would I see this if presented differently?"',
    category: 'Information Processing',
  },
];

const SCENARIO_TYPES = [
  {
    name: 'Pre-Mortem Analysis',
    description: 'Imagine a decision has failed. Work backward to identify what went wrong and how to prevent it.',
    icon: '\u{1F50D}',
  },
  {
    name: 'Best/Worst/Most Likely',
    description: 'Map three scenarios for any decision to calibrate expectations and prepare contingencies.',
    icon: '\u{1F4CA}',
  },
  {
    name: 'Second-Order Effects',
    description: 'Trace the consequences of consequences. What happens after the immediate outcome?',
    icon: '\u{1F300}',
  },
  {
    name: 'Inversion Thinking',
    description: 'Instead of asking how to succeed, ask what would guarantee failure — then avoid those things.',
    icon: '\u{1F504}',
  },
];

export default function PerspectivePage() {
  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Perspective Enhancement</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Kegan developmental stages, cognitive bias awareness, mental models,
            and scenario planning tools for how you see the world.
          </p>
        </header>

        {/* Developmental Frameworks Section */}
        <section className="mb-12" aria-labelledby="frameworks-heading">
          <h2 id="frameworks-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F4D0}'}
            </span>
            Developmental Frameworks
          </h2>
          <p className="text-text/50 text-sm mb-6">
            Robert Kegan&apos;s constructive-developmental theory maps how adults make
            meaning of their experiences. Each stage represents a qualitatively different
            way of understanding self and world.
          </p>

          <div className="space-y-4 mb-4">
            {KEGAN_STAGES.map((stage) => (
              <div key={stage.stage} className="card-surface p-5">
                <div className="flex items-center gap-3 mb-2">
                  <span className="w-8 h-8 rounded-full bg-accent/10 text-accent text-sm font-bold flex items-center justify-center flex-shrink-0">
                    {stage.stage}
                  </span>
                  <h3 className="text-sm font-semibold text-text">{stage.name}</h3>
                </div>
                <p className="text-sm text-text/50 leading-relaxed mb-2 ml-11">{stage.description}</p>
                <p className="text-xs text-text/30 ml-11">
                  <span className="font-medium text-text/40">Focus:</span> {stage.focus}
                </p>
              </div>
            ))}
          </div>

          <MethodologyPanel
            title="Developmental Frameworks"
            methodology="Kegan's constructive-developmental theory describes five stages of adult meaning-making, from the Impulsive Mind (Stage 1) through the Self-Transforming Mind (Stage 5). Stage assessment uses the Subject-Object Interview (SOI) methodology adapted into a structured questionnaire format. The assessment identifies your current center of gravity and growing edge. AI-assisted interpretation synthesizes responses into a developmental profile while respecting the complexity of stage transitions."
            evidenceLevel="strong"
            calculationType="ai-assisted"
            sources={[
              'Kegan, R. (1982) \"The Evolving Self\" - foundational developmental theory',
              'Kegan, R. (1994) \"In Over Our Heads\" - application to modern life complexity',
              'Lahey et al. (2011) Subject-Object Interview scoring manual and reliability studies',
              'Cook-Greuter, S. (2013) \"Nine Levels of Increasing Embrace\" - complementary ego development model',
            ]}
          />
        </section>

        {/* Cognitive Biases Section */}
        <section className="mb-12" aria-labelledby="biases-heading">
          <h2 id="biases-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F9E0}'}
            </span>
            Cognitive Bias Awareness
          </h2>
          <p className="text-text/50 text-sm mb-6">
            Understanding your cognitive biases is the first step toward clearer thinking.
            Each bias includes a practical mitigation strategy.
          </p>

          <div className="grid sm:grid-cols-2 gap-4">
            {COGNITIVE_BIASES.map((bias) => (
              <div key={bias.name} className="card-surface p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-primary">{bias.name}</h3>
                  <span className="px-2 py-0.5 bg-white/5 text-text/30 text-[10px] font-medium rounded-full">
                    {bias.category}
                  </span>
                </div>
                <p className="text-sm text-text/50 leading-relaxed mb-3">{bias.description}</p>
                <div className="bg-bg/50 rounded-lg px-3 py-2">
                  <p className="text-xs text-accent/70">
                    <span className="font-medium">Mitigation:</span> {bias.mitigation}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Scenario Planning Section */}
        <section className="mb-12" aria-labelledby="scenarios-heading">
          <h2 id="scenarios-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl" aria-hidden="true">
              {'\u{1F52D}'}
            </span>
            Scenario Planning
          </h2>
          <p className="text-text/50 text-sm mb-6">
            Mental models and scenario planning tools to help you think through
            decisions with greater clarity and fewer blind spots.
          </p>

          <div className="grid sm:grid-cols-2 gap-4">
            {SCENARIO_TYPES.map((scenario) => (
              <div key={scenario.name} className="card-surface p-5">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl" aria-hidden="true">{scenario.icon}</span>
                  <h3 className="text-sm font-semibold text-text">{scenario.name}</h3>
                </div>
                <p className="text-sm text-text/50 leading-relaxed">{scenario.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <a
            href="/discover/intake"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-accent-dark to-accent text-bg font-semibold rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(32,178,170,0.3)] hover:scale-[1.02] active:scale-100"
          >
            Map Your Perspective
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

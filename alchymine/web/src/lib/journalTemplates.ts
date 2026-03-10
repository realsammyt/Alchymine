export type AlchymineSystem =
  | "intelligence"
  | "healing"
  | "wealth"
  | "creative"
  | "perspective";

export interface JournalTemplate {
  id: string;
  system: AlchymineSystem;
  entryType: string;
  title: string;
  promptQuestions: string[];
  tags: string[];
  label: string;
  description: string;
}

export const JOURNAL_TEMPLATES: JournalTemplate[] = [
  // ── Perspective ────────────────────────────────────────────────────
  {
    id: "perspective-decision-matrix",
    system: "perspective",
    entryType: "decision",
    title: "Decision Matrix Reflection",
    promptQuestions: [
      "What decision did you evaluate using the weighted matrix?",
      "Which option ranked highest, and does that feel right?",
      "What criteria shifted the outcome the most?",
      "How confident are you in this decision now?",
    ],
    tags: ["decision", "framework", "perspective"],
    label: "Decision Matrix Reflection",
    description: "Reflect on a decision you analyzed with the weighted matrix.",
  },
  {
    id: "perspective-six-hats",
    system: "perspective",
    entryType: "reflection",
    title: "Six Thinking Hats Synthesis",
    promptQuestions: [
      "Which thinking hat was easiest for you to wear? Why?",
      "Which hat challenged you the most?",
      "What emerged when you synthesized all six perspectives?",
      "What action will you take based on this analysis?",
    ],
    tags: ["six-hats", "thinking", "perspective"],
    label: "Six Thinking Hats Synthesis",
    description:
      "Synthesize insights from exploring a problem through six perspectives.",
  },
  {
    id: "perspective-bias-discovery",
    system: "perspective",
    entryType: "insight",
    title: "Cognitive Bias Discovery",
    promptQuestions: [
      "What cognitive bias did the analysis detect in your reasoning?",
      "Can you recall a past decision where this bias may have influenced you?",
      "How does the suggested reframe change your perspective?",
      "What will you watch for going forward?",
    ],
    tags: ["bias", "awareness", "perspective"],
    label: "Cognitive Bias Discovery",
    description:
      "Explore a cognitive bias pattern discovered in your thinking.",
  },
  {
    id: "perspective-scenario-planning",
    system: "perspective",
    entryType: "decision",
    title: "Scenario Planning Narrative",
    promptQuestions: [
      "What decision or situation did you model scenarios for?",
      "What does the most likely scenario look like for you?",
      "Which risk variables matter most, and can you influence them?",
      "What early warning signs should you watch for?",
    ],
    tags: ["scenarios", "planning", "perspective"],
    label: "Scenario Planning Narrative",
    description: "Capture your scenario planning analysis and key takeaways.",
  },
  {
    id: "perspective-kegan-growth",
    system: "perspective",
    entryType: "assessment",
    title: "Kegan Growth Edge",
    promptQuestions: [
      "What developmental stage were you assessed at? Does it feel accurate?",
      "What growth edge resonates most with where you are right now?",
      "Can you recall a recent moment where you operated from this stage?",
      "Which growth practice will you commit to trying this week?",
    ],
    tags: ["kegan", "development", "growth"],
    label: "Kegan Growth Edge",
    description: "Reflect on your developmental stage and growth edges.",
  },

  // ── Wealth ─────────────────────────────────────────────────────────
  {
    id: "wealth-archetype-discovery",
    system: "wealth",
    entryType: "assessment",
    title: "Wealth Archetype Discovery",
    promptQuestions: [
      "What wealth archetype were you matched with? Does it resonate?",
      "What blind spot surprised you most about your archetype?",
      "How does your natural archetype align or conflict with your financial goals?",
      "Which recommended action will you take first, and why?",
    ],
    tags: ["archetype", "wealth", "identity"],
    label: "Archetype Discovery",
    description: "Reflect on your wealth archetype and its insights.",
  },
  {
    id: "wealth-lever-commitment",
    system: "wealth",
    entryType: "intention",
    title: "Wealth Lever Commitment",
    promptQuestions: [
      "Which wealth lever (Earn, Keep, Grow, Protect, Transfer) is your top priority right now?",
      "Why does this lever matter most at this point in your life?",
      "What tension exists between your current priority and where you want to be?",
      "What one action will you take this week to strengthen this lever?",
    ],
    tags: ["levers", "commitment", "wealth"],
    label: "Wealth Lever Commitment",
    description: "Set intentions around your prioritized wealth levers.",
  },
  {
    id: "wealth-90day-reflection",
    system: "wealth",
    entryType: "progress",
    title: "90-Day Phase Reflection",
    promptQuestions: [
      "Which phase of your 90-day plan did you just complete?",
      "What daily habits worked well? Which ones didn't stick?",
      "What unexpected obstacles did you encounter?",
      "What financial wins, however small, can you celebrate?",
    ],
    tags: ["90-day", "progress", "wealth"],
    label: "90-Day Phase Reflection",
    description: "Reflect on a completed phase of your wealth activation plan.",
  },
  {
    id: "wealth-debt-journey",
    system: "wealth",
    entryType: "progress",
    title: "Debt Payoff Journey",
    promptQuestions: [
      "How did you feel when you first saw your debt landscape visualized?",
      "Which payoff strategy did you choose, and what drove that decision?",
      "What spending patterns have you noticed since starting this journey?",
      "What milestone will you celebrate next?",
    ],
    tags: ["debt", "journey", "wealth"],
    label: "Debt Payoff Journey",
    description:
      "Track your emotional and practical journey through debt payoff.",
  },
  {
    id: "wealth-financial-patterns",
    system: "wealth",
    entryType: "insight",
    title: "Financial Pattern Awareness",
    promptQuestions: [
      "What financial pattern or money script have you become aware of?",
      "Where did this pattern originate — family, culture, past experience?",
      "How has this pattern served you? How has it held you back?",
      "What would a healthier relationship with this pattern look like?",
    ],
    tags: ["patterns", "awareness", "wealth"],
    label: "Financial Pattern Awareness",
    description: "Explore inherited financial patterns and money scripts.",
  },

  // ── Healing ────────────────────────────────────────────────────────
  {
    id: "healing-breathwork-log",
    system: "healing",
    entryType: "practice-log",
    title: "Breathwork Session Log",
    promptQuestions: [
      "Which breathwork pattern did you practice today (Box, 4-7-8, Coherence)?",
      "How long was your session? How did your state shift before vs. after?",
      "What physical sensations did you notice during the practice?",
      "What level of difficulty felt right? Are you ready to progress?",
    ],
    tags: ["breathwork", "practice", "healing"],
    label: "Breathwork Session Log",
    description: "Log and reflect on a breathwork practice session.",
  },
  {
    id: "healing-modality-experience",
    system: "healing",
    entryType: "practice-log",
    title: "Modality Experience",
    promptQuestions: [
      "Which healing modality did you try (somatic, contemplative, expressive, etc.)?",
      "What was your experience like — physically, emotionally, spiritually?",
      "What surprised you about this practice?",
      "Would you return to this modality? Why or why not?",
    ],
    tags: ["modality", "experience", "healing"],
    label: "Modality Experience",
    description: "Capture your experience with a healing modality.",
  },
  {
    id: "healing-assessment-reflection",
    system: "healing",
    entryType: "assessment",
    title: "Healing Assessment Reflection",
    promptQuestions: [
      "What did your healing assessment reveal about your current state?",
      "How does this compare to how you felt a month ago?",
      "What emerging edges do you notice in your healing work?",
      "What goals will you set for your next healing cycle?",
    ],
    tags: ["assessment", "reflection", "healing"],
    label: "Healing Assessment Reflection",
    description: "Reflect on your healing assessment results and progress.",
  },
  {
    id: "healing-practice-progress",
    system: "healing",
    entryType: "progress",
    title: "Practice Progress",
    promptQuestions: [
      "How many sessions have you completed this week/month?",
      "What cumulative changes have you noticed in your body, mood, or outlook?",
      "How has this healing practice integrated into your daily life?",
      "Has your affinity for any particular modality shifted over time?",
    ],
    tags: ["progress", "practice", "healing"],
    label: "Practice Progress",
    description: "Track your cumulative healing practice progress.",
  },
  {
    id: "healing-state-shift",
    system: "healing",
    entryType: "reflection",
    title: "State Shift Journal",
    promptQuestions: [
      "Describe your emotional or physical state before today's practice.",
      "What shifted during or immediately after the practice?",
      "What word or image captures the quality of this shift?",
      "What would you like to carry forward from this experience?",
    ],
    tags: ["state-shift", "awareness", "healing"],
    label: "State Shift Journal",
    description: "Document before/after state shifts from healing practices.",
  },

  // ── Intelligence ───────────────────────────────────────────────────
  {
    id: "intelligence-natal-chart",
    system: "intelligence",
    entryType: "assessment",
    title: "Natal Chart Resonance",
    promptQuestions: [
      "Look at your Sun, Moon, and Rising signs — which one feels most like you?",
      "Does your Moon sign description match your emotional inner life?",
      "How does your Rising sign compare to how others perceive you?",
      "Which planetary aspect stood out as particularly meaningful?",
    ],
    tags: ["astrology", "natal-chart", "identity"],
    label: "Natal Chart Resonance",
    description:
      "Reflect on how your astrological chart resonates with your experience.",
  },
  {
    id: "intelligence-life-path",
    system: "intelligence",
    entryType: "reflection",
    title: "Life Path Narrative",
    promptQuestions: [
      "What is your Life Path number? Does it describe your life trajectory?",
      "How does your Expression number compare to the talents you actually use?",
      "What deep yearnings does your Soul Urge number point to — are you honoring them?",
      "How does your Personal Year number relate to what's happening in your life right now?",
    ],
    tags: ["numerology", "life-path", "reflection"],
    label: "Life Path Narrative",
    description:
      "Explore your numerology profile and how it maps to your life.",
  },
  {
    id: "intelligence-personal-year",
    system: "intelligence",
    entryType: "reflection",
    title: "Personal Year Transition",
    promptQuestions: [
      "What Personal Year are you entering or currently in?",
      "What themes does this year's number suggest for your growth?",
      "How does this compare to what you experienced in your previous Personal Year?",
      "What intention will you set to align with this year's energy?",
    ],
    tags: ["numerology", "personal-year", "transition"],
    label: "Personal Year Transition",
    description: "Reflect on your current Personal Year and its lessons.",
  },
  {
    id: "intelligence-biorhythm",
    system: "intelligence",
    entryType: "practice-log",
    title: "Biorhythm Cycle Reflection",
    promptQuestions: [
      "Where are your physical, emotional, and intellectual cycles positioned right now?",
      "Does your current energy level match what the cycles predict?",
      "Have you noticed any patterns that correlate with high or low cycle periods?",
      "How will you plan your week based on these cycle positions?",
    ],
    tags: ["biorhythm", "cycles", "tracking"],
    label: "Biorhythm Cycle Reflection",
    description:
      "Track how your biorhythm cycles correlate with lived experience.",
  },

  // ── Creative ───────────────────────────────────────────────────────
  {
    id: "creative-style-fingerprint",
    system: "creative",
    entryType: "assessment",
    title: "Style Fingerprint Identity",
    promptQuestions: [
      "What did your Creative Style Fingerprint reveal as your dominant components?",
      "Does this description match how you experience your own creative process?",
      "What blind spots in your creative practice did the assessment uncover?",
      "Do you feel confident calling yourself 'creative'? What shifts when you do?",
    ],
    tags: ["fingerprint", "identity", "creative"],
    label: "Style Fingerprint Identity",
    description:
      "Explore your creative identity through your style fingerprint.",
  },
  {
    id: "creative-project-progress",
    system: "creative",
    entryType: "practice-log",
    title: "Project Progress Log",
    promptQuestions: [
      "Which creative project are you working on? What progress did you make today?",
      "What creative blocks did you encounter, and how did you work through them?",
      "What surprised you during the creative process?",
      "What will you focus on in your next session?",
    ],
    tags: ["project", "progress", "creative"],
    label: "Project Progress Log",
    description: "Track progress on a creative project.",
  },
  {
    id: "creative-block-breakthrough",
    system: "creative",
    entryType: "insight",
    title: "Creative Block Breakthrough",
    promptQuestions: [
      "What creative block were you facing? How long had it persisted?",
      "What finally broke through it — a technique, a change of environment, time?",
      "What did you learn about your creative process from this breakthrough?",
      "How will you approach similar blocks in the future?",
    ],
    tags: ["breakthrough", "blocks", "creative"],
    label: "Creative Block Breakthrough",
    description: "Document a creative block breakthrough and what you learned.",
  },
  {
    id: "creative-guilford-growth",
    system: "creative",
    entryType: "reflection",
    title: "Guilford Growth Area",
    promptQuestions: [
      "Which Guilford dimension (fluency, flexibility, originality, elaboration, sensitivity, redefinition) is your strongest?",
      "Which dimension feels most challenging? Why do you think that is?",
      "How do these thinking dimensions show up in your daily life beyond creative work?",
      "What one exercise could you try this week to strengthen your weakest dimension?",
    ],
    tags: ["guilford", "growth", "creative"],
    label: "Guilford Growth Area",
    description:
      "Reflect on your divergent thinking strengths and growth areas.",
  },
  {
    id: "creative-collaboration",
    system: "creative",
    entryType: "reflection",
    title: "Collaboration Reflection",
    promptQuestions: [
      "Who did you collaborate with, and what was the creative outcome?",
      "Where did your creative styles clash? Where did they complement each other?",
      "What synergies emerged that wouldn't have happened working alone?",
      "What did this collaboration teach you about your own creative process?",
    ],
    tags: ["collaboration", "teamwork", "creative"],
    label: "Collaboration Reflection",
    description: "Reflect on creative collaboration dynamics and discoveries.",
  },
];

/** Look up a template by its ID. Returns undefined if not found. */
export function getTemplateById(id: string): JournalTemplate | undefined {
  return JOURNAL_TEMPLATES.find((t) => t.id === id);
}

/** Get all templates for a given system. */
export function getTemplatesBySystem(
  system: AlchymineSystem,
): JournalTemplate[] {
  return JOURNAL_TEMPLATES.filter((t) => t.system === system);
}

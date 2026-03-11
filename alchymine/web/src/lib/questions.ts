/**
 * Assessment question definitions for the Alchymine intake flow.
 *
 * 20 mini-IPIP Big Five items + 4 Attachment items + 3 Risk Tolerance items
 * + 9 Enneagram items + 5 Kegan Perspective items + 26 Guilford Creativity items = 67 total
 *
 * Each question has:
 *  - id: unique identifier matching the backend scoring engine keys
 *  - text: the question as presented to the user
 *  - trait: which psychological construct this measures
 *  - isReversed: whether the item is reverse-scored (informational for the backend)
 */

export interface Question {
  id: string;
  text: string;
  trait: string;
  isReversed: boolean;
  category:
    | "big_five"
    | "attachment"
    | "risk_tolerance"
    | "enneagram"
    | "creativity"
    | "perspective";
}

// ─── Big Five (mini-IPIP) — 20 items ────────────────────────────────
// Reference: Donnellan et al. (2006), Psychological Assessment 18(2).

export const BIG_FIVE_QUESTIONS: Question[] = [
  // Extraversion
  {
    id: "bf_e1",
    text: "I am the life of the party.",
    trait: "extraversion",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_e2",
    text: "I don't talk a lot.",
    trait: "extraversion",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_e3",
    text: "I talk to a lot of different people at parties.",
    trait: "extraversion",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_e4",
    text: "I keep in the background.",
    trait: "extraversion",
    isReversed: true,
    category: "big_five",
  },

  // Agreeableness
  {
    id: "bf_a1",
    text: "I sympathize with others' feelings.",
    trait: "agreeableness",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_a2",
    text: "I am not interested in other people's problems.",
    trait: "agreeableness",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_a3",
    text: "I feel others' emotions.",
    trait: "agreeableness",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_a4",
    text: "I am not really interested in others.",
    trait: "agreeableness",
    isReversed: true,
    category: "big_five",
  },

  // Conscientiousness
  {
    id: "bf_c1",
    text: "I get chores done right away.",
    trait: "conscientiousness",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_c2",
    text: "I often forget to put things back in their proper place.",
    trait: "conscientiousness",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_c3",
    text: "I like order.",
    trait: "conscientiousness",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_c4",
    text: "I make a mess of things.",
    trait: "conscientiousness",
    isReversed: true,
    category: "big_five",
  },

  // Neuroticism
  {
    id: "bf_n1",
    text: "I have frequent mood swings.",
    trait: "neuroticism",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_n2",
    text: "I am relaxed most of the time.",
    trait: "neuroticism",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_n3",
    text: "I get upset easily.",
    trait: "neuroticism",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_n4",
    text: "I seldom feel blue.",
    trait: "neuroticism",
    isReversed: true,
    category: "big_five",
  },

  // Openness to Experience
  {
    id: "bf_o1",
    text: "I have a vivid imagination.",
    trait: "openness",
    isReversed: false,
    category: "big_five",
  },
  {
    id: "bf_o2",
    text: "I am not interested in abstract ideas.",
    trait: "openness",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_o3",
    text: "I have difficulty understanding abstract ideas.",
    trait: "openness",
    isReversed: true,
    category: "big_five",
  },
  {
    id: "bf_o4",
    text: "I do not have a good imagination.",
    trait: "openness",
    isReversed: true,
    category: "big_five",
  },
];

// ─── Attachment Style — 4 items ─────────────────────────────────────
// Simplified 4-question assessment from the Alchymine attachment engine.

export const ATTACHMENT_QUESTIONS: Question[] = [
  {
    id: "att_closeness",
    text: "I find it easy to become emotionally close to others.",
    trait: "closeness",
    isReversed: false,
    category: "attachment",
  },
  {
    id: "att_abandonment",
    text: "I often worry that people I care about will leave me.",
    trait: "abandonment",
    isReversed: false,
    category: "attachment",
  },
  {
    id: "att_trust",
    text: "I generally trust that others have good intentions toward me.",
    trait: "trust",
    isReversed: false,
    category: "attachment",
  },
  {
    id: "att_self_reliance",
    text: "I prefer to handle problems on my own rather than depend on others.",
    trait: "self_reliance",
    isReversed: false,
    category: "attachment",
  },
];

// ─── Risk Tolerance — 3 items ───────────────────────────────────────
// Financial risk tolerance assessment for the Wealth Engine.

export const RISK_TOLERANCE_QUESTIONS: Question[] = [
  {
    id: "risk_1",
    text: "I am comfortable investing money in something that could lose value in the short term for potential long-term gains.",
    trait: "risk_tolerance",
    isReversed: false,
    category: "risk_tolerance",
  },
  {
    id: "risk_2",
    text: "I would rather take a chance on a high-reward opportunity than stick with a guaranteed but modest return.",
    trait: "risk_tolerance",
    isReversed: false,
    category: "risk_tolerance",
  },
  {
    id: "risk_3",
    text: "Financial uncertainty excites me more than it worries me.",
    trait: "risk_tolerance",
    isReversed: false,
    category: "risk_tolerance",
  },
];

// ─── Enneagram — 9 items ──────────────────────────────────────────
// Simplified 9-item Enneagram assessment. Each item probes one type.

export const ENNEAGRAM_QUESTIONS: Question[] = [
  {
    id: "enn_1",
    text: "I hold myself to high standards and feel a strong need to do things correctly.",
    trait: "enneagram_type_1",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_2",
    text: "I naturally focus on other people's needs and find fulfillment in helping them.",
    trait: "enneagram_type_2",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_3",
    text: "I am driven to achieve goals and care about how others perceive my success.",
    trait: "enneagram_type_3",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_4",
    text: "I often feel different from others and am drawn to expressing my unique identity.",
    trait: "enneagram_type_4",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_5",
    text: "I need plenty of time alone to think and recharge, and I value deep knowledge.",
    trait: "enneagram_type_5",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_6",
    text: "I tend to anticipate what could go wrong and value security and loyalty.",
    trait: "enneagram_type_6",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_7",
    text: "I seek new experiences and possibilities, and I dislike feeling limited or bored.",
    trait: "enneagram_type_7",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_8",
    text: "I am assertive and direct, and I feel compelled to take charge of situations.",
    trait: "enneagram_type_8",
    isReversed: false,
    category: "enneagram",
  },
  {
    id: "enn_9",
    text: "I prefer harmony and peace, and I tend to go along with others to avoid conflict.",
    trait: "enneagram_type_9",
    isReversed: false,
    category: "enneagram",
  },
];

// ─── Kegan Perspective — 5 items ─────────────────────────────────────
// Simplified 5-question Kegan developmental stage assessment.
// Each item maps to one scoring dimension: self_awareness,
// perspective_taking, relationship_to_authority, conflict_tolerance,
// systems_thinking.
// Reference: Robert Kegan — "The Evolving Self" (1982);
//            "In Over Our Heads" (1994).

export const KEGAN_QUESTIONS: Question[] = [
  {
    id: "kegan_1",
    text: "When I reflect on my actions, I can clearly see how my emotions and assumptions shape my decisions.",
    trait: "kegan_stage",
    isReversed: false,
    category: "perspective",
  },
  {
    id: "kegan_2",
    text: "When someone disagrees with me, I can genuinely understand their point of view even if I still disagree.",
    trait: "kegan_stage",
    isReversed: false,
    category: "perspective",
  },
  {
    id: "kegan_3",
    text: "I follow my own values even when they conflict with what important people in my life expect of me.",
    trait: "kegan_stage",
    isReversed: false,
    category: "perspective",
  },
  {
    id: "kegan_4",
    text: "I can sit with a disagreement without needing to resolve it right away or take sides.",
    trait: "kegan_stage",
    isReversed: false,
    category: "perspective",
  },
  {
    id: "kegan_5",
    text: "I often notice how different systems — social, economic, psychological — interact and shape outcomes in complex ways.",
    trait: "kegan_stage",
    isReversed: false,
    category: "perspective",
  },
];

// ─── Guilford Creativity — 26 items ─────────────────────────────────
// Divergent thinking (18 items across 6 dimensions) + convergent
// thinking (8 items). Based on Guilford's Structure of Intellect (1967).

export const GUILFORD_QUESTIONS: Question[] = [
  // Fluency — ability to generate many ideas
  {
    id: "guil_flu1",
    text: "I can quickly come up with many ideas when brainstorming.",
    trait: "fluency",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_flu2",
    text: "When asked for solutions, I easily generate a long list of possibilities.",
    trait: "fluency",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_flu3",
    text: "I rarely run out of ideas in a creative discussion.",
    trait: "fluency",
    isReversed: false,
    category: "creativity",
  },

  // Flexibility — ability to shift approaches
  {
    id: "guil_flex1",
    text: "I easily switch between different strategies when one approach isn't working.",
    trait: "flexibility",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_flex2",
    text: "I naturally consider problems from multiple angles.",
    trait: "flexibility",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_flex3",
    text: "I can adapt my thinking style to fit different types of challenges.",
    trait: "flexibility",
    isReversed: false,
    category: "creativity",
  },

  // Originality — ability to produce novel ideas
  {
    id: "guil_orig1",
    text: "People often describe my ideas as unusual or unexpected.",
    trait: "originality",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_orig2",
    text: "I prefer to find my own unique approach rather than follow conventional methods.",
    trait: "originality",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_orig3",
    text: "I enjoy coming up with solutions that no one else has thought of.",
    trait: "originality",
    isReversed: false,
    category: "creativity",
  },

  // Elaboration — ability to add detail and complexity
  {
    id: "guil_elab1",
    text: "When I have an idea, I naturally think about how to flesh out every detail.",
    trait: "elaboration",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_elab2",
    text: "I enjoy taking a simple concept and making it richer and more complex.",
    trait: "elaboration",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_elab3",
    text: "I am good at building on others' ideas and adding layers of depth.",
    trait: "elaboration",
    isReversed: false,
    category: "creativity",
  },

  // Sensitivity — ability to detect problems and opportunities
  {
    id: "guil_sens1",
    text: "I quickly notice flaws or gaps that others overlook.",
    trait: "sensitivity",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_sens2",
    text: "I often sense opportunities for improvement before others do.",
    trait: "sensitivity",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_sens3",
    text: "I am highly attuned to subtle patterns and details in my environment.",
    trait: "sensitivity",
    isReversed: false,
    category: "creativity",
  },

  // Redefinition — ability to reframe and repurpose
  {
    id: "guil_redef1",
    text: "I can see new uses for everyday objects or familiar tools.",
    trait: "redefinition",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_redef2",
    text: "I enjoy rethinking the purpose of things and finding unconventional applications.",
    trait: "redefinition",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_redef3",
    text: "When a plan fails, I can repurpose what I've built toward a different goal.",
    trait: "redefinition",
    isReversed: false,
    category: "creativity",
  },

  // Convergent Thinking — analytical and evaluative skills
  {
    id: "guil_conv1",
    text: "I am good at narrowing many ideas down to the single best option.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv2",
    text: "I can logically evaluate the strengths and weaknesses of different approaches.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv3",
    text: "I prefer to fully analyze a problem before proposing a solution.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv4",
    text: "I am skilled at finding the one correct answer when the evidence points to it.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv5",
    text: "I carefully weigh trade-offs before making a decision.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv6",
    text: "I tend to systematically test ideas rather than going with my gut.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv7",
    text: "I can quickly identify which ideas are practical and which are not.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
  {
    id: "guil_conv8",
    text: "I am effective at synthesizing information from multiple sources into a clear conclusion.",
    trait: "convergent",
    isReversed: false,
    category: "creativity",
  },
];

// ─── All questions combined ─────────────────────────────────────────

export const ALL_QUESTIONS: Question[] = [
  ...BIG_FIVE_QUESTIONS,
  ...ATTACHMENT_QUESTIONS,
  ...RISK_TOLERANCE_QUESTIONS,
  ...ENNEAGRAM_QUESTIONS,
  ...KEGAN_QUESTIONS,
  ...GUILFORD_QUESTIONS,
];

// Likert scale labels (1-5)
export const LIKERT_LABELS = [
  "Strongly Disagree",
  "Disagree",
  "Neutral",
  "Agree",
  "Strongly Agree",
] as const;

export const TOTAL_QUESTIONS = ALL_QUESTIONS.length; // 67

export type QuestionCategory = Question["category"];

export const QUESTION_CATEGORIES: QuestionCategory[] = [
  "big_five",
  "attachment",
  "risk_tolerance",
  "enneagram",
  "perspective",
  "creativity",
];

/**
 * Filter ALL_QUESTIONS to only include the specified categories.
 * Returns all questions if sections is empty or undefined.
 */
export function filterQuestionsBySection(
  sections?: QuestionCategory[],
): Question[] {
  if (!sections || sections.length === 0) return ALL_QUESTIONS;
  return ALL_QUESTIONS.filter((q) => sections.includes(q.category));
}

// ─── Creative DNA Supplement Questions ──────────────────────────────
// These are NOT included in ALL_QUESTIONS — they are used in the
// "Deepen Your Creative DNA" supplement flow after initial report.

export interface SelectOption {
  value: string;
  label: string;
}

export interface SupplementQuestion {
  id: string;
  text: string;
  type: "likert" | "select";
  options?: SelectOption[];
}

export const CREATIVE_DNA_SUPPLEMENT_QUESTIONS: SupplementQuestion[] = [
  // Structure vs. Improvisation
  {
    id: "dna_structure_1",
    text: "I prefer to have a detailed plan before starting a creative project.",
    type: "likert",
  },
  {
    id: "dna_structure_2",
    text: "I do my best creative work when I follow a structured process.",
    type: "likert",
  },
  // Collaboration vs. Solitude
  {
    id: "dna_collab_1",
    text: "I create my best work when collaborating with others.",
    type: "likert",
  },
  {
    id: "dna_collab_2",
    text: "I need other people's input to refine my creative ideas.",
    type: "likert",
  },
  // Convergent vs. Divergent
  {
    id: "dna_convergent_1",
    text: "I prefer to explore many possibilities before settling on one direction.",
    type: "likert",
  },
  {
    id: "dna_convergent_2",
    text: "I am energized by generating as many ideas as possible, even wild ones.",
    type: "likert",
  },
  // Categorical: Primary Sensory Mode
  {
    id: "primary_sensory_mode",
    text: "Which sensory mode feels most natural when you create?",
    type: "select",
    options: [
      { value: "visual", label: "Visual (images, colors, shapes)" },
      { value: "verbal", label: "Verbal (words, stories, language)" },
      {
        value: "kinesthetic",
        label: "Kinesthetic (movement, touch, building)",
      },
      { value: "musical", label: "Musical (rhythm, melody, sound)" },
    ],
  },
  // Categorical: Creative Peak
  {
    id: "creative_peak",
    text: "When do you feel most creatively alive?",
    type: "select",
    options: [
      { value: "morning", label: "Morning" },
      { value: "evening", label: "Evening" },
    ],
  },
];

/**
 * Assessment question definitions for the Alchymine intake flow.
 *
 * 20 mini-IPIP Big Five items + 4 Attachment items + 3 Risk Tolerance items = 27 total
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
  category: 'big_five' | 'attachment' | 'risk_tolerance';
}

// ─── Big Five (mini-IPIP) — 20 items ────────────────────────────────
// Reference: Donnellan et al. (2006), Psychological Assessment 18(2).

export const BIG_FIVE_QUESTIONS: Question[] = [
  // Extraversion
  {
    id: 'bf_e1',
    text: 'I am the life of the party.',
    trait: 'extraversion',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_e2',
    text: "I don't talk a lot.",
    trait: 'extraversion',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_e3',
    text: 'I talk to a lot of different people at parties.',
    trait: 'extraversion',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_e4',
    text: 'I keep in the background.',
    trait: 'extraversion',
    isReversed: true,
    category: 'big_five',
  },

  // Agreeableness
  {
    id: 'bf_a1',
    text: "I sympathize with others' feelings.",
    trait: 'agreeableness',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_a2',
    text: "I am not interested in other people's problems.",
    trait: 'agreeableness',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_a3',
    text: "I feel others' emotions.",
    trait: 'agreeableness',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_a4',
    text: 'I am not really interested in others.',
    trait: 'agreeableness',
    isReversed: true,
    category: 'big_five',
  },

  // Conscientiousness
  {
    id: 'bf_c1',
    text: 'I get chores done right away.',
    trait: 'conscientiousness',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_c2',
    text: 'I often forget to put things back in their proper place.',
    trait: 'conscientiousness',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_c3',
    text: 'I like order.',
    trait: 'conscientiousness',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_c4',
    text: 'I make a mess of things.',
    trait: 'conscientiousness',
    isReversed: true,
    category: 'big_five',
  },

  // Neuroticism
  {
    id: 'bf_n1',
    text: 'I have frequent mood swings.',
    trait: 'neuroticism',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_n2',
    text: 'I am relaxed most of the time.',
    trait: 'neuroticism',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_n3',
    text: 'I get upset easily.',
    trait: 'neuroticism',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_n4',
    text: 'I seldom feel blue.',
    trait: 'neuroticism',
    isReversed: true,
    category: 'big_five',
  },

  // Openness to Experience
  {
    id: 'bf_o1',
    text: 'I have a vivid imagination.',
    trait: 'openness',
    isReversed: false,
    category: 'big_five',
  },
  {
    id: 'bf_o2',
    text: 'I am not interested in abstract ideas.',
    trait: 'openness',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_o3',
    text: 'I have difficulty understanding abstract ideas.',
    trait: 'openness',
    isReversed: true,
    category: 'big_five',
  },
  {
    id: 'bf_o4',
    text: 'I do not have a good imagination.',
    trait: 'openness',
    isReversed: true,
    category: 'big_five',
  },
];

// ─── Attachment Style — 4 items ─────────────────────────────────────
// Simplified 4-question assessment from the Alchymine attachment engine.

export const ATTACHMENT_QUESTIONS: Question[] = [
  {
    id: 'att_closeness',
    text: 'I find it easy to become emotionally close to others.',
    trait: 'closeness',
    isReversed: false,
    category: 'attachment',
  },
  {
    id: 'att_abandonment',
    text: 'I often worry that people I care about will leave me.',
    trait: 'abandonment',
    isReversed: false,
    category: 'attachment',
  },
  {
    id: 'att_trust',
    text: 'I generally trust that others have good intentions toward me.',
    trait: 'trust',
    isReversed: false,
    category: 'attachment',
  },
  {
    id: 'att_self_reliance',
    text: 'I prefer to handle problems on my own rather than depend on others.',
    trait: 'self_reliance',
    isReversed: false,
    category: 'attachment',
  },
];

// ─── Risk Tolerance — 3 items ───────────────────────────────────────
// Financial risk tolerance assessment for the Wealth Engine.

export const RISK_TOLERANCE_QUESTIONS: Question[] = [
  {
    id: 'risk_1',
    text: 'I am comfortable investing money in something that could lose value in the short term for potential long-term gains.',
    trait: 'risk_tolerance',
    isReversed: false,
    category: 'risk_tolerance',
  },
  {
    id: 'risk_2',
    text: 'I would rather take a chance on a high-reward opportunity than stick with a guaranteed but modest return.',
    trait: 'risk_tolerance',
    isReversed: false,
    category: 'risk_tolerance',
  },
  {
    id: 'risk_3',
    text: 'Financial uncertainty excites me more than it worries me.',
    trait: 'risk_tolerance',
    isReversed: false,
    category: 'risk_tolerance',
  },
];

// ─── All questions combined ─────────────────────────────────────────

export const ALL_QUESTIONS: Question[] = [
  ...BIG_FIVE_QUESTIONS,
  ...ATTACHMENT_QUESTIONS,
  ...RISK_TOLERANCE_QUESTIONS,
];

// Likert scale labels (1-5)
export const LIKERT_LABELS = [
  'Strongly Disagree',
  'Disagree',
  'Neutral',
  'Agree',
  'Strongly Agree',
] as const;

export const TOTAL_QUESTIONS = ALL_QUESTIONS.length; // 27

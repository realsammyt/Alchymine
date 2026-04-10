/**
 * Starter prompts — contextual conversation starters shown as chips
 * when the chat panel is empty (no history).
 *
 * Each system has 3 prompts tailored to its coaching domain.  The
 * general mode (no system key) has prompts that span all pillars.
 */

import type { SystemKey } from "@/hooks/usePageContext";

export interface StarterPrompt {
  /** Short label displayed on the chip. */
  label: string;
  /** Full message sent to the assistant when clicked. */
  message: string;
}

const STARTER_PROMPTS: Record<string, StarterPrompt[]> = {
  intelligence: [
    {
      label: "Explain my profile",
      message: "Can you explain the key insights from my personal intelligence profile?",
    },
    {
      label: "Life Path meaning",
      message: "What does my Life Path number suggest about my strengths and challenges?",
    },
    {
      label: "Archetype exploration",
      message: "Help me understand my primary archetype and how it shapes my decisions.",
    },
  ],
  healing: [
    {
      label: "Breathwork for me",
      message: "What breathwork practice would suit my profile and current needs?",
    },
    {
      label: "My healing journey",
      message: "Explain my healing journey so far and suggest next steps.",
    },
    {
      label: "Shadow work guide",
      message: "How do I begin shadow work in a safe and grounded way?",
    },
  ],
  wealth: [
    {
      label: "Budget approach",
      message: "Review my budget approach and suggest improvements based on my profile.",
    },
    {
      label: "Compound interest",
      message: "Explain compound interest in a way that connects to my financial goals.",
    },
    {
      label: "Money scripts",
      message: "What money scripts might I be running from my family history?",
    },
  ],
  creative: [
    {
      label: "Unlock creativity",
      message: "What practices can help me unlock my creative potential right now?",
    },
    {
      label: "Creative blocks",
      message: "Help me work through my creative blocks with practical exercises.",
    },
    {
      label: "Daily practice",
      message: "Suggest a daily creative practice tailored to my profile.",
    },
  ],
  perspective: [
    {
      label: "Cognitive patterns",
      message: "Help me notice when I fall into cognitive distortions.",
    },
    {
      label: "Reframe a challenge",
      message: "I have a situation I'd like to reframe with a healthier perspective.",
    },
    {
      label: "Mindfulness start",
      message: "What's a good mindfulness practice for someone at my stage?",
    },
  ],
};

/** General prompts when no system is active. */
const GENERAL_PROMPTS: StarterPrompt[] = [
  {
    label: "Start my journey",
    message: "Where should I begin my personal transformation journey?",
  },
  {
    label: "Explore my profile",
    message: "What are the most important insights from my overall profile?",
  },
  {
    label: "Daily check-in",
    message: "I'd like to do a quick daily check-in across all five pillars.",
  },
];

/**
 * Return the starter prompts for a given system key, falling back to
 * the general prompts when the key is `null` or unknown.
 */
export function getStarterPrompts(systemKey: SystemKey | string | null): StarterPrompt[] {
  if (!systemKey) return GENERAL_PROMPTS;
  return STARTER_PROMPTS[systemKey] ?? GENERAL_PROMPTS;
}

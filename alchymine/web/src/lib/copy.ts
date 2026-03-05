export const COPY = {
  // Time-aware greetings
  greeting: (name?: string) => {
    const hour = new Date().getHours();
    const timeGreeting =
      hour < 12
        ? "Good morning"
        : hour < 17
          ? "Good afternoon"
          : "Good evening";
    return name ? `${timeGreeting}, ${name}` : timeGreeting;
  },

  // Empty states — each is a gentle invitation, never "No data found"
  emptyStates: {
    dashboard: {
      title: "Your Transformation Begins Here",
      body: "Start with a quick assessment to unlock personalized insights across all five pillars.",
      cta: "Begin Your Assessment",
      ctaHref: "/discover/intake",
    },
    journal: {
      title: "Your Space for Reflection",
      body: "Journaling is where insight becomes wisdom. What's on your mind today?",
      cta: "Write Your First Entry",
    },
    healing: {
      title: "Your Healing Journey Awaits",
      body: "Explore evidence-based modalities matched to your unique profile. Start with a 3-minute breathwork session.",
      cta: "Try Breathwork",
    },
    wealth: {
      title: "Build Your Financial Foundation",
      body: "Discover your wealth archetype and create a personalized 90-day plan for lasting change.",
      cta: "Start Assessment",
      ctaHref: "/discover/intake",
    },
    creative: {
      title: "Unlock Your Creative Potential",
      body: "Your creativity has a unique signature. Let's discover it together.",
      cta: "Start Assessment",
      ctaHref: "/discover/intake",
    },
    perspective: {
      title: "Expand Your Worldview",
      body: "Understanding how you make meaning opens doors to growth you didn't know were there.",
      cta: "Start Assessment",
      ctaHref: "/discover/intake",
    },
  },

  // Disclaimers
  disclaimers: {
    financial:
      "This is for educational purposes only, not financial advice. Consult a qualified financial professional before making financial decisions.",
    healing:
      "This does not replace professional medical or mental health care. If you're in crisis, please reach out to a professional.",
    biorhythm:
      "Biorhythm calculations are provided for entertainment purposes only. There is no peer-reviewed scientific evidence supporting biorhythm theory.",
    entertainment:
      "This insight is for entertainment and self-reflection only.",
  },

  // Milestone messages
  milestones: {
    firstAssessment:
      "Welcome to your personalized journey. Your insights are ready to explore.",
    journalStreak: (days: number) =>
      `${days}-day reflection streak! Consistency builds wisdom.`,
    breathworkSession: (count: number) =>
      count === 1
        ? "Your first breathwork session — a powerful step."
        : `${count} breathwork sessions completed. Your practice is growing.`,
    planProgress: (day: number) =>
      `Day ${day} of your 90-day plan. Every step counts.`,
  },

  // Pillar descriptions (for first visit or onboarding)
  pillarIntros: {
    intelligence:
      "Your Intelligence profile combines numerology, astrology, and biorhythm to reveal patterns in your life's timing and purpose.",
    healing:
      "Healing recommendations are matched to your psychological profile using evidence-rated modalities — from peer-reviewed therapies to traditional practices.",
    wealth:
      "Your Wealth profile identifies your financial archetype and creates actionable plans using deterministic calculations — never AI-generated financial advice.",
    creative:
      "Creative Development maps your unique creative signature using the Guilford framework, then suggests projects that match your strengths.",
    perspective:
      "Perspective Enhancement uses Kegan's developmental framework to understand how you make meaning — and what growth looks like from here.",
  },

  // Evidence level labels
  evidenceLabels: {
    strong: "Supported by peer-reviewed research",
    moderate: "Supported by emerging research",
    emerging: "Based on theoretical frameworks",
    traditional: "Rooted in cultural and historical tradition",
    entertainment: "For entertainment and self-reflection only",
  },
} as const;

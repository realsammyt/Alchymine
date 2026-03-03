import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#DAA520",
          dark: "#B8860B",
          light: "#F0C050",
        },
        secondary: {
          DEFAULT: "#7B2D8E",
          dark: "#4A0E4E",
          light: "#9B4DCA",
        },
        accent: {
          DEFAULT: "#20B2AA",
          dark: "#008080",
          light: "#5CD6D0",
        },
        bg: "#0A0A0F",
        surface: "#1A1A2E",
        "surface-elevated": "#22223A",
        text: "#F5F0E8",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      fontSize: {
        "display-xl": [
          "clamp(3rem, 6vw, 5.5rem)",
          { lineHeight: "1.05", letterSpacing: "-0.02em" },
        ],
        "display-lg": [
          "clamp(2.25rem, 4vw, 3.75rem)",
          { lineHeight: "1.1", letterSpacing: "-0.015em" },
        ],
        "display-md": [
          "clamp(1.75rem, 3vw, 2.5rem)",
          { lineHeight: "1.15", letterSpacing: "-0.01em" },
        ],
      },
      animation: {
        shimmer: "shimmer 2s linear infinite",
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "slide-up": "slideUp 0.6s ease-out forwards",
        "slide-up-delayed": "slideUp 0.6s 0.15s ease-out forwards",
        "pulse-gold": "pulseGold 3s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        "float-delayed": "float 6s 2s ease-in-out infinite",
        "glow-breathe": "glowBreathe 4s ease-in-out infinite",
        "grain-drift": "grainDrift 0.5s steps(1) infinite",
        "spiral-pulse": "spiralPulse 3s ease-in-out infinite",
        "spiral-pulse-fast": "spiralPulse 2s ease-in-out infinite",
        "spiral-rotate": "spiralRotate 8s linear infinite",
        "spiral-rotate-reverse": "spiralRotate 5s linear infinite reverse",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGold: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(218, 165, 32, 0.3)" },
          "50%": { boxShadow: "0 0 30px 15px rgba(218, 165, 32, 0.08)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        glowBreathe: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.8" },
        },
        spiralPulse: {
          "0%, 100%": { opacity: "0.7", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        spiralRotate: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        grainDrift: {
          "0%": { transform: "translate(0, 0)" },
          "10%": { transform: "translate(-2%, -3%)" },
          "20%": { transform: "translate(3%, 1%)" },
          "30%": { transform: "translate(-1%, 2%)" },
          "40%": { transform: "translate(2%, -1%)" },
          "50%": { transform: "translate(-3%, 3%)" },
          "60%": { transform: "translate(1%, -2%)" },
          "70%": { transform: "translate(-2%, 1%)" },
          "80%": { transform: "translate(3%, -3%)" },
          "90%": { transform: "translate(-1%, 2%)" },
          "100%": { transform: "translate(0, 0)" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-mesh":
          "radial-gradient(ellipse at 20% 80%, rgba(123,45,142,0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(218,165,32,0.06) 0%, transparent 50%), radial-gradient(ellipse at 50% 50%, rgba(32,178,170,0.04) 0%, transparent 60%)",
      },
    },
  },
  plugins: [],
};

export default config;

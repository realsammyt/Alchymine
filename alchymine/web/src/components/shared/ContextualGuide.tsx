"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { COPY } from "@/lib/copy";

type Pillar = keyof typeof COPY.pillarIntros;

interface ContextualGuideProps {
  pillar: Pillar;
  storageKey: string;
}

export default function ContextualGuide({
  pillar,
  storageKey,
}: ContextualGuideProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const dismissed = localStorage.getItem(`guide_dismissed_${storageKey}`);
      if (!dismissed) {
        setVisible(true);
      }
    } catch {
      // localStorage unavailable (e.g., SSR or privacy mode)
    }
  }, [storageKey]);

  const handleDismiss = () => {
    try {
      localStorage.setItem(`guide_dismissed_${storageKey}`, "true");
    } catch {
      // localStorage unavailable
    }
    setVisible(false);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="border-l-2 border-primary bg-surface/60 backdrop-blur-sm rounded-r-lg px-4 py-3 mb-6 flex items-start gap-3"
          role="note"
          aria-label={`Guide for ${pillar} pillar`}
        >
          <p className="flex-1 text-sm text-text/70 leading-relaxed">
            {COPY.pillarIntros[pillar]}
          </p>
          <button
            onClick={handleDismiss}
            className="shrink-0 text-xs text-primary/60 hover:text-primary transition-colors mt-0.5 whitespace-nowrap"
            aria-label="Dismiss guide"
          >
            Got it
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

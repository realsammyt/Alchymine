'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getReport, ApiError } from '@/lib/api';

const GENERATION_STEPS = [
  { label: 'Calculating numerology...', icon: '🔢', duration: 2000 },
  { label: 'Mapping astrology...', icon: '⭐', duration: 3000 },
  { label: 'Analyzing personality...', icon: '🧠', duration: 2500 },
  { label: 'Mapping archetypes...', icon: '🪞', duration: 2000 },
  { label: 'Building your profile...', icon: '✨', duration: 3000 },
];

export default function GeneratingPage() {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;

  const [currentStep, setCurrentStep] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const animationRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Animate through the visual steps
  useEffect(() => {
    let stepIndex = 0;
    const totalDuration = GENERATION_STEPS.reduce((s, step) => s + step.duration, 0);
    let elapsed = 0;

    animationRef.current = setInterval(() => {
      elapsed += 100;
      const progressPercent = Math.min((elapsed / totalDuration) * 90, 90); // cap visual at 90%
      setOverallProgress(progressPercent);

      // Determine which step we're on
      let cumulative = 0;
      for (let i = 0; i < GENERATION_STEPS.length; i++) {
        cumulative += GENERATION_STEPS[i].duration;
        if (elapsed < cumulative) {
          if (i !== stepIndex) {
            stepIndex = i;
            setCurrentStep(i);
          }
          break;
        }
      }

      // If we've exceeded total duration, just stay on last step
      if (elapsed >= totalDuration) {
        setCurrentStep(GENERATION_STEPS.length - 1);
      }
    }, 100);

    return () => {
      if (animationRef.current) clearInterval(animationRef.current);
    };
  }, []);

  // Poll the API for report completion
  useEffect(() => {
    if (!reportId) return;

    pollRef.current = setInterval(async () => {
      try {
        const report = await getReport(reportId);
        // If we get here without an error, the report is complete
        if (report.status === 'completed') {
          setOverallProgress(100);
          if (pollRef.current) clearInterval(pollRef.current);
          if (animationRef.current) clearInterval(animationRef.current);
          setTimeout(() => {
            router.push(`/discover/report/${reportId}`);
          }, 800);
        } else if (report.status === 'failed') {
          setError('Report generation failed. Please try again.');
          if (pollRef.current) clearInterval(pollRef.current);
          if (animationRef.current) clearInterval(animationRef.current);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 202) {
          // Still generating — this is expected
          return;
        }
        // Real error — but don't stop polling for transient network issues
        console.error('Polling error:', err);
      }
    }, 2000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [reportId, router]);

  const step = GENERATION_STEPS[currentStep];

  return (
    <div className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md text-center">
        {/* Animated orb */}
        <div className="relative w-32 h-32 mx-auto mb-10">
          {/* Outer glow ring */}
          <div className="absolute inset-0 rounded-full bg-primary/10 animate-pulse-gold" />
          {/* Spinning gradient ring */}
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-primary border-r-primary/50 animate-spin" style={{ animationDuration: '3s' }} />
          {/* Inner shimmer */}
          <div className="absolute inset-4 rounded-full bg-gradient-to-br from-primary-dark/30 to-secondary-dark/30 shimmer-gold" />
          {/* Center icon */}
          <div className="absolute inset-0 flex items-center justify-center text-4xl">
            {step.icon}
          </div>
        </div>

        {/* Step label */}
        <h2 className="text-2xl font-bold mb-2 animate-fade-in" key={step.label}>
          {step.label}
        </h2>
        <p className="text-text/50 text-sm mb-8">
          Our deterministic engines are analyzing your unique data.
        </p>

        {/* Progress bar */}
        <div className="w-full bg-surface rounded-full h-2.5 mb-4 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-300 ease-out relative overflow-hidden"
            style={{ width: `${overallProgress}%` }}
          >
            <div className="absolute inset-0 shimmer-gold opacity-60" />
          </div>
        </div>
        <p className="text-sm text-text/40">
          {Math.round(overallProgress)}% complete
        </p>

        {/* Step indicators */}
        <div className="mt-10 space-y-3">
          {GENERATION_STEPS.map((s, idx) => (
            <div
              key={s.label}
              className={`flex items-center gap-3 text-sm transition-all duration-500 ${
                idx < currentStep
                  ? 'text-primary'
                  : idx === currentStep
                    ? 'text-text'
                    : 'text-text/20'
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${
                  idx < currentStep
                    ? 'bg-primary text-bg'
                    : idx === currentStep
                      ? 'border-2 border-primary text-primary'
                      : 'border border-white/10'
                }`}
              >
                {idx < currentStep && (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
              <span>{s.label.replace('...', '')}</span>
            </div>
          ))}
        </div>

        {/* Error state */}
        {error && (
          <div className="mt-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
            <button
              onClick={() => router.push('/discover/intake')}
              className="block mt-2 text-primary hover:text-primary/80 underline"
            >
              Start over
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

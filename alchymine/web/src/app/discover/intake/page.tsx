'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/components/shared/Button';

const INTENTIONS = [
  { value: 'career', label: 'Career Growth', icon: '💼' },
  { value: 'love', label: 'Love & Relationships', icon: '❤️' },
  { value: 'purpose', label: 'Life Purpose', icon: '🧭' },
  { value: 'money', label: 'Financial Freedom', icon: '💰' },
  { value: 'health', label: 'Health & Vitality', icon: '🌿' },
  { value: 'family', label: 'Family & Legacy', icon: '👨‍👩‍👧‍👦' },
  { value: 'business', label: 'Business Building', icon: '🚀' },
  { value: 'legacy', label: 'Legacy & Impact', icon: '🏛️' },
] as const;

interface IntakeFormData {
  fullName: string;
  birthDate: string;
  birthTime: string;
  birthCity: string;
  intention: string;
}

export default function IntakePage() {
  const router = useRouter();
  const [formData, setFormData] = useState<IntakeFormData>({
    fullName: '',
    birthDate: '',
    birthTime: '',
    birthCity: '',
    intention: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof IntakeFormData, string>>>({});

  function validate(): boolean {
    const newErrors: Partial<Record<keyof IntakeFormData, string>> = {};

    if (!formData.fullName.trim() || formData.fullName.trim().length < 2) {
      newErrors.fullName = 'Please enter your full name (at least 2 characters).';
    }
    if (!formData.birthDate) {
      newErrors.birthDate = 'Please select your birth date.';
    }
    if (!formData.intention) {
      newErrors.intention = 'Please select your primary intention.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    // Store in sessionStorage for the assessment page to pick up
    sessionStorage.setItem('alchymine_intake', JSON.stringify(formData));
    router.push('/discover/assessment');
  }

  return (
    <div className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            Let&apos;s <span className="text-gradient-gold">Begin</span>
          </h1>
          <p className="text-text/60">
            Tell us a bit about yourself. This information powers the
            deterministic engines behind your profile.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Full Name */}
          <div>
            <label
              htmlFor="fullName"
              className="block text-sm font-medium text-text/80 mb-2"
            >
              Full Name <span className="text-primary">*</span>
            </label>
            <input
              id="fullName"
              type="text"
              required
              placeholder="e.g. Maya Angelou"
              value={formData.fullName}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, fullName: e.target.value }))
              }
              className="w-full px-4 py-3 bg-surface border border-white/10 rounded-xl text-text placeholder-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors"
            />
            {errors.fullName && (
              <p className="mt-1.5 text-sm text-red-400">{errors.fullName}</p>
            )}
          </div>

          {/* Birth Date */}
          <div>
            <label
              htmlFor="birthDate"
              className="block text-sm font-medium text-text/80 mb-2"
            >
              Birth Date <span className="text-primary">*</span>
            </label>
            <input
              id="birthDate"
              type="date"
              required
              value={formData.birthDate}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, birthDate: e.target.value }))
              }
              className="w-full px-4 py-3 bg-surface border border-white/10 rounded-xl text-text focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors [color-scheme:dark]"
            />
            {errors.birthDate && (
              <p className="mt-1.5 text-sm text-red-400">{errors.birthDate}</p>
            )}
          </div>

          {/* Birth Time (optional) */}
          <div>
            <label
              htmlFor="birthTime"
              className="block text-sm font-medium text-text/80 mb-2"
            >
              Birth Time{' '}
              <span className="text-text/40 font-normal">
                (optional — enables Rising sign)
              </span>
            </label>
            <input
              id="birthTime"
              type="time"
              value={formData.birthTime}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, birthTime: e.target.value }))
              }
              className="w-full px-4 py-3 bg-surface border border-white/10 rounded-xl text-text focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors [color-scheme:dark]"
            />
          </div>

          {/* Birth City (optional) */}
          <div>
            <label
              htmlFor="birthCity"
              className="block text-sm font-medium text-text/80 mb-2"
            >
              Birth City{' '}
              <span className="text-text/40 font-normal">
                (optional — enables house calculations)
              </span>
            </label>
            <input
              id="birthCity"
              type="text"
              placeholder="e.g. Toronto, Canada"
              value={formData.birthCity}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, birthCity: e.target.value }))
              }
              className="w-full px-4 py-3 bg-surface border border-white/10 rounded-xl text-text placeholder-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors"
            />
          </div>

          {/* Intention Selector */}
          <div>
            <label className="block text-sm font-medium text-text/80 mb-3">
              What brings you here? <span className="text-primary">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              {INTENTIONS.map((intent) => (
                <button
                  key={intent.value}
                  type="button"
                  onClick={() =>
                    setFormData((prev) => ({
                      ...prev,
                      intention: intent.value,
                    }))
                  }
                  className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border text-left text-sm transition-all duration-200 ${
                    formData.intention === intent.value
                      ? 'border-primary/50 bg-primary/10 text-text'
                      : 'border-white/10 bg-surface text-text/60 hover:border-white/20 hover:bg-surface/80'
                  }`}
                >
                  <span className="text-lg">{intent.icon}</span>
                  <span>{intent.label}</span>
                </button>
              ))}
            </div>
            {errors.intention && (
              <p className="mt-1.5 text-sm text-red-400">{errors.intention}</p>
            )}
          </div>

          {/* Submit */}
          <div className="pt-4">
            <Button type="submit" size="lg" className="w-full">
              Continue to Assessment
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

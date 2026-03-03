"use client";

import SpiralHub from "@/components/spiral/SpiralHub";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function DiscoverPage() {
  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-12">
      <MotionReveal>
        <SpiralHub />
      </MotionReveal>
    </main>
  );
}

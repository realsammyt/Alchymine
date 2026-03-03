"use client";

import SpiralHub from "@/components/spiral/SpiralHub";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function DiscoverPage() {
  return (
    <main className="grain-overlay min-h-screen">
      <div className="bg-atmosphere min-h-screen">
        <MotionReveal>
          <SpiralHub />
        </MotionReveal>
      </div>
    </main>
  );
}

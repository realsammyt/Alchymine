"use client";

import SpiralHub from "@/components/spiral/SpiralHub";
import { MotionReveal } from "@/components/shared/MotionReveal";
import ProtectedRoute from "@/components/shared/ProtectedRoute";

export default function DiscoverPage() {
  return (
    <ProtectedRoute>
      <main className="grain-overlay min-h-screen">
        <div className="bg-atmosphere min-h-screen">
          <MotionReveal>
            <SpiralHub />
          </MotionReveal>
        </div>
      </main>
    </ProtectedRoute>
  );
}

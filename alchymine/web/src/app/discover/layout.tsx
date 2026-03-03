"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import StepIndicator from "@/components/shared/StepIndicator";

const STEPS = [
  { label: "Intake", path: "/discover/intake" },
  { label: "Assessment", path: "/discover/assessment" },
  { label: "Generating", path: "/discover/generating" },
  { label: "Report", path: "/discover/report" },
];

function getCurrentStep(pathname: string): number {
  if (pathname.includes("/report")) return 3;
  if (pathname.includes("/generating")) return 2;
  if (pathname.includes("/assessment")) return 1;
  return 0;
}

export default function DiscoverLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const currentStep = getCurrentStep(pathname);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav bar */}
      <header className="border-b border-white/5 bg-bg/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-gradient-gold">
            Alchymine
          </Link>
          <div className="hidden sm:block">
            <StepIndicator steps={STEPS} currentStep={currentStep} />
          </div>
        </div>
        {/* Mobile step indicator */}
        <div className="sm:hidden px-4 pb-3">
          <StepIndicator steps={STEPS} currentStep={currentStep} />
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 flex flex-col">{children}</main>
    </div>
  );
}

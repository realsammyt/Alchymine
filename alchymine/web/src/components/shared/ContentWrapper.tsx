"use client";

import { usePathname } from "next/navigation";

import { useChatOverlay } from "@/contexts/ChatContext";

const PUBLIC_PAGES = [
  "/",
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
];

export default function ContentWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { mode } = useChatOverlay();
  const isPublic = PUBLIC_PAGES.includes(pathname);

  if (isPublic) {
    return <>{children}</>;
  }

  const splitMargin = mode === "split" ? "lg:mr-[40%]" : "";

  return (
    <div
      className={`lg:ml-64 pt-14 pb-16 lg:pt-0 lg:pb-0 min-h-screen transition-[margin] duration-300 ease-in-out ${splitMargin}`}
    >
      {children}
    </div>
  );
}

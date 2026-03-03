"use client";

import { usePathname } from "next/navigation";

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
  const isPublic = PUBLIC_PAGES.includes(pathname);

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <div className="lg:ml-64 pt-14 pb-16 lg:pt-0 lg:pb-0 min-h-screen">
      {children}
    </div>
  );
}

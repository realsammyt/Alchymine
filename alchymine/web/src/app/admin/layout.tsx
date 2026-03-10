"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AdminRoute from "@/components/shared/AdminRoute";

const ADMIN_NAV = [
  { name: "Dashboard", href: "/admin/dashboard", icon: "chart" },
  { name: "Users", href: "/admin/users", icon: "users" },
  { name: "Invite Codes", href: "/admin/invite-codes", icon: "key" },
  { name: "Waitlist", href: "/admin/waitlist", icon: "mail" },
  { name: "Feedback", href: "/admin/feedback", icon: "chat" },
];

function AdminIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const base = `w-5 h-5 ${className}`;
  switch (icon) {
    case "chart":
      return (
        <svg
          className={base}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
    case "users":
      return (
        <svg
          className={base}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "key":
      return (
        <svg
          className={base}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" />
        </svg>
      );
    case "mail":
      return (
        <svg
          className={base}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect width="20" height="16" x="2" y="4" rx="2" />
          <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
        </svg>
      );
    case "chat":
      return (
        <svg
          className={base}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    default:
      return null;
  }
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <AdminRoute>
      <div className="min-h-screen flex">
        {/* Admin Sidebar */}
        <aside className="hidden lg:flex flex-col w-56 bg-surface border-r border-white/5 fixed left-64 top-0 bottom-0 z-30">
          <div className="p-4 border-b border-white/5">
            <h2 className="text-sm font-display text-primary tracking-wide uppercase">
              Admin Panel
            </h2>
          </div>
          <nav className="flex-1 px-3 py-4">
            <ul className="space-y-1" role="list">
              {ADMIN_NAV.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-body transition-colors ${
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-text/60 hover:text-text hover:bg-white/5"
                      }`}
                    >
                      <AdminIcon icon={item.icon} />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div className="p-4 border-t border-white/5">
            <Link
              href="/dashboard"
              className="text-xs text-text/40 hover:text-text/60 transition-colors"
            >
              Back to App
            </Link>
          </div>
        </aside>

        {/* Admin Content */}
        <main className="flex-1 lg:ml-56 p-6 lg:p-8">{children}</main>
      </div>
    </AdminRoute>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import { NavIcon } from "@/components/shared/Icons";

interface NavItem {
  name: string;
  href: string;
  icon: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: "home",
    label: "Dashboard overview",
  },
  {
    name: "Discover",
    href: "/discover",
    icon: "spiral",
    label: "Intake and assessment flow",
  },
  {
    name: "Intelligence",
    href: "/intelligence",
    icon: "brain",
    label: "Personalized Intelligence system",
  },
  {
    name: "Healing",
    href: "/healing",
    icon: "leaf",
    label: "Ethical Healing system",
  },
  {
    name: "Wealth",
    href: "/wealth",
    icon: "chart",
    label: "Generational Wealth system",
  },
  {
    name: "Creative",
    href: "/creative",
    icon: "palette",
    label: "Creative Development system",
  },
  {
    name: "Perspective",
    href: "/perspective",
    icon: "telescope",
    label: "Perspective Enhancement system",
  },
  {
    name: "Journal",
    href: "/journal",
    icon: "book",
    label: "Reflection journal",
  },
  {
    name: "Profile",
    href: "/profile",
    icon: "user",
    label: "Your unified profile",
  },
  {
    name: "About",
    href: "/about",
    icon: "info",
    label: "About Alchymine",
  },
];

export default function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Hide navigation on public pages (landing, auth)
  const publicPages = [
    "/",
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
  ];
  if (publicPages.includes(pathname)) {
    return null;
  }

  const isActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <nav
        className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 w-64 bg-surface border-r border-white/5 z-40"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="p-6 border-b border-white/5">
          <Link
            href="/"
            className="text-gradient-gold font-display text-2xl font-light tracking-wide block"
          >
            Alchymine
          </Link>
          <p className="text-xs text-text/40 mt-1 font-body">
            Transformation OS
          </p>
        </div>

        {/* Nav Items */}
        <ul className="flex-1 px-3 py-4 space-y-1" role="list">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  aria-label={item.label}
                  aria-current={active ? "page" : undefined}
                  className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-body transition-all duration-300 ease-out ${
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-text/60 hover:text-text hover:bg-white/5 hover:translate-x-0.5"
                  }`}
                >
                  <NavIcon icon={item.icon} className="w-5 h-5" />
                  {item.name}
                  {active && (
                    <span
                      className="absolute bottom-0 left-3 right-3 h-px rounded-full"
                      style={{
                        background:
                          "linear-gradient(90deg, transparent, rgba(218,165,32,0.6), transparent)",
                      }}
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {user?.is_admin && (
          <div className="px-3 pt-2 mt-2 border-t border-white/5">
            <Link
              href="/admin/dashboard"
              aria-label="Admin panel"
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-body transition-all duration-300 ease-out ${
                pathname.startsWith("/admin")
                  ? "bg-primary/10 text-primary"
                  : "text-text/60 hover:text-text hover:bg-white/5"
              }`}
            >
              <svg
                className="w-5 h-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              Admin
            </Link>
          </div>
        )}

        {/* Footer */}
        <div className="p-4 border-t border-white/5">
          {user ? (
            <div className="space-y-2">
              <p className="text-xs text-text/40 truncate">{user.email}</p>
              <button
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
                className="flex items-center gap-2 text-xs text-text/30 hover:text-text/50 transition-colors"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-2 text-xs text-text/30 hover:text-text/50 transition-colors"
            >
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              Sign In
            </Link>
          )}
        </div>
      </nav>

      {/* Mobile Top Bar */}
      <header className="lg:hidden fixed top-0 left-0 right-0 bg-surface/95 backdrop-blur-xl border-b border-white/5 z-50">
        <div className="flex items-center justify-between px-4 py-3">
          <Link
            href="/"
            className="text-gradient-gold font-display text-xl font-light tracking-wide"
          >
            Alchymine
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-text/60 hover:text-text rounded-lg hover:bg-white/5 transition-colors focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none"
            aria-label={
              mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"
            }
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-nav-menu"
          >
            {mobileMenuOpen ? (
              <svg
                className="w-6 h-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            ) : (
              <svg
                className="w-6 h-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <nav
            id="mobile-nav-menu"
            className="px-4 pb-4 animate-fade-in"
            aria-label="Main navigation"
          >
            <ul className="space-y-1" role="list">
              {NAV_ITEMS.map((item) => {
                const active = isActive(item.href);
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      aria-label={item.label}
                      aria-current={active ? "page" : undefined}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-text/60 hover:text-text hover:bg-white/5"
                      }`}
                    >
                      <NavIcon icon={item.icon} className="w-5 h-5" />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
              {user?.is_admin && (
                <li>
                  <Link
                    href="/admin/dashboard"
                    aria-label="Admin panel"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      pathname.startsWith("/admin")
                        ? "bg-primary/10 text-primary"
                        : "text-text/60 hover:text-text hover:bg-white/5"
                    }`}
                  >
                    <svg
                      className="w-5 h-5"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                    Admin
                  </Link>
                </li>
              )}
            </ul>
          </nav>
        )}
      </header>

      {/* Mobile Bottom Navigation */}
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 backdrop-blur-xl bg-surface/80 border-t border-white/5 z-50"
        aria-label="Quick navigation"
      >
        <ul className="flex items-center justify-around px-2 py-2" role="list">
          {NAV_ITEMS.slice(0, 6).map((item) => {
            const active = isActive(item.href);
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  aria-label={item.label}
                  aria-current={active ? "page" : undefined}
                  className={`touch-target-sm flex flex-col items-center justify-center gap-0.5 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-colors ${
                    active ? "text-primary" : "text-text/40 hover:text-text/60"
                  }`}
                >
                  <NavIcon
                    icon={item.icon}
                    className={`w-5 h-5 ${active ? "text-primary" : ""}`}
                  />
                  <span className="truncate max-w-[48px]">
                    {(
                      {
                        Dashboard: "Home",
                        Discover: "Discover",
                        Intelligence: "Mind",
                        Healing: "Heal",
                        Wealth: "Wealth",
                        Creative: "Create",
                        Perspective: "View",
                      } as Record<string, string>
                    )[item.name] ?? item.name}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}

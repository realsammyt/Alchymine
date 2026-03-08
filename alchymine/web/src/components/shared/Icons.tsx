/**
 * Shared SVG icon components used across the landing page and navigation.
 * Centralizes icon definitions to avoid duplication of SVG paths.
 */

import type { SVGProps } from "react";

interface IconProps extends SVGProps<SVGSVGElement> {
  className?: string;
}

const defaultProps: SVGProps<SVGSVGElement> = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

function Icon({ className, children, ...props }: IconProps) {
  return (
    <svg className={className} {...defaultProps} {...props}>
      {children}
    </svg>
  );
}

// ── System icons (five pillars) ───────────────────────────────────────

export function BrainIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M12 2a4 4 0 0 0-4 4v1a4 4 0 0 0-4 4c0 1.5.8 2.8 2 3.4V18a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-3.6c1.2-.6 2-1.9 2-3.4a4 4 0 0 0-4-4V6a4 4 0 0 0-4-4z" />
      <path d="M12 2v20" />
    </Icon>
  );
}

export function LeafIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </Icon>
  );
}

export function ChartIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </Icon>
  );
}

export function PaletteIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
    </Icon>
  );
}

export function TelescopeIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="m10.065 12.493-6.18 1.318a.934.934 0 0 1-1.108-.702l-.537-2.15a1.07 1.07 0 0 1 .691-1.265l13.504-4.44" />
      <path d="m13.56 11.747 4.332-.924" />
      <path d="m16.243 5.636 2.16.45a.93.93 0 0 1 .704 1.108l-.534 2.15a1.07 1.07 0 0 1-1.267.69l-2.455-.519" />
      <path d="m13.56 11.747-3.495 5.245" />
      <path d="m10.065 12.493-3.495 5.245" />
    </Icon>
  );
}

// ── Navigation-only icons ─────────────────────────────────────────────

export function HomeIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </Icon>
  );
}

export function SpiralIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M12 22c-4.97 0-9-4.03-9-9 0-3.87 2.55-7.16 6-8.27" />
      <path d="M12 18a6 6 0 0 1-6-6c0-2.58 1.67-4.78 4-5.6" />
      <path d="M12 14a2 2 0 0 1-2-2c0-.87.56-1.61 1.33-1.89" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </Icon>
  );
}

export function BookIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </Icon>
  );
}

export function UserIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </Icon>
  );
}

// ── Trust / utility icons ─────────────────────────────────────────────

export function CodeIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </Icon>
  );
}

export function LockIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </Icon>
  );
}

export function ShieldIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    </Icon>
  );
}

export function EyeIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </Icon>
  );
}

export function CheckIcon({ className, ...props }: IconProps) {
  return (
    <Icon className={className} {...props}>
      <polyline points="20 6 9 17 4 12" />
    </Icon>
  );
}

// ── Lookup helpers ────────────────────────────────────────────────────

const SYSTEM_ICONS: Record<string, React.ComponentType<IconProps>> = {
  brain: BrainIcon,
  leaf: LeafIcon,
  chart: ChartIcon,
  palette: PaletteIcon,
  telescope: TelescopeIcon,
};

const TRUST_ICONS: Record<string, React.ComponentType<IconProps>> = {
  code: CodeIcon,
  lock: LockIcon,
  shield: ShieldIcon,
  eye: EyeIcon,
};

const NAV_ICONS: Record<string, React.ComponentType<IconProps>> = {
  home: HomeIcon,
  spiral: SpiralIcon,
  brain: BrainIcon,
  leaf: LeafIcon,
  chart: ChartIcon,
  palette: PaletteIcon,
  telescope: TelescopeIcon,
  book: BookIcon,
  user: UserIcon,
};

/**
 * Render a system pillar icon by name.
 * Returns null for unknown icon names.
 */
export function SystemIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const IconComponent = SYSTEM_ICONS[icon];
  return IconComponent ? <IconComponent className={className} /> : null;
}

/**
 * Render a trust/ethics icon by name.
 * Returns null for unknown icon names.
 */
export function TrustIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const IconComponent = TRUST_ICONS[icon];
  return IconComponent ? <IconComponent className={className} /> : null;
}

/**
 * Render a navigation icon by name.
 * Returns null for unknown icon names.
 */
export function NavIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const IconComponent = NAV_ICONS[icon];
  return IconComponent ? <IconComponent className={className} /> : null;
}

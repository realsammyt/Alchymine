import Link from 'next/link';

export type SystemStatus = 'active' | 'coming-soon' | 'beta';

interface SystemCardProps {
  name: string;
  href: string;
  icon: React.ReactNode;
  description: string;
  status: SystemStatus;
  features: string[];
  gradient: string;
}

const statusConfig: Record<SystemStatus, { label: string; className: string }> = {
  active: {
    label: 'Active',
    className: 'bg-accent/20 text-accent',
  },
  beta: {
    label: 'Beta',
    className: 'bg-primary/20 text-primary',
  },
  'coming-soon': {
    label: 'Coming Soon',
    className: 'bg-secondary/20 text-secondary',
  },
};

export default function SystemCard({
  name,
  href,
  icon,
  description,
  status,
  features,
  gradient,
}: SystemCardProps) {
  const statusInfo = statusConfig[status];

  return (
    <Link
      href={href}
      className="group block card-surface p-6 transition-all duration-300 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      aria-label={`${name} system - ${description}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div
          className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-2xl`}
          aria-hidden="true"
        >
          {icon}
        </div>
        <span
          className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${statusInfo.className}`}
          role="status"
          aria-label={`Status: ${statusInfo.label}`}
        >
          {statusInfo.label}
        </span>
      </div>

      <h3 className="text-lg font-semibold text-text mb-2 group-hover:text-primary transition-colors">
        {name}
      </h3>

      <p className="text-text/50 text-sm leading-relaxed mb-4">
        {description}
      </p>

      <ul className="space-y-1.5" aria-label={`${name} features`}>
        {features.map((feature) => (
          <li key={feature} className="flex items-center gap-2 text-xs text-text/40">
            <span className="w-1 h-1 rounded-full bg-primary/50 flex-shrink-0" aria-hidden="true" />
            {feature}
          </li>
        ))}
      </ul>

      <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-1 text-xs text-primary/60 group-hover:text-primary transition-colors">
        Explore
        <svg
          className="w-3 h-3 transition-transform group-hover:translate-x-1"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M5 12h14" />
          <path d="m12 5 7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}

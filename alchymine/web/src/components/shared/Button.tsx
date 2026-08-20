"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-medium hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]",
  secondary:
    "bg-gradient-to-r from-secondary-dark to-secondary text-white font-medium hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-[0.98]",
  ghost:
    "border border-primary/30 text-primary font-medium hover:bg-primary/10 hover:border-primary/50 active:scale-[0.98]",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-sm rounded-lg",
  md: "px-6 py-3 text-base rounded-xl",
  lg: "px-8 py-4 text-lg rounded-xl",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      className = "",
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        // ring-primary/60, not the /50 this carried before: /50 computes
        // 2.92:1 against the page background, under the 3:1 WCAG 1.4.11
        // asks of a focus indicator. /60 clears it at 3.74:1 on the
        // background and 3.55:1 on a card surface. The rest of the
        // repo's /40 and /50 rings are tracked in issue #275.
        className={`inline-flex items-center justify-center gap-2 font-body font-medium tracking-wide transition-all duration-300 ease-out disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:active:scale-100 focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {loading && <span className="sr-only">Loading</span>}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export default Button;

import type { ComponentProps } from "react";
import { cn } from "./cn";
import { Icon, type IconName } from "./icons";
import { Tooltip } from "./tooltip";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const base =
  "relative inline-flex min-h-11 min-w-11 select-none items-center justify-center gap-2 rounded-md px-4 font-sans text-step-0 font-semibold transition-transform duration-(--duration-fast) ease-out active:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50";
const variants: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg shadow-paper hover:-translate-y-px",
  secondary: "border border-ink/40 bg-card text-ink shadow-paper hover:-translate-y-px",
  ghost: "text-ink hover:bg-ink/5",
  danger: "bg-danger text-paper shadow-paper hover:-translate-y-px",
};

/** Class string for anything that must look like a button (e.g. a Next `Link`). */
export const buttonClass = (variant: Variant = "primary", className?: string) =>
  cn(base, variants[variant], className);

export type ButtonProps = ComponentProps<"button"> & { variant?: Variant; loading?: boolean };

export function Button({
  variant = "primary",
  loading,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, className)}
      {...rest}
    >
      {children}
      {loading && <span className="sr-only">Working…</span>}
    </button>
  );
}

/** Icon-only button. `label` is required: it is the accessible name and the tooltip. */
export function IconButton({
  label,
  icon,
  variant = "ghost",
  className,
  type = "button",
  ...rest
}: Omit<ButtonProps, "children" | "loading"> & { label: string; icon: IconName }) {
  return (
    <Tooltip content={label}>
      <button
        type={type}
        aria-label={label}
        className={buttonClass(variant, cn("px-0", className))}
        {...rest}
      >
        <Icon name={icon} />
      </button>
    </Tooltip>
  );
}

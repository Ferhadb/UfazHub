import type { ReactNode } from "react";
import { cn } from "./cn";
import { Icon, type IconName } from "./icons";

type Tone = "info" | "success" | "warning" | "danger";
const tones: Record<Tone, { box: string; icon: IconName }> = {
  info: { box: "border-l-accent", icon: "info" },
  success: { box: "border-l-success", icon: "check" },
  warning: { box: "border-l-warning", icon: "alert" },
  danger: { box: "border-l-danger", icon: "alert" },
};
const iconColor: Record<Tone, string> = {
  info: "text-accent",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

/** A margin note boxed in: danger interrupts screen readers (role=alert), the rest are notes. */
export function Callout({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "note"}
      className={cn(
        "bg-card border-rule flex gap-3 rounded-md border border-l-4 p-4",
        tones[tone].box,
        className,
      )}
    >
      <Icon name={tones[tone].icon} className={cn("mt-0.5 shrink-0", iconColor[tone])} />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div className="text-muted">{children}</div>
      </div>
    </div>
  );
}

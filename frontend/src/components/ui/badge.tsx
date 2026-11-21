import type { ComponentProps } from "react";
import { cn, tintBorder, tintText, type Tint } from "./cn";

export type BadgeTone = Tint | "neutral" | "flame";

const toneClass: Record<BadgeTone, string> = {
  neutral: "border-ink/50 text-ink",
  flame: "border-flame-text text-flame-text",
  ...Object.fromEntries(
    (Object.keys(tintText) as Tint[]).map((t) => [t, `${tintBorder[t]} ${tintText[t]}`]),
  ),
} as Record<BadgeTone, string>;

/** Small quiet label, set in mono like a call number. */
export function Badge({
  tone = "neutral",
  className,
  ...rest
}: { tone?: BadgeTone } & ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "text-step--1 inline-flex items-center rounded-sm border px-2 py-0.5 font-mono tracking-widest uppercase",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}

/** Rubber stamp: bold double rule, tilted 2-4 degrees, thunks in when it appears. */
export function Stamp({
  tone = "flame",
  tilt = 3,
  className,
  style,
  ...rest
}: { tone?: BadgeTone; tilt?: number } & ComponentProps<"span">) {
  return (
    <span
      style={{ rotate: `${tilt}deg`, ...style }}
      className={cn(
        "anim-thunk text-step--1 inline-block rounded-sm border-2 px-2 py-0.5 font-mono font-bold tracking-widest uppercase outline-1 -outline-offset-5",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}

import { useId } from "react";
import { cn } from "./cn";

/* Original geometric ornaments (carpet and tile geometry, drawn from scratch: eight-point stars,
 * lattices, interlaced bands). They use currentColor at low opacity, so they sit behind content. */
export const ornamentVariants = ["star", "lattice", "rosette", "weave", "band", "chain"] as const;
export type OrnamentVariant = (typeof ornamentVariants)[number];

const tiles: Record<OrnamentVariant, { w: number; h: number; body: React.ReactNode }> = {
  // Eight-point star: two squares, one turned 45 degrees, with a centre dot.
  star: {
    w: 48,
    h: 48,
    body: (
      <>
        <rect x="12" y="12" width="24" height="24" />
        <rect x="12" y="12" width="24" height="24" transform="rotate(45 24 24)" />
        <circle cx="24" cy="24" r="3" />
        <path d="M0 0l6 6M48 0l-6 6M0 48l6-6M48 48l-6-6" />
      </>
    ),
  },
  // Diamond lattice with nested diamonds.
  lattice: {
    w: 32,
    h: 32,
    body: (
      <>
        <path d="M16 0l16 16-16 16L0 16Z" />
        <path d="M16 8l8 8-8 8-8-8Z" />
      </>
    ),
  },
  // Six-fold rosette from overlapping circles.
  rosette: {
    w: 40,
    h: 40,
    body: (
      <>
        <circle cx="20" cy="20" r="10" />
        <circle cx="20" cy="10" r="10" />
        <circle cx="20" cy="30" r="10" />
        <circle cx="10.6" cy="15" r="10" />
        <circle cx="29.4" cy="25" r="10" />
      </>
    ),
  },
  // Over-under weave of two crossing stripes.
  weave: {
    w: 24,
    h: 24,
    body: (
      <>
        <path d="M0 6h24M0 18h24" />
        <path d="M6 0v10M6 14v10M18 0v4M18 8v8M18 20v4" />
      </>
    ),
  },
  // Divider band: chain of diamonds between two rules.
  band: {
    w: 24,
    h: 16,
    body: (
      <>
        <path d="M0 2h24M0 14h24" />
        <path d="M12 3l5 5-5 5-5-5Z" />
      </>
    ),
  },
  // Chain of linked octagons, for headers and footers.
  chain: {
    w: 28,
    h: 16,
    body: (
      <>
        <path d="M5 8l3-5h6l3 5-3 5H8Z" />
        <path d="M17 8h5M0 8h2" />
      </>
    ),
  },
};

export function Ornament({
  variant = "star",
  className,
  strength = 0.07,
}: {
  variant?: OrnamentVariant;
  className?: string;
  /** Opacity; 0.04 to 0.08 behind text, higher for dividers. */
  strength?: number;
}) {
  const id = useId();
  const { w, h, body } = tiles[variant];
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={cn("pointer-events-none text-current", className)}
      style={{ opacity: strength }}
      width="100%"
      height="100%"
    >
      <defs>
        <pattern id={id} width={w} height={h} patternUnits="userSpaceOnUse">
          <g fill="none" stroke="currentColor" strokeWidth="1" strokeLinejoin="round">
            {body}
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}

/** A horizontal divider built from the band ornament. */
export function OrnamentDivider({ className }: { className?: string }) {
  return (
    <div role="separator" className={cn("text-ink h-4 w-full", className)}>
      <Ornament variant="band" strength={0.35} />
    </div>
  );
}

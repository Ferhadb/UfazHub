import type { SVGProps } from "react";

/* Loose line illustrations for empty, 404 and error states. Ink strokes, one flame accent.
 * Decorative: the surrounding text carries the meaning. */
function Frame(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 160 120"
      width="160"
      height="120"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    />
  );
}

const flame = { stroke: "var(--flame)" };

/** An empty card-catalogue drawer. */
export function EmptyDrawer(props: SVGProps<SVGSVGElement>) {
  return (
    <Frame {...props}>
      <path d="M22 44c40-3 76-3 116 0l4 52c-45 3-82 3-124 0Z" />
      <path d="M26 44l8-14c30-3 62-3 92 0l8 14" />
      <path d="M64 66c10-2 22-2 32 0M66 78c9 1 19 1 28 0" />
      <path d="M72 58c5-2 11-2 16 0" {...flame} />
    </Frame>
  );
}

/** Footprints walking off the page (first to arrive). */
export function Footprints(props: SVGProps<SVGSVGElement>) {
  return (
    <Frame {...props}>
      <path d="M42 82c-8-1-12-10-8-18s12-10 16-4 1 20-8 22ZM44 92c2 4 7 3 8-1" />
      <path d="M92 52c-8-1-12-10-8-18s12-10 16-4 1 20-8 22ZM94 62c2 4 7 3 8-1" {...flame} />
      <path d="M124 24l8-6M128 34l10-2" strokeDasharray="1 7" />
    </Frame>
  );
}

/** A catalogue card with a torn corner: nothing found. */
export function LostCard(props: SVGProps<SVGSVGElement>) {
  return (
    <Frame {...props}>
      <path d="M30 22c34-3 66-3 98 0l1 56-9 8 4 12c-30 2-64 2-96 0Z" />
      <path d="M44 42c22-2 44-2 70 0M44 56c18-1 36-1 52 0" />
      <path d="M96 72c6 4 14 4 20-2" {...flame} />
      <circle cx="108" cy="48" r="9" {...flame} />
    </Frame>
  );
}

/** A tipped inkwell: something broke. */
export function Inkwell(props: SVGProps<SVGSVGElement>) {
  return (
    <Frame {...props}>
      <path d="M50 52l34-14 24 36-34 14Z" />
      <path d="M86 38l6-10 10 5-4 10" />
      <path d="M104 78c10 6 20 8 34 6-6 10-22 14-38 8" {...flame} />
      <path d="M22 100c30 3 80 3 118 0" />
    </Frame>
  );
}

/** A compass: lost, or just browsing. */
export function Compass(props: SVGProps<SVGSVGElement>) {
  return (
    <Frame {...props}>
      <circle cx="80" cy="60" r="38" />
      <circle cx="80" cy="60" r="31" strokeDasharray="2 6" />
      <path d="M64 76l8-24 24-8-8 24Z" />
      <path d="M72 52l16-8" {...flame} />
      <path d="M80 18v6M80 96v6M38 60h6M116 60h6" />
    </Frame>
  );
}

export const illustrations = { EmptyDrawer, Footprints, LostCard, Inkwell, Compass };

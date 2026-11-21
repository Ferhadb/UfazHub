/** Bookmark-ribbon progress: a ribbon hangs from the top edge and lengthens as you read (transform only). */
export function Ribbon({ progress }: { progress: number }) {
  const pct = Math.round(progress * 100);
  return (
    <div
      role="progressbar"
      aria-label="Reading progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      className="no-print pointer-events-none fixed top-0 right-3 z-20 h-dvh w-3 sm:right-6 sm:w-4"
    >
      <div
        className="bg-flame h-full origin-top [clip-path:polygon(0_0,100%_0,100%_100%,50%_calc(100%-10px),0_100%)] motion-safe:transition-transform motion-safe:duration-150"
        style={{ transform: `scaleY(${Math.max(progress, 0.02)})` }}
      />
    </div>
  );
}

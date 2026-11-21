import { cn, tintText, type Tint } from "./cn";

const tints = Object.keys(tintText) as Tint[];
const bg: Record<Tint, string> = {
  resource: "bg-card border-resource",
  article: "bg-card border-article",
  collection: "bg-card border-collection",
  question: "bg-card border-question",
  research: "bg-card border-research",
};

const initials = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => [...w][0]?.toLocaleUpperCase() ?? "")
    .join("");

/** Image avatar, or initials on a tint picked from the name (stable per person). */
export function Avatar({
  name,
  src,
  size = 40,
  className,
}: {
  name: string;
  src?: string;
  size?: number;
  className?: string;
}) {
  const tint = tints[[...name].reduce((n, c) => n + c.charCodeAt(0), 0) % tints.length]!;
  return (
    <span
      role="img"
      aria-label={name}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      className={cn(
        "inline-grid shrink-0 place-items-center overflow-hidden rounded-full border font-mono font-bold",
        bg[tint],
        tintText[tint],
        className,
      )}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element -- user uploads arrive pre-sized in slice 4
        <img src={src} alt="" width={size} height={size} className="size-full object-cover" />
      ) : (
        <span aria-hidden="true">{initials(name)}</span>
      )}
    </span>
  );
}

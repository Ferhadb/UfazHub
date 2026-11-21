import { parseHighlight } from "@/lib/search/highlight";

/** Renders API-highlighted text as React nodes (no innerHTML): matches get the highlighter swipe. */
export function Highlight({ text }: { text: string }) {
  return (
    <>
      {parseHighlight(text).map((run, i) =>
        run.hit ? (
          <mark
            key={i}
            className="text-on-highlighter bg-highlighter rounded-sm [box-decoration-break:clone] px-0.5"
          >
            {run.text}
          </mark>
        ) : (
          <span key={i}>{run.text}</span>
        ),
      )}
    </>
  );
}

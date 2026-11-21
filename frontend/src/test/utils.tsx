import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { ToastProvider } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Resource } from "@/lib/api/content";

export function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <TooltipProvider>
          <ToastProvider>{ui}</ToastProvider>
        </TooltipProvider>
      </QueryClientProvider>,
    ),
  };
}

export const resource = (over: Partial<Resource> = {}): Resource => ({
  id: "11111111-1111-1111-1111-111111111111",
  type: "resource",
  call_number: "RES-0421",
  title: "Linear Algebra Done Right",
  description: "A proof-first textbook that pairs well with the L2 algebra course.",
  status: "published",
  is_research: false,
  author: { id: "u1", display_name: "Aygün", reputation: 0, cosmetics: {} },
  tags: ["algebra"],
  vote_score: 3,
  bookmark_count: 1,
  comment_count: 0,
  view_count: 0,
  resource_type: "book",
  category: "Mathematics",
  difficulty: "intermediate",
  time_commitment_minutes: 600,
  prerequisites: "",
  best_part: "",
  warning: "",
  student_note: "",
  links: [{ id: "l1", url: "https://example.org/a", label: "PDF", health: "ok" }],
  created_at: "2026-01-01T00:00:00Z",
  my_vote: 0,
  bookmarked: false,
  ...over,
});

type Handler = (req: Request) => Response | Promise<Response>;

/** Stub fetch with `"METHOD /path": handler`; unmatched requests fail the test loudly. */
export function stubApi(routes: Record<string, Handler>) {
  const fn = vi.fn(async (req: Request) => {
    const key = `${req.method} ${new URL(req.url).pathname}`;
    const h = routes[key];
    if (!h) throw new Error(`unexpected request: ${key}`);
    return h(req);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const page = (items: unknown[], next: string | null = null) =>
  Response.json({ items, next_cursor: next });

export const comment = (over: Record<string, unknown> = {}) => ({
  id: "c1",
  item_id: "11111111-1111-1111-1111-111111111111",
  parent_id: null,
  body: "Great find",
  author: { id: "u2", display_name: "Leyla" },
  created_at: "2026-01-02T00:00:00Z",
  replies: [],
  reply_count: 0,
  ...over,
});

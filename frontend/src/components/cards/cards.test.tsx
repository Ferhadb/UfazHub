import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { ForYouView } from "./for-you-view";
import { itemHref } from "./item-card";
import { ResearchView } from "./research-view";

const replace = vi.fn();
let session: { status: string; user: { id: string } | null };
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, push: vi.fn() }) }));
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session }));
afterEach(() => vi.unstubAllGlobals());
beforeEach(() => {
  session = { status: "authenticated", user: { id: "u1" } };
  replace.mockClear();
});

const card = (over: Record<string, unknown> = {}) => ({
  id: "i1",
  type: "article",
  call_number: "ART-0001",
  title: "A survey of Caspian geology",
  description: "d",
  is_research: true,
  author: { id: "u2", display_name: "Leyla", reputation: 0 },
  tags: [],
  vote_score: 1,
  comment_count: 0,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

it("links every content type to its own section", () => {
  expect(
    (["resource", "article", "collection", "question"] as const).map((type) =>
      itemHref({ type, call_number: "X-1" }),
    ),
  ).toEqual(["/resources/X-1", "/articles/X-1", "/collections/X-1", "/questions/X-1"]);
});

describe("ResearchView", () => {
  it("lists research across types and filters by type", async () => {
    const types: (string | null)[] = [];
    stubApi({
      "GET /api/research": (req) => {
        types.push(new URL(req.url).searchParams.get("type"));
        return page([card()]);
      },
    });
    renderWithProviders(<ResearchView />);
    expect(
      await screen.findByRole("link", { name: "A survey of Caspian geology" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Collections" }));
    await waitFor(() => expect(types.at(-1)).toBe("collection"));
  });

  it("has an empty state", async () => {
    stubApi({ "GET /api/research": () => page([]) });
    renderWithProviders(<ResearchView />);
    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });

  it("pages with load more", async () => {
    stubApi({
      "GET /api/research": (req) =>
        new URL(req.url).searchParams.has("cursor")
          ? page([card({ id: "i2", title: "Second" })])
          : page([card()], "next"),
    });
    renderWithProviders(<ResearchView />);
    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByRole("link", { name: "Second" })).toBeInTheDocument();
  });
});

describe("ForYouView", () => {
  it("toggles a followed tag and refreshes the feed", async () => {
    let followed: { name: string; slug: string }[] = [];
    let feedCalls = 0;
    stubApi({
      "GET /api/tags": () => page([{ name: "Algorithms", slug: "algorithms", count: 3 }]),
      "GET /api/me/tags": () => Response.json(followed),
      "GET /api/feed/for-you": () => {
        feedCalls++;
        return page(followed.length ? [card({ is_research: false })] : []);
      },
      "PUT /api/tags/algorithms/follow": () => {
        followed = [{ name: "Algorithms", slug: "algorithms" }];
        return Response.json({ following: true });
      },
    });
    renderWithProviders(<ForYouView />);
    expect(await screen.findByText("Your shelf is empty")).toBeInTheDocument();
    const btn = await screen.findByRole("button", { name: "#Algorithms" });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    expect(
      await screen.findByRole("link", { name: "A survey of Caspian geology" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "#Algorithms" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(feedCalls).toBeGreaterThan(1);
  });

  it("sends signed-out visitors to sign in", () => {
    session = { status: "anonymous", user: null };
    stubApi({ "GET /api/tags": () => page([]) });
    renderWithProviders(<ForYouView />);
    expect(replace).toHaveBeenCalledWith("/signin?next=/for-you");
  });
});

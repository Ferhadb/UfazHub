import { screen } from "@testing-library/react";
import { page, renderWithProviders, resource, stubApi } from "@/test/utils";
import { ArticleReader } from "./reader";

vi.mock("next/navigation", () => ({ usePathname: () => "/articles/x", useRouter: () => ({}) }));
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({
    status: "authenticated",
    user: { id: "u1", role: "student", email_verified: true },
  }),
}));
afterEach(() => vi.unstubAllGlobals());

const article = {
  ...resource({ call_number: "ART-0001", title: "On Proofs" }),
  type: "article",
  slug: "on-proofs",
  body_md: "x",
  body_html: "<p>Opening.</p><h2>First</h2><p>text</p><h2>Second</h2><p>more</p>",
  toc: [
    { level: 2, text: "First" },
    { level: 2, text: "Second" },
  ],
  reading_minutes: 4,
  cover: null,
  published_at: "2026-01-01T00:00:00Z",
};

describe("ArticleReader", () => {
  it("renders the article with a progress ribbon, TOC and note column", async () => {
    stubApi({
      "GET /api/articles/on-proofs": () => Response.json(article),
      [`GET /api/content/${article.id}/comments`]: () => page([]),
    });
    renderWithProviders(<ArticleReader refId="on-proofs" />);
    expect(await screen.findByRole("heading", { level: 1, name: "On Proofs" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    const toc = screen.getByRole("navigation", { name: "In this article" });
    expect(toc).toHaveTextContent("Second");
    expect(await screen.findByRole("heading", { level: 2, name: "First" })).toHaveAttribute(
      "id",
      "section-0",
    );
    expect(screen.getByText("4 min read")).toBeInTheDocument();
  });

  it("explains a missing article", async () => {
    stubApi({
      "GET /api/articles/nope": () =>
        Response.json({ code: "not_found", message: "no" }, { status: 404 }),
    });
    renderWithProviders(<ArticleReader refId="nope" />);
    expect(await screen.findByText("That page is not in the binding")).toBeInTheDocument();
  });
});

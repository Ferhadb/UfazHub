import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonLd, publicArticle, publicArticleCards } from "./seo";

afterEach(() => vi.unstubAllGlobals());

describe("public SEO data", () => {
  it("escapes markup in structured data", () => {
    expect(jsonLd({ headline: "</script><script>bad</script>" })).not.toContain("<");
  });

  it("omits unpublished articles", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "draft" }),
      }),
    );
    expect(await publicArticle("draft-article")).toBeNull();
  });

  it("paginates published articles for the sitemap", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            { status: "published", slug: "first" },
            { status: "draft", slug: "draft" },
          ],
          next_cursor: "page-two",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [{ status: "published", slug: "second" }], next_cursor: null }),
      });
    vi.stubGlobal("fetch", fetchMock);
    expect((await publicArticleCards()).map(({ slug }) => slug)).toEqual(["first", "second"]);
    expect(fetchMock.mock.calls[1]?.[0].searchParams.get("cursor")).toBe("page-two");
  });
});

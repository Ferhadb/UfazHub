import type { components } from "@/lib/api/schema";

export const siteUrl = new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://ufazhub.xyz");

export type PublicArticle = components["schemas"]["ArticleOut"];
export type PublicArticleCard = components["schemas"]["ArticleCard"];
type PublicContent = { call_number: string; status: string; created_at: string };

export function apiUrl(path: string): string {
  return new URL(path, process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000").toString();
}

export async function publicArticle(ref: string): Promise<PublicArticle | null> {
  try {
    const response = await fetch(apiUrl(`/api/articles/${encodeURIComponent(ref)}`), {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) return null;
    const article = (await response.json()) as PublicArticle;
    return article.status === "published" ? article : null;
  } catch {
    return null;
  }
}

export async function publicArticleCards(): Promise<PublicArticleCard[]> {
  return publicList<PublicArticleCard>("articles");
}

export async function publicContentPaths(): Promise<Array<{ path: string; createdAt: string }>> {
  const kinds = ["resources", "collections", "questions"] as const;
  const lists = await Promise.all(kinds.map((kind) => publicList<PublicContent>(kind)));
  return lists.flatMap((items, index) =>
    items.map((item) => ({
      path: `/${kinds[index]}/${encodeURIComponent(item.call_number)}`,
      createdAt: item.created_at,
    })),
  );
}

async function publicList<T extends { status: string }>(kind: string): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  // Keep sitemap generation bounded if the API is unexpectedly cyclic.
  for (let page = 0; page < 100; page++) {
    try {
      const url = new URL(apiUrl(`/api/${kind}`));
      url.searchParams.set("limit", "50");
      if (cursor) url.searchParams.set("cursor", cursor);
      const response = await fetch(url, {
        next: { revalidate: 3600 },
        signal: AbortSignal.timeout(3000),
      });
      if (!response.ok) break;
      const result = (await response.json()) as {
        items: T[];
        next_cursor: string | null;
      };
      items.push(...result.items.filter((item) => item.status === "published"));
      if (!result.next_cursor || result.next_cursor === cursor) break;
      cursor = result.next_cursor;
    } catch {
      break;
    }
  }
  return items;
}

export function jsonLd(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

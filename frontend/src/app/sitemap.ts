import type { MetadataRoute } from "next";
import { publicArticleCards, publicContentPaths, siteUrl } from "@/lib/seo";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes = [
    "",
    "/resources",
    "/articles",
    "/collections",
    "/questions",
    "/courses",
    "/research",
    "/people",
    "/privacy",
  ];
  const [articles, content] = await Promise.all([publicArticleCards(), publicContentPaths()]);
  return [
    ...staticRoutes.map((route) => ({ url: new URL(route || "/", siteUrl).toString() })),
    ...articles.map((article) => ({
      url: new URL(`/articles/${encodeURIComponent(article.slug)}`, siteUrl).toString(),
      lastModified: article.updated_at,
    })),
    ...content.map((item) => ({
      url: new URL(item.path, siteUrl).toString(),
      lastModified: item.createdAt,
    })),
  ];
}

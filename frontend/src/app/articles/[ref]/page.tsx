import type { Metadata } from "next";
import { ArticleReader } from "@/components/articles/reader";
import { jsonLd, publicArticle, siteUrl } from "@/lib/seo";

type Props = { params: Promise<{ ref: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ref } = await params;
  const article = await publicArticle(ref);
  if (!article) return { title: "Article", robots: { index: false, follow: false } };
  const url = `/articles/${encodeURIComponent(article.slug)}`;
  return {
    title: article.title,
    description: article.excerpt,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      title: article.title,
      description: article.excerpt,
      url,
      publishedTime: article.published_at ?? undefined,
      modifiedTime: article.updated_at,
      authors: [article.author.display_name],
      images: [article.cover?.urls.lg ?? "/opengraph-image"],
    },
  };
}

export default async function Page({ params }: Props) {
  const { ref } = await params;
  const article = await publicArticle(ref);
  return (
    <>
      {article && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: jsonLd({
              "@context": "https://schema.org",
              "@type": "Article",
              headline: article.title,
              description: article.excerpt,
              datePublished: article.published_at ?? article.created_at,
              dateModified: article.updated_at,
              author: { "@type": "Person", name: article.author.display_name },
              publisher: { "@type": "Organization", name: "UFAZ Hub" },
              mainEntityOfPage: new URL(
                `/articles/${encodeURIComponent(article.slug)}`,
                siteUrl,
              ).toString(),
              ...(article.cover && { image: article.cover.urls.lg }),
            }),
          }}
        />
      )}
      <ArticleReader refId={ref} />
    </>
  );
}

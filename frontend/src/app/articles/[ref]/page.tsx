import type { Metadata } from "next";
import { ArticleReader } from "@/components/articles/reader";

export const metadata: Metadata = { title: "Article" };

export default async function Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  return <ArticleReader refId={ref} />;
}

import type { Metadata } from "next";
import { EditArticle } from "@/components/articles/edit-article";

export const metadata: Metadata = { title: "Edit article" };

export default async function Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  return <EditArticle refId={ref} />;
}

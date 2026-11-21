import type { Metadata } from "next";
import { CollectionDetail } from "@/components/collections/collection-detail";

export const metadata: Metadata = { title: "Collection" };

export default async function Page({ params }: { params: Promise<{ callNumber: string }> }) {
  const { callNumber } = await params;
  return <CollectionDetail callNumber={callNumber} />;
}

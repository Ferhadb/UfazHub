import type { Metadata } from "next";
import { ResourceDetail } from "./detail";

export const metadata: Metadata = { title: "Resource" };

export default async function Page({ params }: { params: Promise<{ callNumber: string }> }) {
  const { callNumber } = await params;
  return <ResourceDetail callNumber={callNumber} />;
}

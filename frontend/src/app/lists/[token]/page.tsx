import type { Metadata } from "next";
import { SharedListView } from "@/components/lists/shared-list-view";

// A shared link is a capability: keep it out of search engines and referrers.
export const metadata: Metadata = {
  title: "Reading list",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default async function Page({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <SharedListView token={token} />;
}

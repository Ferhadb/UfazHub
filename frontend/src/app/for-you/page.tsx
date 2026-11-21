import type { Metadata } from "next";
import { ForYouView } from "@/components/cards/for-you-view";

export const metadata: Metadata = { title: "For you" };

export default function Page() {
  return <ForYouView />;
}

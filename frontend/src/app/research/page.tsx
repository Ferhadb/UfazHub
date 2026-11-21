import type { Metadata } from "next";
import { ResearchView } from "@/components/cards/research-view";

export const metadata: Metadata = { title: "Research" };

export default function Page() {
  return <ResearchView />;
}

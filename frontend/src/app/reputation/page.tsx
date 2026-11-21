import type { Metadata } from "next";
import { ReputationView } from "@/components/reputation/reputation-view";

export const metadata: Metadata = { title: "How reputation works" };

export default function Page() {
  return <ReputationView />;
}

import type { Metadata } from "next";
import { QuestionsView } from "@/components/qa/questions-view";

export const metadata: Metadata = { title: "Questions" };

export default function Page() {
  return <QuestionsView />;
}

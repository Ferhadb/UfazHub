import type { Metadata } from "next";
import { Suspense } from "react";
import { QuestionThread } from "@/components/qa/question-thread";

export const metadata: Metadata = { title: "Question" };

export default async function Page({ params }: { params: Promise<{ callNumber: string }> }) {
  const { callNumber } = await params;
  return (
    <Suspense>
      <QuestionThread callNumber={callNumber} />
    </Suspense>
  );
}

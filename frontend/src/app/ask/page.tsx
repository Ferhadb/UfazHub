import type { Metadata } from "next";
import { AskForm } from "@/components/qa/ask-form";

export const metadata: Metadata = { title: "Ask a question" };

export default function Page() {
  return (
    <main id="main" className="relative z-10 mx-auto max-w-2xl px-4 py-8 sm:py-12">
      <p className="text-step--1 text-question font-mono tracking-widest uppercase">
        Catalogue · Questions
      </p>
      <h1 className="font-display text-step-4 mt-1">Ask a question</h1>
      <AskForm />
    </main>
  );
}

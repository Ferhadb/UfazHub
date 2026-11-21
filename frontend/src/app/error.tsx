"use client";

import { Inkwell } from "@/components/ui/illustrations";
import { Button } from "@/components/ui/button";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main
      id="main"
      role="alert"
      className="relative z-10 mx-auto flex min-h-[70dvh] max-w-3xl flex-col items-center justify-center px-4 py-12 text-center"
    >
      <Inkwell className="text-ink size-40" />
      <p className="text-step--1 text-flame-text mt-5 font-mono tracking-widest">
        A SPILL IN THE ARCHIVE
      </p>
      <h1 className="font-display text-step-4 mt-3">The inkwell tipped over.</h1>
      <p className="text-muted mt-4">
        We could not open this page. The shelves should be back in order shortly.
      </p>
      <Button className="mt-8" onClick={reset}>
        Try this page again
      </Button>
    </main>
  );
}

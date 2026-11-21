import Link from "next/link";
import { LostCard } from "@/components/ui/illustrations";

export default function NotFound() {
  return (
    <main
      id="main"
      className="relative z-10 mx-auto flex min-h-[70dvh] max-w-3xl flex-col items-center justify-center px-4 py-12 text-center"
    >
      <LostCard className="text-ink size-40" />
      <p className="text-step--1 text-flame-text mt-5 font-mono tracking-widest">404 / MISFILED</p>
      <h1 className="font-display text-step-4 mt-3">This card escaped the catalogue.</h1>
      <p className="text-muted mt-4">
        The page may have moved, or perhaps it was only a rumour in the margins.
      </p>
      <Link
        href="/"
        className="bg-accent text-accent-fg mt-8 inline-flex min-h-11 items-center rounded-md px-5 font-semibold"
      >
        Back to the library
      </Link>
    </main>
  );
}

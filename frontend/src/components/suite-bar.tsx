import { GPA_URL } from "@/lib/gpa";

/** Thin strip shared with UFAZ GPA: the two products read as one student suite. */
export function SuiteBar() {
  const item = "inline-flex min-h-8 items-center px-3 font-mono tracking-widest uppercase";
  return (
    <div className="border-rule bg-ink/5 text-step--1 border-b">
      <nav
        aria-label="UFAZ student suite"
        className="mx-auto flex max-w-6xl items-center px-1 sm:px-6"
      >
        <a href={GPA_URL} className={`${item} text-muted hover:text-ink`}>
          UFAZ GPA <span aria-hidden>↗</span>
        </a>
        <span aria-current="page" className={`${item} text-flame-text font-semibold`}>
          UFAZ Hub
        </span>
        <span className="text-muted ml-auto hidden px-3 sm:inline">One sign-in, two apps</span>
      </nav>
    </div>
  );
}

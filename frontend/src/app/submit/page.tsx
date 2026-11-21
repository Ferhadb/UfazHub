import type { Metadata } from "next";
import { Suspense } from "react";
import { Composer } from "./composer";

export const metadata: Metadata = { title: "Add to the library" };

export default function Page() {
  return (
    <Suspense>
      <Composer />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPassword } from "./reset";

export const metadata: Metadata = { title: "Reset password" };

export default function Page() {
  return (
    <Suspense>
      <ResetPassword />
    </Suspense>
  );
}

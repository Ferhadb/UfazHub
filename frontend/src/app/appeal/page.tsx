import type { Metadata } from "next";
import { AppealForm } from "./form";

export const metadata: Metadata = { title: "Appeal a suspension" };

export default function Page() {
  return <AppealForm />;
}

import type { Metadata } from "next";
import { SubmitForm } from "./form";

export const metadata: Metadata = { title: "Submit a resource" };

export default function Page() {
  return <SubmitForm />;
}

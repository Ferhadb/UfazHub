import type { Metadata } from "next";
import { AdminPanel } from "@/components/admin/admin-panel";

export const metadata: Metadata = { title: "Admin" };

export default function Page() {
  return <AdminPanel />;
}

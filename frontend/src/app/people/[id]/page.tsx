import type { Metadata } from "next";
import { ProfileView } from "@/components/people/profile-view";

export const metadata: Metadata = { title: "Profile" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProfileView id={id} />;
}

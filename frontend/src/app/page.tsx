import type { Metadata } from "next";
import { HomeContents } from "@/components/home/home-contents";

export const metadata: Metadata = {
  title: { absolute: "UFAZ Hub" },
  alternates: { canonical: "/" },
};

export default function Home() {
  return <HomeContents />;
}

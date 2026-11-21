import type { Metadata } from "next";
import { DesignGallery } from "./gallery";

export const metadata: Metadata = { title: "Design system" };

export default function Page() {
  return <DesignGallery />;
}

import type { Metadata } from "next";
import { BookmarksView } from "@/components/lists/bookmarks-view";

export const metadata: Metadata = { title: "Your shelf" };

export default function Page() {
  return <BookmarksView />;
}

import type { Metadata } from "next";
import { CourseView } from "@/components/courses/course-view";

export const metadata: Metadata = { title: "Course" };

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <CourseView slug={slug} />;
}

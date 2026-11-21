import { notFound, redirect } from "next/navigation";

/** GPA profiles link here with the Unistra id; we forward to the Hub profile. */
export default async function Page({ params }: { params: Promise<{ gpaId: string }> }) {
  const { gpaId } = await params;
  const base = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${base}/api/people/by-gpa/${encodeURIComponent(gpaId)}`, {
    cache: "no-store",
  }).catch(() => null);
  if (!res?.ok) notFound();
  redirect(`/people/${(await res.json()).id}`);
}

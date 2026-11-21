import type { Metadata } from "next";
import { cookies } from "next/headers";
import { localeCookie, resolveLocale } from "@/i18n/config";
import { messagesFor } from "@/i18n/messages";

export const metadata: Metadata = { title: "Privacy", alternates: { canonical: "/privacy" } };

export default async function PrivacyPage() {
  const locale = resolveLocale((await cookies()).get(localeCookie)?.value);
  const t = messagesFor(locale).Privacy;
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 py-12 sm:px-8">
      <h1 className="font-display text-step-4">{t.title}</h1>
      <p className="text-muted mt-4">{t.intro}</p>
      {(
        [
          [t.accountTitle, t.accountBody],
          [t.sessionsTitle, t.sessionsBody],
          [t.activityTitle, t.activityBody],
          [t.contactTitle, t.contactBody],
        ] as const
      ).map(([title, body]) => (
        <section key={title} className="border-rule mt-8 border-t pt-6">
          <h2 className="font-display text-step-2">{title}</h2>
          <p className="text-muted mt-3 leading-relaxed">{body}</p>
        </section>
      ))}
    </main>
  );
}

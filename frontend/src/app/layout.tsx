import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import { Caveat, Commissioner, JetBrains_Mono, Piazzolla } from "next/font/google";
import Link from "next/link";
import { NextIntlClientProvider } from "next-intl";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
import { localeCookie, resolveLocale } from "@/i18n/config";
import { messagesFor } from "@/i18n/messages";
import { siteUrl } from "@/lib/seo";
import "./globals.css";

// Every face ships latin + latin-ext + cyrillic: EN, AZ, FR and RU all render in the real fonts.
// next/font needs literal option objects, so the subsets list is repeated per face.
const piazzolla = Piazzolla({
  subsets: ["latin", "latin-ext", "cyrillic"],
  axes: ["opsz"],
  display: "swap",
  variable: "--font-piazzolla",
});
const commissioner = Commissioner({
  subsets: ["latin", "latin-ext", "cyrillic"],
  axes: ["FLAR", "VOLM", "slnt"],
  display: "swap",
  variable: "--font-commissioner",
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin", "latin-ext", "cyrillic"],
  display: "swap",
  variable: "--font-jetbrains",
});
const caveat = Caveat({
  subsets: ["latin", "latin-ext", "cyrillic"],
  display: "swap",
  variable: "--font-caveat",
});

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: { default: "UFAZ Hub", template: "%s · UFAZ Hub" },
  description: "A student-run library of resources, articles and answers for UFAZ.",
  openGraph: {
    type: "website",
    siteName: "UFAZ Hub",
    title: "UFAZ Hub",
    description: "A student-run library of resources, articles and answers for UFAZ.",
    url: "/",
    images: ["/opengraph-image"],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F6F1E7" },
    { media: "(prefers-color-scheme: dark)", color: "#0F1420" },
  ],
};

// Runs before first paint: apply a stored explicit choice; otherwise CSS follows the OS.
const noFlash = `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = resolveLocale((await cookies()).get(localeCookie)?.value);
  const footer = messagesFor(locale).Footer;
  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={`${piazzolla.variable} ${commissioner.variable} ${jetbrains.variable} ${caveat.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: noFlash }} />
        <link
          rel="alternate"
          type="application/rss+xml"
          title={footer.rssTitle}
          href="/api/feeds/articles.rss"
        />
        <link
          rel="alternate"
          type="application/atom+xml"
          title={footer.atomTitle}
          href="/api/feeds/articles.atom"
        />
      </head>
      <body>
        <a
          href="#main"
          className="bg-ink text-paper sr-only rounded-md px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-(--z-toast)"
        >
          {messagesFor(locale).Navigation.skip}
        </a>
        <NextIntlClientProvider locale={locale} messages={messagesFor(locale)}>
          <Providers>
            <SiteHeader />
            {children}
            <footer className="border-rule text-step--1 text-muted border-t px-4 py-6 sm:px-8">
              <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-2">
                <p>{footer.about}</p>
                <nav aria-label={footer.siteInformation} className="flex flex-wrap gap-x-5">
                  <Link
                    href="/privacy"
                    className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
                  >
                    {footer.privacy}
                  </Link>
                  <a
                    href="/api/feeds/articles.rss"
                    className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
                  >
                    {footer.rss}
                  </a>
                  <a
                    href="/api/feeds/articles.atom"
                    className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
                  >
                    {footer.atom}
                  </a>
                </nav>
              </div>
            </footer>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

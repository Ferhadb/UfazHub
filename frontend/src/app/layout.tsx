import type { Metadata, Viewport } from "next";
import { Caveat, Commissioner, JetBrains_Mono, Piazzolla } from "next/font/google";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
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
  title: { default: "UFAZ Hub", template: "%s · UFAZ Hub" },
  description: "A student-run library of resources, articles and answers for UFAZ.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F6F1E7" },
    { media: "(prefers-color-scheme: dark)", color: "#0F1420" },
  ],
};

// Runs before first paint: apply a stored explicit choice; otherwise CSS follows the OS.
const noFlash = `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${piazzolla.variable} ${commissioner.variable} ${jetbrains.variable} ${caveat.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: noFlash }} />
      </head>
      <body>
        <a
          href="#main"
          className="bg-ink text-paper sr-only rounded-md px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-(--z-toast)"
        >
          Skip to content
        </a>
        <Providers>
          <SiteHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}

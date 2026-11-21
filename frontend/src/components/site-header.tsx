"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { NotificationBell } from "@/components/notifications/bell";
import { SearchPalette } from "@/components/search-palette";
import { ShortcutHelp } from "@/components/shortcut-help";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar } from "@/components/ui/avatar";
import { buttonClass } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { Drawer } from "@/components/ui/modal";
import { useSession } from "@/lib/auth/use-session";

export function SiteHeader() {
  const t = useTranslations("Navigation");
  const { user, status } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const links = [
    { href: "/resources", label: t("resources") },
    { href: "/articles", label: t("articles") },
    { href: "/collections", label: t("collections") },
    { href: "/questions", label: t("questions") },
    { href: "/courses", label: t("courses") },
    { href: "/research", label: t("research") },
    { href: "/people", label: t("people") },
    ...(status === "authenticated"
      ? [
          { href: "/for-you", label: t("forYou") },
          { href: "/bookmarks", label: t("shelf") },
        ]
      : []),
    ...(user?.role === "admin" ? [{ href: "/admin", label: t("admin") }] : []),
  ];
  const hidden = ["/articles", "/courses"];
  const desktop = links.filter((l) => !hidden.includes(l.href));
  const authed = status === "authenticated" && user;
  return (
    <header className="border-rule relative z-10 border-b">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-2 sm:px-8">
        <Link
          href="/"
          className="inline-flex min-h-11 shrink-0 flex-col justify-center leading-none"
        >
          <span className="font-display text-step-1">
            UFAZ <span className="text-flame-text">Hub</span>
          </span>
          <span className="text-muted mt-1 hidden font-mono text-[0.625rem] tracking-widest uppercase sm:block">
            Community knowledge
          </span>
        </Link>
        <nav
          aria-label={t("main")}
          className="ml-2 hidden items-center gap-1 whitespace-nowrap xl:flex"
        >
          {desktop.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname.startsWith(link.href) ? "page" : undefined}
              className="hover:text-flame-text aria-[current=page]:border-flame-text inline-flex min-h-11 items-center border-b-2 border-transparent px-3 text-sm font-medium"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <SearchPalette />
          <div className="hidden items-center gap-2 whitespace-nowrap xl:flex">
            {authed ? (
              <>
                <NotificationBell />
                <Link
                  href="/settings"
                  aria-label={`${t("settings")} for ${user.display_name}`}
                  className="inline-flex min-h-11 min-w-11 items-center justify-center"
                >
                  <Avatar name={user.display_name} />
                </Link>
              </>
            ) : status === "anonymous" ? (
              <>
                <Link href="/signin" className={buttonClass("ghost")}>
                  {t("signIn")}
                </Link>
                <Link href="/signup" className={buttonClass("secondary")}>
                  {t("signUp")}
                </Link>
              </>
            ) : null}
            <Link href="/submit" className={buttonClass("primary")}>
              + {t("share")}
            </Link>
          </div>
          <div className="xl:hidden">
            <Drawer
              open={menuOpen}
              onOpenChange={setMenuOpen}
              title={t("main")}
              trigger={
                <button
                  type="button"
                  aria-label="Open menu"
                  className="text-ink hover:bg-ink/5 inline-flex min-h-11 min-w-11 items-center justify-center rounded-md"
                >
                  <Icon name="menu" />
                </button>
              }
            >
              <nav aria-label={t("main")} className="flex flex-col gap-1">
                {links.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className={buttonClass("ghost", "justify-start")}
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
              <div className="border-rule mt-2 flex flex-wrap items-center gap-2 border-t pt-3">
                <Link
                  href="/submit"
                  onClick={() => setMenuOpen(false)}
                  className={buttonClass("primary")}
                >
                  + {t("share")}
                </Link>
                {authed ? (
                  <>
                    <NotificationBell />
                    <Link
                      href={`/people/${user.id}`}
                      onClick={() => setMenuOpen(false)}
                      className={buttonClass("ghost")}
                    >
                      {t("profile")}
                    </Link>
                    <Link
                      href="/settings"
                      onClick={() => setMenuOpen(false)}
                      className={buttonClass("ghost")}
                    >
                      {t("settings")}
                    </Link>
                  </>
                ) : status === "anonymous" ? (
                  <>
                    <Link
                      href="/signin"
                      onClick={() => setMenuOpen(false)}
                      className={buttonClass("ghost")}
                    >
                      {t("signIn")}
                    </Link>
                    <Link
                      href="/signup"
                      onClick={() => setMenuOpen(false)}
                      className={buttonClass("secondary")}
                    >
                      {t("signUp")}
                    </Link>
                  </>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <LocaleSwitcher />
                <ThemeToggle />
                <ShortcutHelp />
              </div>
            </Drawer>
          </div>
        </div>
      </div>
    </header>
  );
}

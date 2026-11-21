"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { localeCookie, locales, type Locale } from "@/i18n/config";

const names: Record<Locale, string> = {
  en: "English",
  az: "Azərbaycanca",
  fr: "Français",
  ru: "Русский",
};

export function LocaleSwitcher() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("Navigation");

  return (
    <label className="text-step--1 text-muted inline-flex min-h-11 items-center gap-2 font-mono">
      <span>{t("language")}</span>
      <select
        aria-label={t("language")}
        className="border-rule bg-paper text-ink focus-visible:outline-accent min-h-11 rounded-sm border px-2 focus-visible:outline-2"
        value={locale}
        onChange={(event) => {
          const selected = event.currentTarget.value;
          if (!locales.some((item) => item === selected)) return;
          document.cookie = `${localeCookie}=${selected}; Path=/; Max-Age=31536000; SameSite=Lax`;
          router.refresh();
        }}
      >
        {locales.map((item) => (
          <option key={item} value={item} lang={item}>
            {names[item]}
          </option>
        ))}
      </select>
    </label>
  );
}

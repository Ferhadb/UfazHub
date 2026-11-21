export const locales = ["en", "az", "fr", "ru"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const localeCookie = "ufazhub_locale";

export function isLocale(value: string | undefined): value is Locale {
  return locales.some((locale) => locale === value);
}

export function resolveLocale(value: string | undefined): Locale {
  return isLocale(value) ? value : defaultLocale;
}

import { defaultLocale, type Locale } from "./config";
import en from "./messages/en.json";
import az from "./messages/az.json";
import fr from "./messages/fr.json";
import ru from "./messages/ru.json";

const overrides = { en, az, fr, ru } as const;

// Untranslated scaffolding falls back at the namespace/key level to complete English copy.
export function messagesFor(locale: Locale): typeof en {
  if (locale === defaultLocale) return en;
  const translation = overrides[locale];
  return Object.fromEntries(
    Object.entries(en).map(([namespace, messages]) => [
      namespace,
      { ...messages, ...(translation as Record<string, Record<string, string>>)[namespace] },
    ]),
  ) as typeof en;
}

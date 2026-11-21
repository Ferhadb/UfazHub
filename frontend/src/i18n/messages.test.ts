import { describe, expect, it } from "vitest";
import { locales, resolveLocale } from "./config";
import { messagesFor } from "./messages";

describe("locale messages", () => {
  it("falls back to English for unsupported cookie values", () => {
    expect(resolveLocale("de")).toBe("en");
    expect(resolveLocale("az")).toBe("az");
  });

  it("has all English keys in each scaffold locale", () => {
    const baseline = messagesFor("en");
    for (const locale of locales) {
      const messages = messagesFor(locale);
      for (const namespace of Object.keys(baseline) as (keyof typeof baseline)[]) {
        expect(Object.keys(messages[namespace]).sort()).toEqual(
          Object.keys(baseline[namespace]).sort(),
        );
      }
    }
  });

  it("keeps Azerbaijani, French and Russian glyphs intact", () => {
    expect("Əə Iı İi Şş Çç Ğğ Öö Üü").toContain("Əə");
    expect(messagesFor("az").Navigation.language).toBe("Dil");
    expect(messagesFor("fr").Navigation.settings).toBe("Paramètres");
    expect(messagesFor("ru").Navigation.research).toBe("Исследования");
    expect("é è ê à ç œ « » Ёё Щщ Ыы").toContain("Ёё Щщ Ыы");
  });
});

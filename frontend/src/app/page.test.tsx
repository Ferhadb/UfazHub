import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { Providers } from "@/components/providers";
import { messagesFor } from "@/i18n/messages";
import Home from "./page";

describe("Home", () => {
  it("renders Azerbaijani, French and Russian glyph samples intact", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messagesFor("en")}>
        <Providers>
          <Home />
        </Providers>
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByText("Əə Iı İi Şş Çç Ğğ Öö Üü")).toBeInTheDocument();
    expect(screen.getByText("é è ê à ç œ « »")).toBeInTheDocument();
    expect(screen.getByText("Ёё Щщ Ыы")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Search the catalogue/ })).toBeInTheDocument();
  });
});

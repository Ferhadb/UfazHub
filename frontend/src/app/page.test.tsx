import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("renders Azerbaijani, French and Russian glyph samples intact", () => {
    render(<Home />);
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      "Əlgəbr və həndəsə: Iı İi Şş Çç Ğğ Öö Üü",
    );
    expect(screen.getByText(/é è ê à ç œ « très utile »/)).toBeInTheDocument();
    expect(screen.getByText("Ёё Щщ Ыы: читать перед экзаменом.")).toBeInTheDocument();
  });
});

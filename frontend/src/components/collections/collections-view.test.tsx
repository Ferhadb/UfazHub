import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { Spines } from "./collections-view";

const col = (i: number) =>
  ({
    id: `id${i}`,
    call_number: `COL-000${i}`,
    title: `Path ${i}`,
    description: `About ${i}`,
    is_research: false,
    items: [{ position: 0, note: "", item: { id: "x", title: "First stop" } }],
  }) as never;

describe("Spines", () => {
  it("pulls a spine out and shows its card; pressing again closes it", async () => {
    renderWithProviders(<Spines collections={[col(1), col(2)]} />);
    const spine = screen.getByRole("button", { name: /Path 2/ });
    expect(spine).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(spine);
    expect(spine).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("link", { name: "Open collection" })).toHaveAttribute(
      "href",
      "/collections/COL-0002",
    );
    await userEvent.click(spine);
    expect(screen.queryByRole("link", { name: "Open collection" })).not.toBeInTheDocument();
  });
});

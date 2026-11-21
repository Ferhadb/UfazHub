import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/utils";
import { Composer } from "./composer";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { id: "u1", email_verified: true } }),
}));

afterEach(() => vi.unstubAllGlobals());

describe("Composer", () => {
  it("switches the form and the ruling by type, and mirrors the title on the live card", async () => {
    stubApi({});
    const { container } = renderWithProviders(<Composer />);
    expect(container.querySelector(".ruled-resource")).not.toBeNull();
    await userEvent.type(screen.getByLabelText("Title"), "Spectral theorem");
    const preview = screen.getByRole("complementary", { name: "Live preview" });
    expect(preview).toHaveTextContent("Spectral theorem");

    await userEvent.click(screen.getByRole("button", { name: /Article/ }));
    expect(container.querySelector(".ruled-article")).not.toBeNull();
    expect(screen.getByLabelText("Body (Markdown)")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Collection/ }));
    expect(container.querySelector(".ruled-collection")).not.toBeNull();
    expect(screen.getByLabelText("Find a resource or article")).toBeInTheDocument();
  });
});

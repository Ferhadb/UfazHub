import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/utils";
import { ArticleForm } from "./article-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { id: "u1", email_verified: true } }),
}));
afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
});

describe("ArticleForm", () => {
  it("saves a draft with the typed payload and opens it", async () => {
    let body: Record<string, unknown> = {};
    stubApi({
      "POST /api/articles": async (req) => {
        body = await req.json();
        return Response.json(
          { slug: "my-post", call_number: "ART-0001", status: "draft" },
          { status: 201 },
        );
      },
    });
    renderWithProviders(<ArticleForm />);
    await userEvent.type(screen.getByLabelText("Title"), "My post");
    await userEvent.type(screen.getByLabelText("Body (Markdown)"), "Some words about things.");
    await userEvent.type(screen.getByLabelText("Tags"), "a, b");
    await userEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/articles/my-post"));
    expect(body).toMatchObject({ title: "My post", tags: ["a", "b"], publish: false });
  });

  it("shows server field errors and previews through the server", async () => {
    stubApi({
      "POST /api/articles": () =>
        Response.json(
          { code: "validation_error", message: "Invalid", fields: { title: "Too short" } },
          { status: 422 },
        ),
      "POST /api/articles/preview": () =>
        Response.json({ body_html: "<h2>Rendered</h2>", reading_minutes: 1, toc: [] }),
    });
    renderWithProviders(<ArticleForm />);
    await userEvent.type(screen.getByLabelText("Body (Markdown)"), "## Rendered heading text");
    await userEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(await screen.findByText("Too short")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(await screen.findByRole("heading", { name: "Rendered" })).toBeInTheDocument();
  });
});

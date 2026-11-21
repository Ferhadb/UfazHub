import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, resource, stubApi as stub } from "@/test/utils";

const noDupes = { "GET /api/resources/duplicates": () => Response.json([]) };
const stubApi = (routes: Parameters<typeof stub>[0]) => stub({ ...noDupes, ...routes });
import { SubmitForm } from "./form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
let verified = true;
vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { email_verified: verified } }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
  verified = true;
});

async function fillValid() {
  await userEvent.type(screen.getByLabelText("Title"), "Linear Algebra Done Right");
  await userEvent.type(
    screen.getByLabelText(/What is it/),
    "A proof-first textbook for L2 algebra.",
  );
  await userEvent.type(screen.getByLabelText("Link 1"), "https://example.org/laa");
}

describe("SubmitForm", () => {
  it("shows field errors and sends nothing when the form is invalid", async () => {
    const fetchMock = stubApi({});
    renderWithProviders(<SubmitForm />);
    await userEvent.type(screen.getByLabelText("Link 1"), "javascript:alert(1)");
    await userEvent.click(screen.getByRole("button", { name: "Submit for the shelf" }));
    expect(await screen.findByText("At least 3 characters")).toBeInTheDocument();
    expect(screen.getByText(/Say a little more/)).toBeInTheDocument();
    expect(screen.getByText("Enter a full http(s) link")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock.mock.calls.filter(([r]) => r.method === "POST")).toHaveLength(0);
  });

  it("posts the typed payload and goes to the new card", async () => {
    let body: Record<string, unknown> = {};
    stubApi({
      "POST /api/resources": async (req) => {
        body = await req.json();
        return Response.json(resource({ call_number: "RES-0500" }), { status: 201 });
      },
    });
    renderWithProviders(<SubmitForm />);
    await fillValid();
    await userEvent.type(screen.getByLabelText("Tags"), "algebra, Past Exams ,");
    await userEvent.type(screen.getByLabelText("Time commitment (minutes)"), "90");
    await userEvent.click(screen.getByRole("button", { name: "Submit for the shelf" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/resources/RES-0500"));
    expect(body).toMatchObject({
      title: "Linear Algebra Done Right",
      resource_type: "article",
      difficulty: "beginner",
      time_commitment_minutes: 90,
      tags: ["algebra", "Past Exams"],
      links: [{ url: "https://example.org/laa", label: "" }],
      is_research: false,
    });
  });

  it("maps the server's field errors onto the form", async () => {
    stubApi({
      "POST /api/resources": () =>
        Response.json(
          {
            code: "validation_error",
            message: "Invalid input",
            fields: { "links.0.url": "Only http and https links are allowed" },
          },
          { status: 422 },
        ),
    });
    renderWithProviders(<SubmitForm />);
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: "Submit for the shelf" }));
    expect(await screen.findByText("Only http and https links are allowed")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("warns about duplicates without blocking", async () => {
    stubApi({
      "GET /api/resources/duplicates": () =>
        Response.json([
          { call_number: "RES-0007", title: "Linear Algebra Done Right", match: "same_link" },
        ]),
    });
    renderWithProviders(<SubmitForm />);
    await userEvent.type(screen.getByLabelText("Link 1"), "https://example.org/laa");
    await userEvent.tab();
    expect(await screen.findByRole("link", { name: /RES-0007/ })).toHaveAttribute(
      "href",
      "/resources/RES-0007",
    );
    expect(screen.getByText("(same link)")).toBeInTheDocument();
  });

  it("adds and removes links, capped at five", async () => {
    stubApi({});
    renderWithProviders(<SubmitForm />);
    for (let i = 0; i < 4; i++)
      await userEvent.click(screen.getByRole("button", { name: /Add another link/ }));
    expect(screen.getAllByLabelText(/^Link \d$/)).toHaveLength(5);
    expect(screen.queryByRole("button", { name: /Add another link/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove link 5" }));
    expect(screen.getAllByLabelText(/^Link \d$/)).toHaveLength(4);
  });

  it("blocks unverified accounts up front", () => {
    verified = false;
    stubApi({});
    renderWithProviders(<SubmitForm />);
    expect(screen.getByText("Verify your email first")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit for the shelf" })).toBeDisabled();
  });
});

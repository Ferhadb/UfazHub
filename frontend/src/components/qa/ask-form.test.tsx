import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/utils";
import { AskForm } from "./ask-form";

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

const hit = {
  call_number: "QST-0003",
  title: "How does Dijkstra shortest path work?",
  answer_count: 2,
  has_accepted: true,
};

describe("AskForm", () => {
  it("suggests similar questions while the title is typed", async () => {
    stubApi({ "GET /api/questions/similar": () => Response.json([hit]) });
    renderWithProviders(<AskForm />);
    await userEvent.type(screen.getByLabelText("Question"), "Dijkstra shortest path?");
    const link = await screen.findByRole("link", { name: /QST-0003 How does Dijkstra/ });
    expect(link).toHaveAttribute("href", "/questions/QST-0003");
    expect(screen.getByText(/2 answers, checked/)).toBeInTheDocument();
  });

  it("validates before sending anything", async () => {
    const fetchMock = stubApi({ "GET /api/questions/similar": () => Response.json([]) });
    renderWithProviders(<AskForm />);
    await userEvent.type(screen.getByLabelText("Linked resource (optional)"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Post the question" }));
    expect(await screen.findByText("Ask in at least 10 characters")).toBeInTheDocument();
    expect(screen.getByText("Name the course or subject")).toBeInTheDocument();
    expect(screen.getByText("A call number such as RES-0421")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([r]) => r.method === "POST")).toHaveLength(0);
  });

  it("posts the question and opens its page", async () => {
    let body: Record<string, unknown> = {};
    stubApi({
      "GET /api/questions/similar": () => Response.json([]),
      "POST /api/questions": async (req) => {
        body = await req.json();
        return Response.json({ call_number: "QST-0009", status: "published" }, { status: 201 });
      },
    });
    renderWithProviders(<AskForm />);
    await userEvent.type(screen.getByLabelText("Question"), "How do I prove Dijkstra correct?");
    await userEvent.type(screen.getByLabelText("Details"), "I lose the invariant proof.");
    await userEvent.type(screen.getByLabelText("Course or subject"), "Algorithms L2");
    await userEvent.type(screen.getByLabelText("Tags"), "graphs, proofs");
    await userEvent.click(screen.getByRole("button", { name: "Post the question" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/questions/QST-0009"));
    expect(body).toEqual({
      title: "How do I prove Dijkstra correct?",
      body: "I lose the invariant proof.",
      topic: "Algorithms L2",
      linked_resource: null,
      tags: ["graphs", "proofs"],
    });
  });

  it("maps server field errors onto the form", async () => {
    stubApi({
      "GET /api/questions/similar": () => Response.json([]),
      "POST /api/questions": () =>
        Response.json(
          {
            code: "bad_request",
            message: "That resource does not exist.",
            fields: { linked_resource: "No published resource with this call number" },
          },
          { status: 400 },
        ),
    });
    renderWithProviders(<AskForm />);
    await userEvent.type(screen.getByLabelText("Question"), "How do I prove Dijkstra correct?");
    await userEvent.type(screen.getByLabelText("Details"), "I lose the invariant proof.");
    await userEvent.type(screen.getByLabelText("Course or subject"), "Algorithms");
    await userEvent.type(screen.getByLabelText("Linked resource (optional)"), "RES-9999");
    await userEvent.click(screen.getByRole("button", { name: "Post the question" }));
    expect(await screen.findByText(/No published resource/)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("asks unverified users to verify first", () => {
    verified = false;
    stubApi({});
    renderWithProviders(<AskForm />);
    expect(screen.getByText("Verify your email first")).toBeInTheDocument();
  });
});

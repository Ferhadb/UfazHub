import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { AdminPanel } from "@/components/admin/admin-panel";
import { ModerationHistory } from "./history";
import { ReportButton } from "./report-button";

const session = vi.hoisted(() => ({
  current: { status: "authenticated", user: { id: "me", role: "user" } } as {
    status: string;
    user: { id: string; role: string } | null;
  },
}));
vi.mock("@/lib/auth/use-session", () => ({ useSession: () => session.current }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

afterEach(() => {
  vi.unstubAllGlobals();
  session.current = { status: "authenticated", user: { id: "me", role: "user" } };
});

describe("ReportButton", () => {
  it("is absent for guests and for the author", () => {
    session.current = { status: "anonymous", user: null };
    const { unmount } = renderWithProviders(<ReportButton itemId="i1" authorId="x" />);
    expect(screen.queryByRole("button", { name: "Report" })).toBeNull();
    unmount();
    session.current = { status: "authenticated", user: { id: "x", role: "user" } };
    renderWithProviders(<ReportButton itemId="i1" authorId="x" />);
    expect(screen.queryByRole("button", { name: "Report" })).toBeNull();
  });

  it("sends the chosen reason and note", async () => {
    let body: unknown;
    stubApi({
      "POST /api/content/i1/report": async (req) => {
        body = await req.json();
        return new Response(null, { status: 204 });
      },
    });
    renderWithProviders(<ReportButton itemId="i1" authorId="x" />);
    await userEvent.click(screen.getByRole("button", { name: "Report" }));
    await userEvent.selectOptions(screen.getByLabelText("What is wrong?"), "broken_link");
    await userEvent.type(screen.getByLabelText("Note (optional)"), "404 page");
    await userEvent.click(screen.getByRole("button", { name: "Send report" }));
    await waitFor(() => expect(body).toEqual({ reason: "broken_link", note: "404 page" }));
    expect(await screen.findByText("Report sent")).toBeInTheDocument();
  });
});

describe("ModerationHistory", () => {
  const item = { id: "i1", call_number: "RES-0001", title: "My notes", status: "hidden" };
  const event = {
    id: "e1",
    action: "content.hide",
    reason: "Looks like spam",
    created_at: "2026-01-02T10:00:00Z",
    item,
  };

  it("shows the reason and lets the author appeal a hidden post", async () => {
    let body: unknown;
    stubApi({
      "GET /api/me/moderation": () => page([event]),
      "GET /api/me/appeals": () => page([]),
      "POST /api/content/i1/appeal": async (req) => {
        body = await req.json();
        return new Response(null, { status: 204 });
      },
    });
    renderWithProviders(<ModerationHistory />);
    expect(await screen.findByText("Reason: Looks like spam")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Appeal" }));
    const send = screen.getByRole("button", { name: "Send appeal" });
    expect(send).toBeDisabled(); // too short
    await userEvent.type(screen.getByLabelText("Your message"), "This is a real resource");
    await userEvent.click(send);
    await waitFor(() => expect(body).toEqual({ message: "This is a real resource" }));
  });

  it("shows a sent appeal instead of the button", async () => {
    stubApi({
      "GET /api/me/moderation": () => page([event]),
      "GET /api/me/appeals": () =>
        page([
          {
            id: "a1",
            kind: "content",
            status: "open",
            message: "m",
            response: null,
            user: { id: "me", display_name: "Me" },
            item,
            created_at: "2026-01-03T00:00:00Z",
            resolved_at: null,
          },
        ]),
    });
    renderWithProviders(<ModerationHistory />);
    expect(await screen.findByText("Appeal sent")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Appeal" })).toBeNull();
  });
});

describe("AdminPanel", () => {
  it("turns non-admins away without calling the admin API", () => {
    const fetchSpy = stubApi({});
    renderWithProviders(<AdminPanel />);
    expect(screen.getByText("Admins only")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("bulk-hides the selected queue items with a reason", async () => {
    session.current = { status: "authenticated", user: { id: "me", role: "admin" } };
    let body: unknown;
    stubApi({
      "GET /api/admin/queue": () =>
        page([
          {
            id: "i1",
            type: "resource",
            call_number: "RES-0001",
            title: "Spammy thing",
            status: "published",
            hidden_reason: null,
            author: { id: "u", display_name: "Leyla", reputation: 0 },
            report_count: 2,
            reasons: ["spam"],
            created_at: "2026-01-01T00:00:00Z",
            activity_at: "2026-01-02T00:00:00Z",
          },
        ]),
      "POST /api/admin/content/actions": async (req) => {
        body = await req.json();
        return Response.json({ done: ["i1"], failed: [] });
      },
    });
    renderWithProviders(<AdminPanel />);
    await userEvent.click(await screen.findByRole("checkbox", { name: "Select RES-0001" }));
    expect(screen.getByText("1 selected")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Hide" }));
    await userEvent.type(screen.getByLabelText("Reason"), "spam link");
    await userEvent.click(screen.getAllByRole("button", { name: "Hide" }).at(-1)!);
    await waitFor(() => expect(body).toEqual({ ids: ["i1"], action: "hide", reason: "spam link" }));
    expect(await screen.findByText("1 done")).toBeInTheDocument();
  });
});

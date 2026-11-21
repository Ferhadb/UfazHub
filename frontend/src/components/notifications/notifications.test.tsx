import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page, renderWithProviders, stubApi } from "@/test/utils";
import { NotificationBell } from "./bell";
import { NotificationsView } from "./notifications-view";

vi.mock("@/lib/auth/use-session", () => ({
  useSession: () => ({ status: "authenticated", user: { id: "u1" } }),
}));

afterEach(() => vi.unstubAllGlobals());

const note = (over: Record<string, unknown> = {}) => ({
  id: "n1",
  kind: "answer",
  actor: { id: "u2", display_name: "Leyla", reputation: 0 },
  call_number: "QST-0001",
  title: "How do I prove Dijkstra correct?",
  message: "",
  read: false,
  created_at: "2026-01-02T10:00:00Z",
  ...over,
});

describe("NotificationBell", () => {
  it("marks unread with a flame dot and says the count aloud", async () => {
    stubApi({ "GET /api/notifications/unread": () => Response.json({ unread: 3 }) });
    renderWithProviders(<NotificationBell />);
    const link = await screen.findByRole("link", { name: "Notifications, 3 unread" });
    expect(link).toHaveAttribute("href", "/notifications");
    expect(link.querySelector(".bg-flame")).not.toBeNull();
  });

  it("shows no marker when everything is read", async () => {
    stubApi({ "GET /api/notifications/unread": () => Response.json({ unread: 0 }) });
    renderWithProviders(<NotificationBell />);
    const link = await screen.findByRole("link", { name: "Notifications" });
    await waitFor(() => expect(link.querySelector(".bg-flame")).toBeNull());
  });
});

describe("NotificationsView", () => {
  it("lists notifications, links to the page and marks one read on open", async () => {
    let marked: unknown;
    stubApi({
      "GET /api/notifications": () =>
        page([
          note(),
          note({
            id: "n2",
            kind: "moderation",
            message: "Broken link",
            read: true,
            call_number: "RES-0002",
            title: "Old",
          }),
        ]),
      "GET /api/notifications/settings": () => Response.json({ email_digest: false }),
      "POST /api/notifications/read": async (req) => {
        marked = await req.json();
        return Response.json({ unread: 0 });
      },
    });
    renderWithProviders(<NotificationsView />);
    const link = await screen.findByRole("link", { name: /QST-0001/ });
    expect(link).toHaveAttribute("href", "/questions/QST-0001");
    expect(screen.getByText("Leyla answered")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /RES-0002/ })).toHaveAttribute(
      "href",
      "/resources/RES-0002",
    );
    expect(screen.getByText(/Moderation, Broken link/)).toBeInTheDocument();
    await userEvent.click(link);
    await waitFor(() => expect(marked).toEqual({ ids: ["n1"] }));
  });

  it("marks everything read and toggles the digest", async () => {
    let all: unknown;
    let digest: unknown;
    stubApi({
      "GET /api/notifications": () => page([note()]),
      "GET /api/notifications/settings": () => Response.json({ email_digest: false }),
      "POST /api/notifications/read": async (req) => {
        all = await req.json();
        return Response.json({ unread: 0 });
      },
      "PUT /api/notifications/settings": async (req) => {
        digest = await req.json();
        return Response.json(digest);
      },
    });
    renderWithProviders(<NotificationsView />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark all read" }));
    await waitFor(() => expect(all).toEqual({ ids: null }));
    const sw = screen.getByRole("switch", { name: "Email me a daily digest" });
    await waitFor(() => expect(sw).toBeEnabled());
    await userEvent.click(sw);
    await waitFor(() => expect(digest).toEqual({ email_digest: true }));
  });

  it("has an empty state and an error state with retry", async () => {
    stubApi({
      "GET /api/notifications": () => page([]),
      "GET /api/notifications/settings": () => Response.json({ email_digest: false }),
    });
    const { unmount } = renderWithProviders(<NotificationsView />);
    expect(await screen.findByText("All quiet")).toBeInTheDocument();
    unmount();
    stubApi({
      "GET /api/notifications": () =>
        Response.json({ code: "boom", message: "Down for lunch" }, { status: 500 }),
      "GET /api/notifications/settings": () => Response.json({ email_digest: false }),
    });
    renderWithProviders(<NotificationsView />);
    expect(await screen.findByText("Down for lunch")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

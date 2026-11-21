import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { getAccessToken, setAccessToken } from "./token";
import { useSession } from "./use-session";

const user = {
  id: "1",
  email: "a@example.com",
  display_name: "Aygün",
  role: "user",
  status: "active",
  email_verified: true,
  created_at: "2026-01-01T00:00:00Z",
};
const tokens = { access_token: "jwt-1", token_type: "bearer", expires_in: 900, user };

function setup(fetchImpl: typeof fetch) {
  vi.stubGlobal("fetch", vi.fn(fetchImpl));
  const client = new QueryClient();
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return renderHook(() => useSession(), { wrapper });
}

const clearCsrf = () => (document.cookie = "csrf_token=; path=/; max-age=0");

describe("useSession", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    clearCsrf();
  });

  it("is anonymous without a request when no session hint exists", async () => {
    const { result } = setup(async () => Response.json(tokens));
    await waitFor(() => expect(result.current.status).toBe("anonymous"));
    expect(fetch).not.toHaveBeenCalled();
  });

  it("silently refreshes into an authenticated session and keeps the token in memory", async () => {
    document.cookie = "csrf_token=c1; path=/";
    const { result } = setup(async () => Response.json(tokens));
    await waitFor(() => expect(result.current.status).toBe("authenticated"));
    expect(result.current.user?.email).toBe("a@example.com");
    expect(getAccessToken()).toBe("jwt-1");
    const req = vi.mocked(fetch).mock.calls[0]![0] as Request;
    expect(new URL(req.url).pathname).toBe("/api/auth/refresh");
    expect(req.headers.get("X-CSRF-Token")).toBe("c1");
  });

  it("falls back to anonymous when the refresh is rejected", async () => {
    document.cookie = "csrf_token=c1; path=/";
    const { result } = setup(async () =>
      Response.json({ code: "refresh_reuse", message: "Session expired." }, { status: 401 }),
    );
    await waitFor(() => expect(result.current.status).toBe("anonymous"));
    expect(getAccessToken()).toBeNull();
  });
});

import { NextRequest } from "next/server";
import { isProtected, middleware } from "./middleware";

const req = (path: string, cookie?: string) =>
  new NextRequest(`http://localhost${path}`, { headers: cookie ? { cookie } : {} });

describe("route guard", () => {
  it("knows which paths need a session", () => {
    expect(isProtected("/settings")).toBe(true);
    expect(isProtected("/admin/users")).toBe(true);
    expect(isProtected("/ask")).toBe(true);
    expect(isProtected("/reputation")).toBe(false); // the rules page is public
    expect(isProtected("/settingsx")).toBe(false);
    expect(isProtected("/signin")).toBe(false);
  });

  it("redirects signed-out visitors to sign in with a return path", () => {
    const res = middleware(req("/settings?tab=2"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/signin?next=%2Fsettings%3Ftab%3D2");
  });

  it("lets a browser with a session hint through", () => {
    const res = middleware(req("/settings", "csrf_token=abc"));
    expect(res.headers.get("location")).toBeNull();
  });
});

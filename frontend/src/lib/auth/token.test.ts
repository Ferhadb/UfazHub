import { getAccessToken, readCsrfCookie, safeNext, setAccessToken } from "./token";

describe("safeNext", () => {
  it("allows same-site paths only", () => {
    expect(safeNext("/settings?tab=1")).toBe("/settings?tab=1");
    for (const bad of ["//evil.com", "https://evil.com", "/\\evil.com", "", null, undefined]) {
      expect(safeNext(bad)).toBe("/");
    }
  });
});

describe("access token store", () => {
  it("keeps the token in memory only", () => {
    setAccessToken("abc");
    expect(getAccessToken()).toBe("abc");
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain("abc");
    expect(document.cookie).not.toContain("abc");
    setAccessToken(null);
  });

  it("reads the CSRF cookie", () => {
    document.cookie = "csrf_token=tok%2Bx; path=/";
    expect(readCsrfCookie()).toBe("tok+x");
  });
});

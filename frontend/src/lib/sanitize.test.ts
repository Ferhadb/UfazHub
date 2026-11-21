import { sanitizeHtml } from "./sanitize";

describe("sanitizeHtml", () => {
  it.each([
    ["<script>alert(1)</script><p>hi</p>", "<p>hi</p>"],
    ["<img src=x onerror=alert(1)>", "<img>"],
    ['<a href="javascript:alert(1)">x</a>', '<a rel="noopener nofollow ugc">x</a>'],
    ['<a href="data:text/html;base64,AA">x</a>', '<a rel="noopener nofollow ugc">x</a>'],
    ['<iframe src="https://evil.example"></iframe>', ""],
    ["<svg onload=alert(1)></svg>", ""],
    ["<style>p{display:none}</style><p>a</p>", "<p>a</p>"],
    ['<p onclick="x()" style="color:red" id="a">a</p>', "<p>a</p>"],
  ])("neutralises %s", (dirty, clean) => {
    expect(sanitizeHtml(dirty)).toBe(clean);
  });

  it("forces rel on links and drops target", () => {
    const el = document.createElement("div");
    el.innerHTML = sanitizeHtml('<a href="https://x.org" target="_blank" rel="opener">x</a>');
    const a = el.querySelector("a")!;
    expect(a.getAttribute("rel")).toBe("noopener nofollow ugc");
    expect(a.hasAttribute("target")).toBe(false);
    expect(a.getAttribute("href")).toBe("https://x.org");
  });

  it("keeps Azerbaijani and French text intact", () => {
    expect(sanitizeHtml("<p>Əlifba ı ş « é œ »</p>")).toBe("<p>Əlifba ı ş « é œ »</p>");
  });
});

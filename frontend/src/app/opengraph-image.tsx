import { ImageResponse } from "next/og";

export const alt = "UFAZ Hub — the student knowledge library";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#F6F1E7",
        color: "#17140F",
        padding: 72,
        borderTop: "20px solid #0E5A6B",
      }}
    >
      <div style={{ fontSize: 31, letterSpacing: 3 }}>UFAZ · BAKU & PARIS</div>
      <div style={{ fontSize: 92, lineHeight: 1.05, maxWidth: 980 }}>
        The library we wrote ourselves.
      </div>
      <div style={{ fontSize: 29, color: "#0E5A6B" }}>Resources · Articles · Answers</div>
    </div>,
    size,
  );
}

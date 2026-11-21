import type { SVGProps } from "react";

/* Hand-drawn icon set: loose 24px strokes, round caps, deliberately not machine-straight.
 * Decorative by default (aria-hidden); pass `title` when an icon stands alone. */
const paths = {
  search: "M10.5 4.2a6.4 6.3 0 1 0 .1 12.7 6.4 6.3 0 0 0-.1-12.7ZM15.2 15.4l5 5.1",
  bookmark: "M6.5 3.6c3.6-.3 7.4-.2 11 0l.2 16.6-5.6-4.4-5.7 4.4Z",
  menu: "M4 7.2c5-.5 11-.4 16 0M4 12.1c5.4-.4 10.6-.3 16 0M4 17c5-.4 10.8-.5 16 .1",
  close: "M5.5 5.6l13 12.8M18.4 5.3 5.7 18.6",
  check: "M4.6 12.8l4.6 4.6L19.6 6.6",
  "arrow-right": "M4 12.3c5 .2 10-.2 15.5-.1M13.5 6.2l6.2 6-6 6.1",
  "chevron-left": "M14.8 5.2l-6.6 6.9 6.6 6.8",
  "chevron-right": "M9.2 5.2l6.6 6.9-6.6 6.8",
  plus: "M12 4.6c.2 5 0 10.4 0 14.9M4.6 12.1c5-.2 10.3 0 14.8-.1",
  user: "M12 4a3.8 3.9 0 1 0 .1 7.8A3.8 3.9 0 0 0 12 4ZM4.8 20c.4-4 3.2-6 7.2-6s6.8 2 7.2 6",
  bell: "M6.2 17.4c1-1.3 1.3-3 1.3-5.2a4.5 4.6 0 0 1 9 0c0 2.2.3 3.9 1.3 5.2-3.7.4-7.8.4-11.6 0ZM10 20.4c1.3.5 2.7.5 4 0",
  sun: "M12 8a4 4 0 1 0 .1 8A4 4 0 0 0 12 8ZM12 2.8V5M12 19v2.2M2.8 12H5M19 12h2.2M5.5 5.6l1.6 1.5M16.9 16.9l1.6 1.5M18.5 5.6l-1.6 1.5M7.1 16.9l-1.6 1.5",
  moon: "M19.6 14.6A8 8 0 0 1 9.4 4.4a8 8 0 1 0 10.2 10.2Z",
  star: "M12 3.6l2.6 5.5 6 .8-4.4 4.1 1.1 6-5.3-3-5.4 2.9 1.2-5.9L3.4 9.9l6-.8Z",
  flag: "M5.6 21V4.2M5.6 4.8c3.5-1.6 6 1.6 12.8-.4l-2 4.4 2 4.2c-6.5 2-9.3-1.2-12.8.2",
  message: "M4.4 5.6c5.1-.4 10.2-.4 15.2 0l.2 10.6c-3.2.2-5 .1-7 .1L8 20v-3.8c-1.2 0-2.4 0-3.6-.1Z",
  tag: "M3.8 11.6V4.4h7.2l9.2 9.3-7 7ZM8 8.3a.6.6 0 1 0 .1 0Z",
  eye: "M2.6 12c2.4-4.2 5.6-6.2 9.4-6.2s7 2 9.4 6.2c-2.4 4.2-5.6 6.2-9.4 6.2S5 16.2 2.6 12ZM12 9.3a2.7 2.7 0 1 0 .1 5.4 2.7 2.7 0 0 0-.1-5.4Z",
  home: "M3.6 11.4 12 4l8.4 7.4M6 10v10h12V10M10 20v-5.4h4V20",
  book: "M4 5.2c3-.9 5.6-.6 8 1.2 2.4-1.8 5-2.1 8-1.2v13.2c-3-.8-5.6-.5-8 1.3-2.4-1.8-5-2.1-8-1.3ZM12 6.4v13.3",
  pencil: "M4.4 19.6l1-4.6L16.6 3.8l3.6 3.6L9 18.6ZM14.2 6.2l3.6 3.6",
  link: "M10 14a4 4 0 0 0 5.7 0l3.4-3.4a4 4 0 0 0-5.7-5.7L12 6.3M14 10a4 4 0 0 0-5.7 0l-3.4 3.4a4 4 0 0 0 5.7 5.7L12 17.7",
  upload: "M12 16V4.8M7.2 9.2 12 4.4l4.8 4.8M4.4 15.8v3.8h15.2v-3.8",
  trash: "M4.6 6.8h14.8M9.2 6.6V4.2h5.6v2.4M6.4 6.8l.8 13h9.6l.8-13M10 10.6v6M14 10.6v6",
  alert: "M12 3.8 2.8 19.8h18.4ZM12 9.8v4.6M12 17.2v.2",
  "arrow-up": "M12 20c.1-5 0-10.3 0-15.4M6 10.4l6-6 6 6.1",
  "arrow-down": "M12 4c.1 5 0 10.3 0 15.4M6 13.6l6 6 6-6.1",
  info: "M12 3.8a8.2 8.3 0 1 0 .1 16.5A8.2 8.3 0 0 0 12 3.800ZM12 11v5.4M12 7.8v.2",
} as const;

export type IconName = keyof typeof paths;
export const iconNames = Object.keys(paths) as IconName[];

type IconProps = Omit<SVGProps<SVGSVGElement>, "name"> & {
  name: IconName;
  size?: number;
  title?: string;
};

export function Icon({ name, size = 20, title, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
      {...rest}
    >
      <path d={paths[name]} />
    </svg>
  );
}

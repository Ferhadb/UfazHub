/** What the composer's live index card needs from whichever form is open. */
export type Draft = {
  kind: "resource" | "article" | "collection";
  title: string;
  blurb: string;
  chips: string[];
};

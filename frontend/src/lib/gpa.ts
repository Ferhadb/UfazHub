/** UFAZ GPA is the sister site and the identity provider for students. */
export const GPA_URL = (process.env.NEXT_PUBLIC_GPA_URL ?? "https://ufazgpa.xyz").replace(
  /\/+$/,
  "",
);

export const STATE_KEY = "gpa-sso-state";
export const NEXT_KEY = "gpa-sso-next";

/** Start sign-in on GPA. `state` binds the answer to this browser tab. */
export function startGpaSignIn(next: string) {
  const state = crypto.randomUUID().replaceAll("-", "") + crypto.randomUUID().replaceAll("-", "");
  try {
    sessionStorage.setItem(STATE_KEY, state);
    sessionStorage.setItem(NEXT_KEY, next);
  } catch {
    /* private mode: the callback will ask the student to start again */
  }
  window.location.assign(`${GPA_URL}/sso/hub?state=${state}`);
}

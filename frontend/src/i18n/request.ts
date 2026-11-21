import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { localeCookie, resolveLocale } from "./config";
import { messagesFor } from "./messages";

export default getRequestConfig(async () => {
  const locale = resolveLocale((await cookies()).get(localeCookie)?.value);
  return { locale, messages: messagesFor(locale) };
});

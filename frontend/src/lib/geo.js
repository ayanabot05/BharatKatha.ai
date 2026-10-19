/**
 * Best-effort country hint for pricing.
 *
 * The backend prefers its own edge country header, which is derived from the
 * real visitor IP and cannot be spoofed by a browser. This exists only for
 * hosts that set no such header (local development, or an API called directly),
 * where the backend would otherwise show USD to everyone including India.
 *
 * The timezone is the least bad signal available: a visitor whose clock is set
 * to India almost always expects rupee pricing. Only India has to be detected —
 * USD is the backend default, so every other country is already correct.
 */
const INDIA_TIMEZONES = new Set(["Asia/Kolkata", "Asia/Calcutta"]);
const INDIA_LANGUAGE = /[-_]IN$/i;

export function countryHint() {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    if (INDIA_TIMEZONES.has(zone)) return "IN";
  } catch {
    // Intl unavailable: fall through to the language tag.
  }
  try {
    const tags = [navigator.language, ...(navigator.languages || [])];
    if (tags.some((tag) => INDIA_LANGUAGE.test(tag || ""))) return "IN";
  } catch {
    // No navigator: no hint.
  }
  return "";
}

/** axios `params` for the pricing endpoints, undefined when there is no hint. */
export function priceParams() {
  const country = countryHint();
  return country ? { country } : undefined;
}

/**
 * Landing-page translations, one file per language so a native speaker can
 * review a single file instead of hunting through components.
 *
 * Keys are the English source strings the components pass to t(). English is
 * the fallback, so a missing key degrades to English rather than showing a raw
 * identifier or a blank page.
 *
 * Lookups go through normalizeKey(), which folds curly quotes, ellipses,
 * en/em dashes, middle dots and runs of whitespace to one canonical form. These
 * files are hand-authored, and a single mismatched apostrophe would otherwise
 * mean a string silently never translates. Folding it here makes '"' and '’'
 * the same key, so the failure mode is impossible rather than merely unlikely.
 */
import bn from "./bn";
import gu from "./gu";
import hi from "./hi";
import kn from "./kn";
import ml from "./ml";
import mr from "./mr";
import or from "./or";
import ta from "./ta";
import te from "./te";
import ur from "./ur";

export const COPY_LOCALES = { hi, bn, mr, te, ta, gu, ur, kn, or, ml };

export function normalizeKey(value) {
  return String(value ?? "")
    .normalize("NFC")
    .replace(/[\u2018\u2019\u02bc\u2032]/g, "'")   // ’ ‘ ′ -> '
    .replace(/[\u201c\u201d\u2033]/g, '"')         // “ ” ″ -> "
    .replace(/[\u2013\u2014\u2212]/g, "-")         // – — − -> -
    .replace(/[\u00b7\u2022\u30fb]/g, "-")         // · • ・ -> -
    .replace(/\u2026/g, "...")                     // … -> ...
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** normalized English -> { lang: text } */
export const COPY_INDEX = (() => {
  const index = new Map();
  for (const [lang, table] of Object.entries(COPY_LOCALES)) {
    for (const [english, text] of Object.entries(table || {})) {
      const key = normalizeKey(english);
      if (!key) continue;
      if (!index.has(key)) index.set(key, {});
      index.get(key)[lang] = text;
    }
  }
  return index;
})();

/** Translation for one English string, or undefined when we have none. */
export function lookupCopy(text) {
  return COPY_INDEX.get(normalizeKey(text));
}

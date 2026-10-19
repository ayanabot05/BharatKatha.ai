/**
 * Minimal per-route SEO helper for the single-page app.
 *
 * The important, crawlable tags live statically in `public/index.html`
 * (so crawlers that do not run JavaScript still see them). This hook keeps
 * the browser tab, the meta description and the canonical URL correct as the
 * user (or a JS-capable crawler such as Googlebot) navigates between routes.
 */
import { useEffect } from "react";

export const SITE_URL = "https://bharatkatha.ai";
export const SITE_NAME = "BharatKatha";
export const DEFAULT_TITLE = "BharatKatha — Storytelling studio for Indian creators";
export const DEFAULT_DESCRIPTION =
  "Turn a one-line idea into a narrated video with AI illustrations, captions and a voice — 11 Indian languages, AI narration in 10.";

const setMeta = (selector, attr, value) => {
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement("meta");
    const [, name] = selector.match(/\[(?:name|property)="([^"]+)"\]/) || [];
    el.setAttribute(attr, name || "");
    document.head.appendChild(el);
  }
  el.setAttribute("content", value);
};

const setLink = (rel, href) => {
  let el = document.head.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
};

/** Update the document title, description, canonical URL and social tags. */
export function useSeo({ title, description, path = "/", noindex = false }) {
  useEffect(() => {
    const fullTitle = title ? `${title} | ${SITE_NAME}` : DEFAULT_TITLE;
    const desc = description || DEFAULT_DESCRIPTION;
    const url = `${SITE_URL}${path === "/" ? "/" : path}`;

    document.title = fullTitle;
    setMeta('meta[name="description"]', "name", desc);
    setMeta('meta[name="robots"]', "name", noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large");
    setMeta('meta[property="og:title"]', "property", fullTitle);
    setMeta('meta[property="og:description"]', "property", desc);
    setMeta('meta[property="og:url"]', "property", url);
    setMeta('meta[name="twitter:title"]', "name", fullTitle);
    setMeta('meta[name="twitter:description"]', "name", desc);
    setLink("canonical", url);
  }, [title, description, path, noindex]);
}

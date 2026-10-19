import { api } from "@/lib/api";

/**
 * First-party visit tracking.
 *
 * Deliberately tiny: this is the only thing the browser reports about itself.
 * Every other funnel stage is recorded by the server in the handler that
 * performs the action, so it cannot be forged or blocked.
 */
const SID_KEY = "bk_session_id";
const VISIT_KEY = "bk_visit_sent";

export function sessionId() {
  try {
    let id = sessionStorage.getItem(SID_KEY);
    if (!id) {
      id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
      sessionStorage.setItem(SID_KEY, id);
    }
    return id;
  } catch {
    // Private mode or blocked storage: still report, just without a stable id.
    return "anon";
  }
}

/** Record a landing visit, at most once per browser session. */
export function trackVisit(path = "/") {
  try {
    if (sessionStorage.getItem(VISIT_KEY)) return;
    sessionStorage.setItem(VISIT_KEY, "1");
  } catch {
    // Cannot de-duplicate without storage; a duplicate visit is better than none.
  }
  api.post("/events", { name: "visit", session_id: sessionId(), path }).catch(() => {
    // Analytics must never surface an error to the visitor.
  });
}

// Local UI testing only. Cloud Run remains private; the Google identity token
// stays in the development server and is never sent to browser JavaScript.
const { execSync } = require("child_process");
const { createProxyMiddleware } = require("http-proxy-middleware");

const target = process.env.BHARATKATHA_DEV_API_ORIGIN;
let cachedToken = "";
let tokenExpiresAt = 0;

function identityToken() {
  if (cachedToken && Date.now() < tokenExpiresAt - 300000) return cachedToken;
  const token = execSync("gcloud auth print-identity-token", {
    encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 15000,
  }).trim();
  const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
  if (!payload.exp || payload.exp * 1000 <= Date.now() + 300000) {
    throw new Error("Google Cloud identity token is missing or expires soon");
  }
  cachedToken = token;
  tokenExpiresAt = payload.exp * 1000;
  return token;
}

module.exports = function setupProxy(app) {
  if (!target) return;
  const origin = new URL(target);
  const isLocalBackend = origin.protocol === "http:" && ["127.0.0.1", "localhost"].includes(origin.hostname);
  if ((!isLocalBackend && origin.protocol !== "https:") || origin.username || origin.password ||
      origin.pathname !== "/" || origin.search || origin.hash) {
    throw new Error("BHARATKATHA_DEV_API_ORIGIN must be an HTTPS origin");
  }
  const port = process.env.PORT || "3004";
  const allowedOrigins = new Set([`http://localhost:${port}`, `http://127.0.0.1:${port}`]);
  app.use("/api", (request, response, next) => {
    const peer = request.socket?.remoteAddress;
    if (peer && !["::1", "127.0.0.1", "::ffff:127.0.0.1"].includes(peer)) {
      response.status(403).json({ detail: "The local studio is available only on this computer." });
      return;
    }
    // The backend's production origin check cannot recognize localhost. Limit
    // this exception to the local UI before removing Origin upstream.
    if (request.headers.origin && !allowedOrigins.has(request.headers.origin)) {
      response.status(403).json({ detail: "This website cannot access the studio." });
      return;
    }
    try {
      if (!isLocalBackend && process.env.BHARATKATHA_DEV_PUBLIC_GATEWAY !== "true") {
        request.cloudIdentityToken = identityToken();
      }
      delete request.headers.origin;
      next();
    } catch (_) {
      response.status(503).json({ detail: "Local cloud sign-in is unavailable. Your saved work is safe." });
    }
  }, createProxyMiddleware({
    target: origin.origin,
    changeOrigin: true,
    secure: !isLocalBackend,
    onProxyReq(proxyRequest, request) {
      if (request.cloudIdentityToken) {
        proxyRequest.setHeader("Authorization", `Bearer ${request.cloudIdentityToken}`);
      }
    },
  }));
};

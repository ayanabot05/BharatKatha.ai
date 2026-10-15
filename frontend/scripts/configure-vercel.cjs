// Run once with the deployed cloud API origin, then commit vercel.json.
const fs = require("fs");
const path = require("path");
const origin = new URL(process.argv[2] || "https://invalid.local");
if (origin.protocol !== "https:" || origin.hostname === "invalid.local" || origin.username || origin.password || origin.pathname !== "/" || origin.search || origin.hash) {
  throw new Error("Usage: node scripts/configure-vercel.cjs https://YOUR-CLOUD-API-DOMAIN");
}
const config = JSON.parse(fs.readFileSync(path.join(__dirname, "../vercel.json"), "utf8"));
config.rewrites = [
  { source: "/api/:path*", destination: `${origin.origin}/api/:path*` },
  { source: "/((?!api/|static/|styles/|showcase/).*)", destination: "/index.html" },
];
fs.writeFileSync(path.join(__dirname, "../vercel.json"), JSON.stringify(config, null, 2) + "\n");
console.log("Configured Vercel API proxy. Set REACT_APP_BACKEND_URL=/ in Vercel.");

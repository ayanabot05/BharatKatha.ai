const path = require("path");

module.exports = {
  webpack: { alias: { "@": path.resolve(__dirname, "src") } },
  jest: { configure: { moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" } } },
  // CRA 5 already enables Tailwind when tailwind.config.js exists.
  // Do not replace postcssOptions.plugins with CRACO's plugin callback.
};

jest.mock("child_process", () => ({ execSync: jest.fn() }));
jest.mock("http-proxy-middleware", () => ({ createProxyMiddleware: jest.fn(() => "proxy") }));

function setup() {
  jest.resetModules();
  process.env.BHARATKATHA_DEV_API_ORIGIN = "https://bharatkatha-api.example.run.app";
  process.env.PORT = "3004";
  const app = { use: jest.fn() };
  require("./setupProxy")(app);
  return {
    middleware: app.use.mock.calls[0],
    execSync: require("child_process").execSync,
    createProxyMiddleware: require("http-proxy-middleware").createProxyMiddleware,
  };
}

afterEach(() => {
  delete process.env.BHARATKATHA_DEV_API_ORIGIN;
  delete process.env.BHARATKATHA_DEV_PUBLIC_GATEWAY;
  delete process.env.PORT;
  jest.clearAllMocks();
});

test("local proxy rejects a foreign origin without requesting a cloud token", () => {
  const { middleware: [path, guard], execSync } = setup();
  const response = { status: jest.fn().mockReturnThis(), json: jest.fn() };
  guard({ headers: { origin: "https://other.example" } }, response, jest.fn());
  expect(path).toBe("/api");
  expect(response.status).toHaveBeenCalledWith(403);
  expect(execSync).not.toHaveBeenCalled();
});

test("local proxy rejects requests from other computers", () => {
  const { middleware: [, guard], execSync } = setup();
  const response = { status: jest.fn().mockReturnThis(), json: jest.fn() };
  guard({ headers: {}, socket: { remoteAddress: "192.0.2.10" } }, response, jest.fn());
  expect(response.status).toHaveBeenCalledWith(403);
  expect(execSync).not.toHaveBeenCalled();
});

test("local proxy keeps the cloud token server side and sends it upstream", () => {
  const { middleware: [, guard], execSync, createProxyMiddleware } = setup();
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url");
  execSync.mockReturnValue(`header.${payload}.signature\n`);
  const request = { headers: { origin: "http://localhost:3004" } };
  const next = jest.fn();
  guard(request, {}, next);
  expect(next).toHaveBeenCalledTimes(1);
  expect(request.headers.origin).toBeUndefined();
  const config = createProxyMiddleware.mock.calls[0][0];
  const proxyRequest = { setHeader: jest.fn() };
  config.onProxyReq(proxyRequest, request);
  expect(proxyRequest.setHeader).toHaveBeenCalledWith("Authorization", expect.stringMatching(/^Bearer header\./));
  expect(config.target).toBe("https://bharatkatha-api.example.run.app");
});

test("public gateway mode forwards application requests without invoking gcloud credentials", () => {
  process.env.BHARATKATHA_DEV_PUBLIC_GATEWAY = "true";
  const { middleware: [, guard], execSync, createProxyMiddleware } = setup();
  const request = { headers: { origin: "http://localhost:3004" } };
  const next = jest.fn();
  guard(request, {}, next);
  expect(next).toHaveBeenCalledTimes(1);
  expect(execSync).not.toHaveBeenCalled();
  const config = createProxyMiddleware.mock.calls[0][0];
  const proxyRequest = { setHeader: jest.fn() };
  config.onProxyReq(proxyRequest, request);
  expect(proxyRequest.setHeader).not.toHaveBeenCalled();
});

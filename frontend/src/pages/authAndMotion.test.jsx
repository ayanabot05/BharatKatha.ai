import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/lib/api";
import MotionSoon from "@/components/MotionSoon";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import AdminLogin from "@/pages/AdminLogin";

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  errMsg: (error) => error.message,
}));
jest.mock("react-router-dom", () => ({
  Link: ({ children, ...props }) => <a {...props}>{children}</a>,
  useNavigate: () => jest.fn(),
  useSearchParams: () => [new URLSearchParams(globalThis.location.search)],
}));

let root;
let container;

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});

const mount = (element) => act(async () => root.render(element));
const node = (id) => container.querySelector(`[data-testid="${id}"]`);

/** Set a controlled input so React's onChange actually fires. */
const type = async (element, value) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  await act(async () => {
    setter.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
};

// ------------------------------------------------------- motion "coming soon"

test("the motion section never claims AI video motion is available today", async () => {
  await mount(<MotionSoon />);
  const text = container.textContent;
  expect(text).toContain("Available now");
  expect(text).toContain("In development");
  expect(text).toContain("is not live yet");
  expect(text).toContain("unbilled");
  // The only call to action here is the notify list — nothing is for sale.
  const buttons = [...container.querySelectorAll("button")].map((b) => b.textContent.trim());
  expect(buttons).toEqual(["Notify me"]);
  expect(text).not.toMatch(/Buy now|Upgrade/i);
});

test("notify-me records an interest against the AI motion topic", async () => {
  api.post.mockResolvedValue({ data: { saved: true, already: false } });
  await mount(<MotionSoon />);
  await type(node("notify-email-input"), "fan@example.com");
  await act(async () => node("notify-submit-btn").click());
  expect(api.post).toHaveBeenCalledWith("/notify", expect.objectContaining({
    email: "fan@example.com", topic: "ai_motion",
  }));
  expect(node("notify-outcome").textContent).toContain("on the list");
});

test("notify-me does not claim success when nothing was saved", async () => {
  api.post.mockResolvedValue({ data: { saved: false } });
  await mount(<MotionSoon />);
  await type(node("notify-email-input"), "fan@example.com");
  await act(async () => node("notify-submit-btn").click());
  const text = node("notify-outcome").textContent;
  expect(text).toContain("couldn’t save");
  expect(text).not.toContain("on the list");
});

// ------------------------------------------------------------- password reset

test("forgot password is honest while email delivery is not configured", async () => {
  api.post.mockResolvedValue({ data: { sent: true, delivery: "manual" } });
  await mount(<ForgotPassword />);
  await type(node("forgot-email-input"), "a@example.com");
  await act(async () => node("forgot-submit-btn").click());
  expect(api.post).toHaveBeenCalledWith("/auth/forgot", { email: "a@example.com" });
  const text = node("forgot-outcome").textContent;
  expect(text).toContain("email delivery is not switched on");
  expect(text).not.toContain("Check your inbox");
});

test("forgot password says check your inbox only when mail really goes out", async () => {
  api.post.mockResolvedValue({ data: { sent: true, delivery: "email" } });
  await mount(<ForgotPassword />);
  await type(node("forgot-email-input"), "a@example.com");
  await act(async () => node("forgot-submit-btn").click());
  expect(node("forgot-outcome").textContent).toContain("Check your inbox");
});

test("reset refuses mismatched passwords without calling the API", async () => {
  window.history.pushState({}, "", "/reset-password?token=" + "t".repeat(40));
  await mount(<ResetPassword />);
  await type(node("reset-password-input"), "brand-new");
  await type(node("reset-confirm-input"), "something-else");
  await act(async () => node("reset-submit-btn").click());
  expect(api.post).not.toHaveBeenCalled();
  expect(node("reset-error").textContent).toContain("do not match");
});

test("reset submits the token and confirms the change", async () => {
  api.post.mockResolvedValue({ data: { ok: true } });
  window.history.pushState({}, "", "/reset-password?token=" + "t".repeat(40));
  await mount(<ResetPassword />);
  await type(node("reset-password-input"), "brand-new");
  await type(node("reset-confirm-input"), "brand-new");
  await act(async () => node("reset-submit-btn").click());
  expect(api.post).toHaveBeenCalledWith("/auth/reset", { token: "t".repeat(40), password: "brand-new" });
  expect(node("reset-done").textContent).toContain("Password changed");
});

test("reset without a token asks for a fresh link", async () => {
  window.history.pushState({}, "", "/reset-password");
  await mount(<ResetPassword />);
  expect(node("reset-no-token")).not.toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});

// ------------------------------------------------------------ administrator

test("administrator sign-in uses the isolated admin endpoint", async () => {
  api.post.mockResolvedValue({ data: { id: "a-1", email: "boss@example.com" } });
  await mount(<AdminLogin />);
  await type(node("admin-email-input"), "boss@example.com");
  await type(node("admin-password-input"), "secret-password");
  await act(async () => node("admin-login-btn").click());
  expect(api.post).toHaveBeenCalledWith("/admin/auth/login", {
    email: "boss@example.com", password: "secret-password",
  });
});

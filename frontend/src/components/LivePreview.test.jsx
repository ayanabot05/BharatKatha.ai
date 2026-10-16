import React, { act } from "react";
import { createRoot } from "react-dom/client";
import LivePreview from "./LivePreview";
import PhoneShort, { SHOWCASE } from "./PhoneShort";

jest.mock("@/lib/api", () => ({ mediaUrl: (value) => value }));
jest.mock("@/context/LocaleContext", () => ({ useLocale: () => ({ t: (value) => value }) }));
jest.mock("@/components/fx", () => ({
  RamAvatar: () => null,
  BlurReveal: () => null,
  reducedMotion: () => true,
}));

test("studio preview does not claim 100% before the video is rendered", async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const project = { id: "story", title: "Story", step: 6, scenes: [], render: { status: "idle" } };
  await act(async () => root.render(<LivePreview project={project} view={6} />));
  expect(container.textContent).toContain("83%");
  await act(async () => root.render(<LivePreview project={{ ...project, render: { status: "rendering", progress: 40 } }} view={6} />));
  expect(container.textContent).toContain("40%");
  await act(async () => root.render(<LivePreview project={{ ...project, render: { status: "done" } }} view={6} />));
  expect(container.textContent).toContain("100%");
  await act(async () => root.unmount());
  container.remove();
});

test("landing hero phone preview positions screen with absolute inset-2.5 so absolute scene image does not collapse height", async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => root.render(<PhoneShort />));
  const screen = container.querySelector('[data-testid="hero-phone-screen"]');
  expect(screen).not.toBeNull();
  expect(screen.className).toContain("absolute");
  expect(screen.className).toContain("inset-2.5");
  const img = screen.querySelector("img");
  expect(img).not.toBeNull();
  expect(img.getAttribute("src")).toBe(SHOWCASE[0].img);
  expect(screen.textContent).toContain(SHOWCASE[0].cap);
  await act(async () => root.unmount());
  container.remove();
});


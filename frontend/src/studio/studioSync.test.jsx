import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Studio from "@/pages/Studio";
import { api } from "@/lib/api";
jest.mock("react-router-dom", () => ({ useParams: () => ({ id: "sync" }), Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a> }));

jest.mock("@/lib/api", () => ({ api: { get: jest.fn() }, errMsg: () => "Connection failed", mediaUrl: (value) => value }));
jest.mock("sonner", () => ({ toast: { success: jest.fn() } }));
jest.mock("@/components/fx", () => ({ Confetti: () => null, RamAvatar: () => null }));
jest.mock("@/components/LivePreview", () => ({ __esModule: true, default: () => null, ramStatus: () => ({ state: "idle" }) }));
jest.mock("@/studio/StepIdea", () => () => null);
jest.mock("@/studio/StepScript", () => () => null);
jest.mock("@/studio/StepStyle", () => () => null);
jest.mock("@/studio/StepAudio", () => () => null);
jest.mock("@/studio/StepRender", () => () => null);
jest.mock("@/studio/StepScenes", () => ({ project, update }) => <button data-testid="save-edit" onClick={() => update({ ...project, title: "Saved edit" })}>Save</button>);

const project = { id: "sync", title: "Initial", language: "en", step: 4, scenes: [] };
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.useFakeTimers(); jest.clearAllMocks();
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.useRealTimers(); });
const mount = () => act(async () => root.render(<Studio />));
const advance = () => act(async () => jest.advanceTimersByTime(15000));

test("a delayed status response cannot overwrite a newer saved edit", async () => {
  let respond;
  api.get.mockResolvedValueOnce({ data: project }).mockImplementationOnce(() => new Promise((resolve) => { respond = resolve; }));
  await mount(); await advance();
  await act(async () => container.querySelector('[data-testid="save-edit"]').click());
  await act(async () => respond({ data: { ...project, title: "Stale poll" } }));
  expect(container.querySelector('[data-testid="studio-project-title"]').textContent).toBe("Saved edit");
});

test("idle project refresh recovers after a connection failure", async () => {
  api.get.mockResolvedValueOnce({ data: project }).mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ data: { ...project, title: "Recovered" } });
  await mount(); await advance();
  expect(container.textContent).toContain("Connection interrupted");
  await advance();
  expect(container.querySelector('[data-testid="studio-project-title"]').textContent).toBe("Recovered");
  expect(container.textContent).not.toContain("Connection interrupted");
});

test("render progress remains visible when another studio step is open", async () => {
  api.get.mockResolvedValue({ data: { ...project, render: { status: "rendering", progress: 40, message: "Rendering scene 2" } } });
  await mount();
  expect(container.textContent).toContain("Rendering your video · 40% · Rendering scene 2");
  await act(async () => [...container.querySelectorAll("button")].find((button) => button.textContent === "View progress").click());
  expect(container.textContent).not.toContain("View progress");
});

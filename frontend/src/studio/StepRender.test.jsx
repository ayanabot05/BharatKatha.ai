import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import StepRender from "./StepRender";

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  errMsg: (error) => error.message,
  mediaUrl: (path) => `/api/media/${path}`,
}));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), info: jest.fn(), success: jest.fn() } }));
jest.mock("react-router-dom", () => ({ Link: ({ children, ...props }) => <a {...props}>{children}</a> }));
jest.mock("@/components/FeedbackForm", () => () => null);
jest.mock("@/components/ui/switch", () => ({ Switch: () => <button type="button" /> }));
jest.mock("@/components/ui/progress", () => ({ Progress: ({ value }) => <div data-testid="progress-value">{value}</div> }));
jest.mock("@/context/LocaleContext", () => ({ useLocale: () => ({ t: (value) => value }) }));

const base = {
  id: "project-1", language: "te", approved: true, validation: { all_passed: true },
  captions_on: true, script: { title: "Telugu story" },
  scenes: [{ id: "scene-1", status: "ready", image_path: "scene.png", approved: true }],
  audio: { path: "voice.wav", mode: "ai" },
  render: { status: "idle", progress: 0 },
};

let root;
let container;
let anchorClick;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  anchorClick = jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  URL.createObjectURL = jest.fn(() => "blob:video");
  URL.revokeObjectURL = jest.fn();
});
afterEach(async () => {
  await act(async () => root.unmount());
  anchorClick.mockRestore();
  container.remove();
});
const mount = (project, update = jest.fn()) => act(async () => root.render(<StepRender project={project} update={update} />));
const node = (id) => container.querySelector(`[data-testid="${id}"]`);

test("a lost render response checks saved job status before offering a retry", async () => {
  const update = jest.fn();
  const running = { ...base, render: { status: "rendering", progress: 1, message: "Queued" } };
  api.post.mockRejectedValue(new Error("Connection interrupted"));
  api.get.mockResolvedValue({ data: running });
  await mount(base, update);
  await act(async () => node("render-btn").click());
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.get).toHaveBeenCalledWith("/projects/project-1");
  expect(update).toHaveBeenCalledWith(running);
  expect(toast.info).toHaveBeenCalled();
  expect(toast.error).not.toHaveBeenCalled();
});

test("rendering shows persisted progress and a clear leave-page message", async () => {
  await mount({ ...base, render: { status: "rendering", progress: 40, message: "Rendering scene 2" } });
  expect(node("render-btn").disabled).toBe(true);
  expect(node("progress-value").textContent).toBe("40");
  expect(node("render-message").textContent).toContain("Rendering scene 2");
  expect(container.textContent).toContain("You can leave this page");
});

test("a finished video previews and downloads through the authorized API", async () => {
  const project = { ...base, render: { status: "done", progress: 100, video_path: "video.mp4" } };
  global.fetch = jest.fn().mockResolvedValue({
    ok: true, headers: { get: () => "video/mp4" }, blob: () => Promise.resolve(new Blob(["mp4"])),
  });
  await mount(project);
  expect(node("final-video").getAttribute("src")).toBe("/api/media/video.mp4");
  await act(async () => node("download-mp4-btn").click());
  expect(fetch).toHaveBeenCalledWith("/api/media/video.mp4?download=1", { credentials: "include" });
  expect(anchorClick).toHaveBeenCalledTimes(1);
});

test("a preview failure gives a retry without hiding the download", async () => {
  await mount({ ...base, render: { status: "done", video_path: "video.mp4" } });
  await act(async () => node("final-video").dispatchEvent(new Event("error")));
  expect(container.textContent).toContain("Retry preview");
  expect(node("download-mp4-btn")).not.toBeNull();
  await act(async () => [...container.querySelectorAll("button")].find((button) => button.textContent === "Retry preview").click());
  expect(node("final-video")).not.toBeNull();
});

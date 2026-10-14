import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import StepAudio from "./StepAudio";
import StepScript from "./StepScript";
import StepScenes from "./StepScenes";
import StudioStepper from "@/components/StudioStepper";

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  errMsg: (e) => e.message, mediaUrl: (s) => s }));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock("@/components/ui/slider", () => ({ Slider: () => <div /> }));

let container, root;
const players = [];
const project = { id: "quality-test", language: "en", step: 4, approved: true,
  scenes: [{ id: "one", narration: "Opening narration", visual: "Village", status: "ready", image_path: "scene.png" }],
  script: { title: "Story", hook: "Old hook", ending: "Old ending", scenes: [
    { narration: "Opening narration", visual: "Village" },
    { narration: "Middle narration", visual: "A decision" },
    { narration: "Closing narration", visual: "Return home" }] } };

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  api.get.mockResolvedValue({ data: { voices: [
    { id: "coral", name: "Female voice", desc: "Google Cloud Chirp 3 HD" },
    { id: "fable", name: "Male voice", desc: "Google Cloud Chirp 3 HD" },
  ] } });
  players.length = 0;
  URL.createObjectURL = jest.fn(() => `blob:preview-${players.length}`);
  URL.revokeObjectURL = jest.fn();
  global.Audio = jest.fn((src) => {
    const player = { src, play: jest.fn().mockResolvedValue(), pause: jest.fn() };
    players.push(player);
    return player;
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
const node = (id) => container.querySelector(`[data-testid="${id}"]`);
const click = async (id) => act(async () => node(id).click());
const mount = async (component) => act(async () => root.render(component));
const edit = async (id, value) => act(async () => {
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(node(id), value);
  node(id).dispatchEvent(new Event("input", { bubbles: true }));
});

test("mobile step menu replaces horizontal navigation and blocks locked steps", async () => {
  const setView = jest.fn();
  await mount(<StudioStepper view={2} maxStep={4} setView={setView} />);
  const menu = node("studio-step-select");
  expect(menu.className).toContain("sm:hidden");
  expect(node("studio-step-list").className).not.toContain("overflow-x-auto");
  expect(menu.querySelector('option[value="5"]').disabled).toBe(true);
  await act(async () => {
    menu.value = "3";
    menu.dispatchEvent(new Event("change", { bubbles: true }));
  });
  expect(setView).toHaveBeenCalledWith(3);
});

test("opening and ending edits change the narration actually sent to the backend", async () => {
  api.patch.mockResolvedValue({ data: project });
  await mount(<StepScript project={project} update={jest.fn()} />);
  await edit("script-hook-input", "A changed opening");
  await edit("script-ending-input", "An earned ending");
  await click("save-script-btn");
  const saved = api.patch.mock.calls[0][1].script;
  expect(saved.scenes[0].narration).toBe("A changed opening");
  expect(saved.scenes[2].narration).toBe("An earned ending");
  expect(saved.hook).toBe(saved.scenes[0].narration);
  expect(saved.ending).toBe(saved.scenes[2].narration);
  expect(node("scene-narration-input-0")).toBeNull();
});

test("starting another voice preview stops the old audio", async () => {
  api.post.mockResolvedValue({ data: new Blob(["voice"]) });
  await mount(<StepAudio project={project} update={jest.fn()} />);
  await click("voice-preview-coral");
  await click("voice-preview-fable");
  expect(players).toHaveLength(2);
  expect(players[0].pause).toHaveBeenCalledTimes(1);
  expect(URL.revokeObjectURL).toHaveBeenCalledWith(players[0].src);
  await click("audio-tab-upload");
  expect(players[1].pause).toHaveBeenCalledTimes(1);
});

test("a late preview response cannot start audio after leaving the voice tab", async () => {
  let finish;
  api.post.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  await mount(<StepAudio project={project} update={jest.fn()} />);
  await click("voice-preview-coral");
  await click("audio-tab-upload");
  await act(async () => finish({ data: new Blob(["voice"]) }));
  expect(players).toHaveLength(0);
});

test("Odia preview and generation do not offer an unavailable voice", async () => {
  await mount(<StepAudio project={{ ...project, language: "or" }} update={jest.fn()} />);
  expect(node("voice-preview-coral").disabled).toBe(true);
  expect(node("voice-preview-fable").disabled).toBe(true);
  expect(node("generate-voice-btn").disabled).toBe(true);
});

test("failed picture approval shows one inline error without a second toast", async () => {
  api.post.mockRejectedValue(new Error("Approval unavailable"));
  await mount(<StepScenes project={project} update={jest.fn()} />);
  await click("scene-approve-btn-0");
  expect(container.textContent.split("Approval unavailable")).toHaveLength(2);
  expect(toast.error).not.toHaveBeenCalled();
});

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import StepAudio from "./StepAudio";
import StepScript from "./StepScript";
import StepScenes from "./StepScenes";
import StudioStepper from "@/components/StudioStepper";
import { LocaleProvider } from "@/context/LocaleContext";
import { ProjectCopyProvider } from "@/context/ProjectCopyContext";
import { translateStudioTelugu } from "@/context/studioTelugu";

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  errMsg: (e) => e.message, mediaUrl: (s) => s }));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), info: jest.fn(), success: jest.fn(), warning: jest.fn() } }));
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
  localStorage.clear();
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

test("Telugu voice screen translates tabs, controls, provider labels and help text", async () => {
  localStorage.setItem("vidbharat_ui_lang", "te");
  await mount(<LocaleProvider><StepAudio project={{ ...project, language: "te" }} update={jest.fn()} /></LocaleProvider>);
  expect(node("audio-tab-ai").textContent).toBe("ప్రాంతీయ ఏఐ వాయిస్");
  expect(node("generate-voice-btn").textContent).toContain("అన్ని దృశ్యాలకు కథనం తయారు చేయండి");
  for (const english of ["Female voice", "Male voice", "Choose a female", "At 1.00x", "Record my voice", "Upload voice-over", "Google Cloud Chirp"])
    expect(container.textContent).not.toContain(english);
  await click("audio-tab-record");
  expect(container.textContent).toContain("మీ కథనాన్ని రికార్డ్ చేయడానికి నొక్కండి");
  await click("audio-tab-upload");
  expect(container.textContent).toContain("అప్‌లోడ్ చేయండి");
});

test("scene descriptions translate for display without changing a saved narration-only edit", async () => {
  localStorage.setItem("vidbharat_ui_lang", "te");
  const story = { ...project, id: "translated-scenes", scenes: [{ ...project.scenes[0], visual: "Father enters a kitchen" }], script: {} };
  api.get.mockResolvedValue({ data: { translations: { "Father enters a kitchen": "నాన్న వంటగదిలోకి వెళ్తారు" } } });
  api.patch.mockResolvedValue({ data: story });
  await mount(<LocaleProvider><ProjectCopyProvider project={story} enabled><StepScenes project={story} update={jest.fn()} /></ProjectCopyProvider></LocaleProvider>);
  const visual = container.querySelectorAll("textarea")[1];
  expect(visual.value).toBe("నాన్న వంటగదిలోకి వెళ్తారు");
  const narration = container.querySelector("textarea");
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(narration, "కొత్త కథనం");
    narration.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const save = [...container.querySelectorAll("button")].find((button) => button.textContent.includes("దృశ్యాన్ని భద్రపరచండి"));
  await act(async () => save.click());
  expect(api.patch.mock.calls[0][1]).toEqual({ narration: "కొత్త కథనం", visual: "Father enters a kitchen" });
});

test("Telugu review advisories retain numbers and translate dynamic server copy", () => {
  expect(translateStudioTelugu("Hook too wordy (13 words). Aim for 5-8 spoken words; check the generated audio timing.")).toContain("13");
  expect(translateStudioTelugu("Optimal scene count (5).")).toBe("తగిన దృశ్యాల సంఖ్య (5).");
  expect(translateStudioTelugu("Narration has 58 words for 45s. Check the generated audio duration; add content only if the original idea needs more story action.")).toContain("58");
});

test("caption failure keeps playable voice and blocks captioned render until explicit choice", async () => {
  const update = jest.fn();
  const failed = { ...project, captions_on: true, audio: { path: "voice.mp3", mode: "ai", caption_status: "failed", duration: 4 } };
  api.patch.mockResolvedValue({ data: { ...failed, captions_on: false } });
  await mount(<StepAudio project={failed} update={update} />);
  expect(node("current-audio-player").getAttribute("src")).toBe("voice.mp3");
  expect(node("audio-continue-btn").disabled).toBe(true);
  const button = [...container.querySelectorAll("button")].find((item) => item.textContent === "Continue without captions");
  await act(async () => button.click());
  expect(api.patch).toHaveBeenCalledWith(`/projects/${project.id}`, { captions_on: false });
  expect(update).toHaveBeenCalledWith(expect.objectContaining({ captions_on: false }), 6);
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
  await mount(<StepAudio project={{ ...project, audio: { provider: "edge" } }} update={jest.fn()} />);
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
  await mount(<StepAudio project={{ ...project, audio: { provider: "edge" } }} update={jest.fn()} />);
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

test("Piper selection stays explicit for preview and scene narration", async () => {
  api.get.mockResolvedValue({ data: { voices: [
    { id: "coral", name: "Female voice", desc: "Edge" },
    { id: "fable", name: "Male voice", desc: "Edge" },
  ], voice_providers: [
    { id: "edge", name: "Edge", type: "hosted", languages: ["te"] },
    { id: "piper", name: "Piper", type: "open", languages: ["te"] },
  ], default_voice_provider: "edge" } });
  api.post.mockImplementation((url) => Promise.resolve({ data: url === "/voice/preview" ? new Blob(["voice"]) : project }));
  await mount(<StepAudio project={{ ...project, language: "te" }} update={jest.fn()} />);
  await act(async () => {
    node("voice-provider-select").value = "piper";
    node("voice-provider-select").dispatchEvent(new Event("change", { bubbles: true }));
  });
  expect(node("voice-preview-fable")).toBeNull();
  await click("voice-preview-coral");
  await click("generate-voice-btn");
  expect(api.post).toHaveBeenCalledWith("/voice/preview", expect.objectContaining({ provider: "piper", language: "te" }), expect.any(Object));
  expect(api.post).toHaveBeenCalledWith(`/projects/${project.id}/audio/ai`, expect.objectContaining({ provider: "piper", voice: "coral" }));
});

test("Hindi selects its available local voice when the Telugu Piper default is unavailable", async () => {
  api.get.mockResolvedValue({ data: { voices: [
    { id: "coral", name: "Female voice", desc: "Edge" },
    { id: "fable", name: "Male voice", desc: "Edge" },
  ], voice_providers: [
    { id: "piper", name: "Piper", type: "open", languages: ["te"] },
    { id: "supertonic", name: "Supertonic 3", type: "open", languages: ["hi"] },
    { id: "edge", name: "Edge", type: "hosted", languages: ["hi"] },
  ], default_voice_provider: "piper" } });
  api.post.mockImplementation((url) => Promise.resolve({ data: url === "/voice/preview" ? new Blob(["voice"]) : project }));
  await mount(<StepAudio project={{ ...project, language: "hi" }} update={jest.fn()} />);
  expect(node("voice-provider-select").value).toBe("supertonic");
  expect(node("voice-preview-M1")).not.toBeNull();
  expect(node("generate-voice-btn").disabled).toBe(false);
  await click("voice-preview-M1");
  await click("generate-voice-btn");
  expect(api.post).toHaveBeenCalledWith("/voice/preview", expect.objectContaining({ provider: "supertonic", voice: "M1", language: "hi" }), expect.any(Object));
  expect(api.post).toHaveBeenCalledWith(`/projects/${project.id}/audio/ai`, expect.objectContaining({ provider: "supertonic", voice: "M1" }));
});

test("premium voice requires a visible estimate and typed request budget", async () => {
  api.get.mockResolvedValue({ data: { voices: [
    { id: "coral", name: "Female voice", desc: "Regional voice" },
  ], voice_providers: [
    { id: "edge", name: "Edge", type: "hosted", languages: ["en"] },
    { id: "google_chirp", name: "Chirp", type: "premium", languages: ["en"] },
  ], premium_voice_rates: { google_chirp: { model_id: "chirp3-hd",
    all_in_inr_per_1000_chars: "2", max_request_inr: "1" } },
  default_voice_provider: "edge" } });
  api.post.mockImplementation((url) => Promise.resolve({ data: url === "/voice/preview" ? new Blob(["voice"]) : project }));
  await mount(<StepAudio project={project} update={jest.fn()} />);
  await act(async () => {
    node("voice-provider-select").value = "google_chirp";
    node("voice-provider-select").dispatchEvent(new Event("change", { bubbles: true }));
  });
  expect(container.textContent).toContain("₹0.04");
  expect(node("generate-voice-btn").disabled).toBe(true);
  expect(node("voice-preview-coral").disabled).toBe(true);
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(node("premium-voice-budget"), "0.04");
    node("premium-voice-budget").dispatchEvent(new Event("input", { bubbles: true }));
  });
  expect(node("generate-voice-btn").disabled).toBe(false);
  await click("generate-voice-btn");
  expect(api.post).toHaveBeenCalledWith(`/projects/${project.id}/audio/ai`,
    expect.objectContaining({ provider: "google_chirp", max_cost_inr: 0.04 }));
});

test("failed picture approval shows one inline error without a second toast", async () => {
  api.post.mockRejectedValue(new Error("Approval unavailable"));
  await mount(<StepScenes project={project} update={jest.fn()} />);
  await click("scene-approve-btn-0");
  expect(container.textContent.split("Approval unavailable")).toHaveLength(2);
  expect(toast.error).not.toHaveBeenCalled();
});

test("lost picture request response checks saved status before suggesting another request", async () => {
  const update = jest.fn();
  const pending = { ...project, scenes: [{ ...project.scenes[0], status: "pending", image_path: null }] };
  const queued = { ...pending, scenes: [{ ...pending.scenes[0], status: "queued" }] };
  api.post.mockRejectedValue(new Error("Connection interrupted"));
  api.get.mockResolvedValue({ data: queued });
  await mount(<LocaleProvider><ProjectCopyProvider project={pending} enabled><StepScenes project={pending} update={update} /></ProjectCopyProvider></LocaleProvider>);
  await click("generate-pictures-btn");
  expect(api.post).toHaveBeenCalledWith(`/projects/${project.id}/scenes/generate`);
  expect(api.get).toHaveBeenCalledWith(`/projects/${project.id}`);
  expect(update).toHaveBeenCalledWith(queued);
  expect(toast.info).toHaveBeenCalled();
  expect(toast.error).not.toHaveBeenCalled();
});

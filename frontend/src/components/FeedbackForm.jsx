import { useState } from "react";
import { api, errMsg } from "@/lib/api";

export default function FeedbackForm({ projectId }) {
  const [form, setForm] = useState({ rating: 4, area: "Story content", comment: "", permission_to_train: false });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await api.post("/feedback", { ...form, project_id: projectId || null }); setMessage("Thank you. Your feedback is saved for review."); setForm({ ...form, comment: "" }); }
    catch (e) { setMessage(errMsg(e)); } finally { setBusy(false); }
  };
  return <form onSubmit={submit} className="card p-5 space-y-4" data-testid="beta-feedback">
    <div><h2 className="text-lg font-bold">Help improve the studio</h2><p className="text-sm text-[#607269]">What worked, and what should we improve?</p></div>
    <div className="grid sm:grid-cols-2 gap-3">
      <label className="text-sm">Your rating<select className="block w-full mt-1 rounded-lg border p-2" value={form.rating} onChange={e => setForm({ ...form, rating: Number(e.target.value) })}>{[1,2,3,4,5].map(n => <option key={n} value={n}>{n} / 5</option>)}</select></label>
      <label className="text-sm">About<select className="block w-full mt-1 rounded-lg border p-2" value={form.area} onChange={e => setForm({ ...form, area: e.target.value })}>{["Story content", "Pictures", "Voice and pauses", "Captions and timing", "Ease of use", "Other"].map(x => <option key={x}>{x}</option>)}</select></label>
    </div>
    <label className="block text-sm">Your feedback<textarea required minLength={3} maxLength={2000} rows={3} value={form.comment} onChange={e => setForm({ ...form, comment: e.target.value })} className="block w-full mt-1 rounded-lg border p-3" placeholder="Tell us what you expected and what happened." /></label>
    <label className="flex gap-2 text-xs text-[#607269]"><input type="checkbox" checked={form.permission_to_train} onChange={e => setForm({ ...form, permission_to_train: e.target.checked })} />Allow this feedback to be considered for future model training after human review. Optional.</label>
    <button disabled={busy} className="btn-primary" type="submit">{busy ? "Saving…" : "Send feedback"}</button>
    {message && <p role="status" className="text-sm">{message}</p>}
  </form>;
}

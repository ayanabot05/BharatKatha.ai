import { useAuth } from "@/context/AuthContext";
import { useLocale, UI_LANGUAGES } from "@/context/LocaleContext";
import FeedbackForm from "@/components/FeedbackForm";
export default function Settings() {
  const { user, logout } = useAuth();
  const { locale, changeLocale, t } = useLocale();
  return <div className="max-w-3xl space-y-5">
    <h1 className="text-3xl font-bold">{t("settings")}</h1>
    <section className="card p-5" data-testid="settings-profile"><h2 className="font-bold">Your account</h2><p className="mt-3">{user?.name}</p><p className="text-sm text-[#607269] break-all">{user?.email}</p><p className="mt-3 text-sm">Plan: <strong className="capitalize">{user?.plan || "free"}</strong> · Private beta</p><p className="mt-2 text-sm text-[#607269]">No paid subscription is managed here. Beta generation limits apply to keep the studio available for everyone.</p></section>
    <section className="card p-5"><label className="block font-bold" htmlFor="settings-language">{t("language")}</label><select id="settings-language" value={locale} onChange={e => changeLocale(e.target.value)} className="mt-3 rounded-lg border p-3">{UI_LANGUAGES.map(l => <option value={l.id} key={l.id}>{l.label}</option>)}</select><p className="mt-2 text-sm text-[#607269]">Your language preference is remembered on this device. Choose the narration language when creating a story.</p></section>
    <section className="card p-5" data-testid="settings-youtube"><h2 className="font-bold">Sharing your video</h2><p className="mt-2 text-sm text-[#607269]">Download your finished video and upload it in YouTube or Instagram. Direct publishing is not available in this beta.</p></section>
    <FeedbackForm />
    <section className="card p-5"><h2 className="font-bold">Your stories and feedback</h2><p className="mt-2 text-sm text-[#607269]">Stories are processed by cloud AI services to create your video. Feedback is reviewed before improvements are released. Your account activity does not automatically train a model.</p><button className="btn-secondary mt-4" onClick={logout}>{t("sign_out")}</button></section>
  </div>;
}

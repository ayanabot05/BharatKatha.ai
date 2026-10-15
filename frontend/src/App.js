import "@/App.css";
import { lazy, Suspense, Component } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { LocaleProvider } from "@/context/LocaleContext";
import AppShell from "@/components/AppShell";
const Landing = lazy(() => import("@/pages/Landing"));
const AuthPage = lazy(() => import("@/pages/AuthPage"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Studio = lazy(() => import("@/pages/Studio"));
const Coach = lazy(() => import("@/pages/Coach"));
const Settings = lazy(() => import("@/pages/Settings"));
import { Loader2 } from "lucide-react";

class PageBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <main className="p-8 text-center"><h1>We couldn’t open this page.</h1><p className="my-4">Your saved stories are safe. Check your connection and reload.</p><button className="btn-primary" onClick={() => window.location.reload()}>Reload page</button></main> : this.props.children;
  }
}

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null)
    return <div className="min-h-screen grid place-items-center"><Loader2 className="animate-spin text-violet-600" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function PublicOnly({ children }) {
  const { user } = useAuth();
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <div className="App">
      <LocaleProvider>
        <AuthProvider>
          <BrowserRouter>
            <PageBoundary><Suspense fallback={<div role="status" className="min-h-screen grid place-items-center">Loading your studio…</div>}><Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<PublicOnly><AuthPage mode="login" /></PublicOnly>} />
              <Route path="/register" element={<PublicOnly><AuthPage mode="register" /></PublicOnly>} />
              <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
              <Route path="/studio/:id" element={<Protected><Studio /></Protected>} />
              <Route path="/coach" element={<Protected><Coach /></Protected>} />
              <Route path="/settings" element={<Protected><Settings /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes></Suspense></PageBoundary>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </LocaleProvider>
    </div>
  );
}

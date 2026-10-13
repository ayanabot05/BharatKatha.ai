import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { LocaleProvider } from "@/context/LocaleContext";
import AppShell from "@/components/AppShell";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Dashboard from "@/pages/Dashboard";
import Studio from "@/pages/Studio";
import Coach from "@/pages/Coach";
import Settings from "@/pages/Settings";
import { Loader2 } from "lucide-react";

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
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<PublicOnly><AuthPage mode="login" /></PublicOnly>} />
              <Route path="/register" element={<PublicOnly><AuthPage mode="register" /></PublicOnly>} />
              <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
              <Route path="/studio/:id" element={<Protected><Studio /></Protected>} />
              <Route path="/coach" element={<Protected><Coach /></Protected>} />
              <Route path="/settings" element={<Protected><Settings /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </LocaleProvider>
    </div>
  );
}

import { useEffect, useState } from "react";
import Analytics from "./pages/Analytics";
import Alerts from "./pages/Alerts";
import Cameras from "./pages/Cameras";
import LiveCameras from "./pages/LiveCameras";
import NotFound from "./pages/NotFound";
import Sectors from "./pages/Sectors";
import Settings from "./pages/Settings";
import Tracking from "./pages/Tracking";
import AppLayout from "./components/layout/AppLayout";
import CameraGrid from "./components/cameras/CameraGrid";
import AlertCenter from "./components/alerts/AlertCenter";
import DetectionPanel from "./components/detection/DetectionPanel";
import AnalyticsPanel from "./components/analytics/AnalyticsPanel";
import SectorRiskMap from "./components/map/SectorRiskMap";
import SystemOverview from "./components/layout/SystemOverview";
import { useAlertWebSocket } from "./hooks/useAlertWebSocket";

import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AdminControlPage from "./pages/AdminControlPage";
import { useAuthStore } from "./state/authStore";

function App() {
  useAlertWebSocket();
  const [path, setPath] = useState(() =>
    window.location.pathname === "/" ? "/dashboard" : window.location.pathname,
  );

  const { checkAuth, isAuthenticated, authInitialized, user } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (window.location.pathname === "/")
      window.history.replaceState({}, "", "/dashboard");
    const handlePopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (nextPath: string) => {
    if (nextPath === path) return;
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  };

  if (path === "/forgot-password") {
    return <ForgotPasswordPage onNavigate={navigate} />;
  }

  if (path.startsWith("/reset-password")) {
    return <ResetPasswordPage onNavigate={navigate} />;
  }

  if (path === "/login") {
    if (authInitialized && isAuthenticated) {
      const redirectPath = user?.role === "MAIN_ADMIN" ? "/admin-control" : "/dashboard";
      window.history.replaceState({}, "", redirectPath);
      return (
        <AppLayout currentPath={redirectPath} onNavigate={navigate}>
          {renderPage(redirectPath, navigate, user, authInitialized, isAuthenticated)}
        </AppLayout>
      );
    }
    return <LoginPage onNavigate={navigate} />;
  }

  return (
    <AppLayout currentPath={path} onNavigate={navigate}>
      {renderPage(path, navigate, user, authInitialized, isAuthenticated)}
    </AppLayout>
  );
}

function renderPage(
  path: string,
  navigate: (path: string) => void,
  user: any,
  authInitialized: boolean,
  isAuthenticated: boolean,
) {
  if (path.startsWith("/admin-control")) {
    if (!authInitialized) {
      return (
        <div className="flex h-64 items-center justify-center text-xs text-[#8B949E]">
          Initializing NetraKon security session...
        </div>
      );
    }
    if (!isAuthenticated || !user) {
      return <LoginPage onNavigate={navigate} />;
    }
    if (user.role !== "MAIN_ADMIN") {
      return (
        <div className="p-8 text-center">
          <h2 className="text-xl font-bold text-red-400">403 Forbidden</h2>
          <p className="mt-2 text-sm text-[#8B949E]">
            Main Administrator privilege required to access Admin Control.
          </p>
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className="mt-4 rounded bg-[#3B82F6] px-4 py-2 text-xs font-semibold text-white"
          >
            Return to Command Center
          </button>
        </div>
      );
    }
    return <AdminControlPage onNavigate={navigate} currentSubPath={path} />;
  }

  switch (path) {
    case "/dashboard":
      return <Dashboard />;
    case "/cameras/live":
    case "/live-cameras":
      return <LiveCameras />;
    case "/alerts":
      return <Alerts />;
    case "/tracking":
      return <Tracking />;
    case "/analytics":
      return <Analytics />;
    case "/sectors":
      return <Sectors />;
    case "/cameras":
      return <Cameras />;
    case "/settings":
      return <Settings />;
    default:
      return <NotFound onReturn={() => navigate("/dashboard")} />;
  }
}

function Dashboard() {
  return (
    <div className="mx-auto max-w-[1800px] space-y-4 p-4 sm:p-6">
      <SystemOverview />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(320px,3fr)]">
        <section className="min-w-0">
          <CameraGrid />
          <SectorRiskMap />
          <AnalyticsPanel />
        </section>
        <aside className="min-w-0 space-y-4">
          <AlertCenter />
          <DetectionPanel />
        </aside>
      </div>
    </div>
  );
}

export default App;

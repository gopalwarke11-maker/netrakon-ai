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

function App() {
  useAlertWebSocket();
  const [path, setPath] = useState(() =>
    window.location.pathname === "/" ? "/dashboard" : window.location.pathname,
  );

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

  return (
    <AppLayout currentPath={path} onNavigate={navigate}>
      {renderPage(path, navigate)}
    </AppLayout>
  );
}

function renderPage(path: string, navigate: (path: string) => void) {
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

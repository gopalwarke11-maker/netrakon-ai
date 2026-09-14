import { useState, type ReactNode } from "react";
import {
  BarChart3,
  Bell,
  Camera,
  ChevronRight,
  LayoutDashboard,
  Map,
  Menu,
  ScanFace,
  Settings,
  Video,
  X,
} from "lucide-react";
import { useBackendHealth } from "../../api/hooks";
import TopNav from "./TopNav";

interface AppLayoutProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: ReactNode;
}

const navigation = [
  { label: "COMMAND CENTER", path: "/dashboard", icon: LayoutDashboard },
  { label: "LIVE CAMERAS", path: "/cameras/live", icon: Video },
  { label: "ALERTS", path: "/alerts", icon: Bell },
  { label: "TRACKING", path: "/tracking", icon: ScanFace },
  { label: "ANALYTICS", path: "/analytics", icon: BarChart3 },
  { label: "SECTORS", path: "/sectors", icon: Map },
  { label: "CAMERAS", path: "/cameras", icon: Camera },
  { label: "SETTINGS", path: "/settings", icon: Settings },
];

function AppLayout({ currentPath, onNavigate, children }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const healthQuery = useBackendHealth();

  const navigate = (path: string) => {
    onNavigate(path);
    setSidebarOpen(false);
  };

  const backendStatus = healthQuery.isPending
    ? "CHECKING"
    : healthQuery.isSuccess
      ? "LIVE BACKEND"
      : "OFFLINE";

  return (
    <div className="min-h-screen bg-[#0A0E14] text-[#E6EDF3]">
      <TopNav />
      <div className="flex">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="fixed bottom-4 left-4 z-30 grid size-11 place-items-center border border-[#2A3441] bg-[#141A23] text-[#E6EDF3] shadow-xl lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={19} />
        </button>
        {sidebarOpen && (
          <button
            type="button"
            aria-label="Close navigation overlay"
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          />
        )}
        <aside
          className={`fixed inset-y-0 left-0 z-40 w-64 border-r border-[#2A3441] bg-[#111923] pt-16 transition-transform lg:sticky lg:top-0 lg:z-10 lg:block lg:h-[calc(100vh-64px)] lg:w-56 lg:translate-x-0 lg:pt-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
        >
          <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-4 lg:hidden">
            <span className="text-xs font-bold tracking-wider">NAVIGATION</span>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close navigation"
            >
              <X size={17} />
            </button>
          </div>
          <div className="border-b border-[#2A3441] px-4 py-4">
            <div
              className={`flex items-center gap-2 text-[10px] font-bold tracking-[0.16em] ${healthQuery.isSuccess ? "text-green-300" : "text-orange-300"}`}
            >
              <span
                className={`size-2 rounded-full ${healthQuery.isSuccess ? "bg-green-400" : "bg-orange-400"}`}
              />
              {backendStatus}
            </div>
            <p className="mt-2 text-[9px] leading-relaxed text-[#8B949E]">
              {healthQuery.isSuccess
                ? "DATA SOURCES CONNECTED"
                : "BACKEND UNAVAILABLE // SHOWING LOCAL EMPTY STATE"}
            </p>
          </div>
          <nav className="space-y-1 p-3" aria-label="Primary navigation">
            {navigation.map(({ label, path, icon: Icon }) => {
              const active = currentPath === path;
              return (
                <button
                  key={path}
                  type="button"
                  onClick={() => navigate(path)}
                  className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-[10px] font-semibold tracking-wider transition ${active ? "border-l-2 border-[#3B82F6] bg-[#3B82F6]/10 text-[#E6EDF3]" : "border-l-2 border-transparent text-[#8B949E] hover:bg-[#141A23] hover:text-[#E6EDF3]"}`}
                >
                  <Icon
                    size={15}
                    className={active ? "text-[#3B82F6]" : "text-[#8B949E]"}
                    aria-hidden="true"
                  />
                  {label}
                  <ChevronRight
                    size={12}
                    className={`ml-auto ${active ? "text-[#3B82F6]" : "opacity-0"}`}
                    aria-hidden="true"
                  />
                </button>
              );
            })}
          </nav>
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}

export default AppLayout;

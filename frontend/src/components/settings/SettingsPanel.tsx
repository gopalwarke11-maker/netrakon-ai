import {
  BellRing,
  BrainCircuit,
  CheckCircle2,
  CircleDot,
  Gauge,
  Moon,
  Radio,
  Settings2,
  Volume2,
  Waypoints,
} from "lucide-react";
import { useBackendHealth, useCameras } from "../../api/hooks";
import { useSettingsStore } from "../../state/settingsStore";

type BooleanSetting =
  | "detectionEnabled"
  | "trackingEnabled"
  | "recording"
  | "alertSound"
  | "darkMode"
  | "highRiskAlerts"
  | "notificationDisplay"
  | "autoReconnect"
  | "compactMode"
  | "animations"
  | "fullscreen";

function SettingsPanel() {
  const state = useSettingsStore();
  const healthQuery = useBackendHealth();
  const camerasQuery = useCameras();
  const toggle = (setting: BooleanSetting) => state.toggleSetting(setting);
  const cameraOptions = camerasQuery.data ?? [];
  const groups = [
    {
      title: "AI MONITORING",
      items: [
        ["detectionEnabled", "Detection", BrainCircuit],
        ["trackingEnabled", "Tracking", Waypoints],
      ] as const,
    },
    {
      title: "ALERTS",
      items: [
        ["alertSound", "Alert sound", Volume2],
        ["highRiskAlerts", "High-risk alerts", BellRing],
        ["notificationDisplay", "Notification display", Radio],
      ] as const,
    },
    {
      title: "CAMERA",
      items: [
        ["autoReconnect", "Auto reconnect", Radio],
        ["recording", "Recording", CircleDot],
      ] as const,
    },
    {
      title: "INTERFACE",
      items: [
        ["compactMode", "Compact mode", Gauge],
        ["animations", "Animations", Settings2],
        ["fullscreen", "Fullscreen", Moon],
      ] as const,
    },
  ];

  return (
    <section className="border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <Settings2 size={15} className="text-[#3B82F6]" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">
            SYSTEM SETTINGS
          </h2>
        </div>
        <span className="text-[10px] text-[#8B949E]">BACKEND-AWARE</span>
      </div>
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        {groups.map((group) => (
          <div key={group.title}>
            <p className="mb-2 text-[9px] font-bold tracking-[0.16em] text-[#8B949E]">
              {group.title}
            </p>
            <div className="divide-y divide-[#2A3441] border border-[#2A3441]">
              {group.items.map(([key, label, Icon]) => {
                const enabled = state[key];
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggle(key)}
                    className="flex w-full items-center justify-between px-3 py-2.5 text-left hover:bg-[#0A0E14]"
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <Icon
                        size={13}
                        className="text-[#8B949E]"
                        aria-hidden="true"
                      />
                      {label}
                    </span>
                    <span
                      className={`relative h-4 w-8 border ${enabled ? "border-[#3B82F6] bg-[#3B82F6]/20" : "border-[#2A3441]"}`}
                    >
                      <span
                        className={`absolute top-0.5 size-2.5 ${enabled ? "translate-x-[17px] bg-[#3B82F6]" : "translate-x-0.5 bg-[#8B949E]"}`}
                      />
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 border-t border-[#2A3441] p-4 sm:grid-cols-2">
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E]">
          CONFIDENCE THRESHOLD{" "}
          <input
            type="range"
            min="0"
            max="100"
            value={state.confidenceThreshold}
            onChange={(event) =>
              state.setConfidenceThreshold(Number(event.target.value))
            }
            className="mt-2 w-full accent-[#3B82F6]"
          />
          <span className="float-right text-[#E6EDF3]">
            {state.confidenceThreshold}%
          </span>
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E]">
          DEFAULT CAMERA
          <select
            value={state.defaultCamera}
            onChange={(event) => state.setDefaultCamera(event.target.value)}
            className="mt-2 block h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
          >
            {cameraOptions.length === 0 && <option value="">NO CAMERAS</option>}
            {cameraOptions.map((camera) => (
              <option key={camera.id} value={camera.id}>
                {camera.id}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex items-center gap-2 border-t border-[#2A3441] px-4 py-3 text-[10px] text-green-300">
        <CheckCircle2 size={13} aria-hidden="true" />
        SYSTEM STATUS //{" "}
        {healthQuery.isSuccess
          ? "OPERATIONAL"
          : healthQuery.isError
            ? "BACKEND UNAVAILABLE"
            : "CHECKING"}
        <span className="ml-auto text-[#8B949E]">ENV: LOCAL</span>
      </div>
    </section>
  );
}

export default SettingsPanel;

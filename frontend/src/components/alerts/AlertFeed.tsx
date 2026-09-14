import { AlertTriangle, CircleAlert, ShieldAlert } from "lucide-react";
import { alertToRecord } from "../../api/adapters";
import { useAlerts } from "../../api/hooks";
import type { AlertRecord } from "../../data/mockData";

const severityColor = {
  LOW: "text-green-300 border-green-500/40",
  MEDIUM: "text-yellow-300 border-yellow-500/40",
  HIGH: "text-orange-400 border-orange-500/40",
  CRITICAL: "text-red-400 border-red-500/40",
} as const;

function AlertFeed() {
  const alertsQuery = useAlerts();
  const alerts: AlertRecord[] =
    alertsQuery.data
      ?.map(alertToRecord)
      .filter((alert) => alert.status === "ACTIVE") ?? [];

  return (
    <section className="overflow-hidden rounded-lg border border-[#2A3441] bg-[#141A23]">
      <div className="flex h-11 items-center justify-between border-b border-[#2A3441] px-4">
        <div className="flex items-center gap-2">
          <ShieldAlert size={15} className="text-red-400" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em] text-[#E6EDF3]">
            ACTIVE ALERTS
          </h2>
        </div>
        <span className="text-[10px] text-[#8B949E]">{alerts.length} DETECTED</span>
      </div>
      <div className="divide-y divide-[#2A3441]">
        {alerts.length === 0 && (
          <p className="p-4 text-xs text-[#8B949E]">NO CURRENT ALERTS</p>
        )}
        {alerts.map((alert) => (
          <article key={alert.id} className="p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <CircleAlert
                  size={15}
                  className={severityColor[alert.risk].split(" ")[0]}
                  aria-hidden="true"
                />
                <div>
                  <p className="text-xs font-bold tracking-wider text-[#E6EDF3]">
                    {alert.objectType} INTRUSION
                  </p>
                  <p className="mt-1 text-[10px] text-[#8B949E]">{alert.id}</p>
                </div>
              </div>
              <span className={`border px-1.5 py-1 text-[9px] font-bold tracking-wider ${severityColor[alert.risk]}`}>
                {alert.risk}
              </span>
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-2 border-y border-[#2A3441] py-3 text-[10px]">
              <div><dt className="text-[#8B949E]">CAMERA</dt><dd className="mt-0.5 text-[#E6EDF3]">{alert.cameraId}</dd></div>
              <div><dt className="text-[#8B949E]">SECTOR</dt><dd className="mt-0.5 text-[#E6EDF3]">{alert.sector}</dd></div>
              <div><dt className="text-[#8B949E]">TRACK ID</dt><dd className="mt-0.5 font-mono text-[#E6EDF3]">{alert.trackId}</dd></div>
              <div><dt className="text-[#8B949E]">OBJECT</dt><dd className="mt-0.5 text-[#E6EDF3]">{alert.objectType}</dd></div>
              <div><dt className="text-[#8B949E]">AI CONFIDENCE</dt><dd className="mt-0.5 font-semibold text-cyan-300">{alert.confidence}%</dd></div>
            </dl>
            <div className="mt-3 flex gap-2 text-[10px] leading-relaxed text-[#8B949E]">
              <AlertTriangle size={13} className="mt-0.5 shrink-0 text-orange-300" aria-hidden="true" />
              <p>{alert.description}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default AlertFeed;

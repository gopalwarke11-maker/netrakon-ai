import { Camera, Radio } from "lucide-react";

interface CameraTileProps {
  cameraId: string;
  sector: string;
}

function CameraTile({ cameraId, sector }: CameraTileProps) {
  return (
    <article className="overflow-hidden rounded-lg border border-[#2A3441] bg-[#141A23]">
      <div className="flex h-10 items-center justify-between border-b border-[#2A3441] px-3">
        <div className="flex items-center gap-2">
          <Camera size={14} className="text-[#3B82F6]" aria-hidden="true" />
          <span className="text-xs font-semibold text-[#E6EDF3]">{sector}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[9px] font-bold tracking-wider text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          LIVE
        </div>
      </div>

      <div className="relative aspect-video overflow-hidden bg-[#080B10]">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "linear-gradient(#2A3441 1px, transparent 1px), linear-gradient(90deg, #2A3441 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-[#8B949E]">
          <Camera size={28} strokeWidth={1.25} aria-hidden="true" />
          <span className="text-[10px] tracking-[0.2em]">
            CCTV SIGNAL READY
          </span>
        </div>
        <div className="absolute bottom-2 left-2 bg-black/70 px-2 py-1 font-mono text-[10px] text-[#E6EDF3]">
          {cameraId}
        </div>
        <div className="absolute right-2 top-2 flex items-center gap-1 rounded bg-black/70 px-2 py-1 text-[9px] font-semibold text-cyan-300">
          <Radio size={11} aria-hidden="true" />
          AI MONITORING
        </div>
      </div>
    </article>
  );
}

export default CameraTile;

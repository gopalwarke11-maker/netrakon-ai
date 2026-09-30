import React from "react";
import { Shield, Radio, BarChart3, Lock, Cpu } from "lucide-react";
import LoginForm from "../components/auth/LoginForm";
import AuthPageLayout from "../components/auth/AuthPageLayout";

interface LoginPageProps {
  onNavigate: (path: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  return (
    <AuthPageLayout>
      {/* Main Content Grid */}
      <div className="grid w-full max-w-6xl grid-cols-1 gap-8 p-4 lg:grid-cols-12 lg:p-8">
        
        {/* Left Atmosphere & Branding Column (Desktop) */}
        <div className="hidden flex-col justify-between space-y-8 rounded-2xl border border-[#2A3441]/60 bg-[#111923]/60 p-8 backdrop-blur-md lg:col-span-6 lg:flex">
          {/* Header Branding */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#3B82F6]/50 bg-[#3B82F6]/10 text-[#3B82F6] shadow-lg shadow-blue-500/20">
                <Shield size={24} aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-[0.2em] text-white">
                  NETRAKON AI
                </h1>
                <p className="text-[10px] font-semibold tracking-[0.25em] text-[#06B6D4]">
                  BORDER INTELLIGENCE SYSTEM
                </p>
              </div>
            </div>

            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium text-cyan-300">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500"></span>
              </span>
              AI POWERED BORDER SURVEILLANCE
            </div>
          </div>

          {/* Core Feature Highlights */}
          <div className="space-y-4">
            <h2 className="text-xs font-bold tracking-widest text-[#8B949E] uppercase">
              SECURITY CONTROL CORE
            </h2>

            <div className="space-y-3">
              <div className="flex items-start gap-3.5 rounded-xl border border-[#2A3441]/50 bg-[#141A23]/70 p-3.5 transition duration-200 hover:border-[#3B82F6]/40">
                <div className="mt-0.5 rounded-lg border border-blue-500/30 bg-blue-500/10 p-2 text-blue-400">
                  <Radio size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#E6EDF3]">Real-time Monitoring</h3>
                  <p className="mt-0.5 text-xs text-[#8B949E]">
                    Low-latency video stream ingestion with automatic failover telemetry.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 rounded-xl border border-[#2A3441]/50 bg-[#141A23]/70 p-3.5 transition duration-200 hover:border-[#3B82F6]/40">
                <div className="mt-0.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-2 text-cyan-400">
                  <Cpu size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#E6EDF3]">AI Powered Intrusion Detection</h3>
                  <p className="mt-0.5 text-xs text-[#8B949E]">
                    YOLOv8 & ByteTrack precision border cross classification and target tracking.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 rounded-xl border border-[#2A3441]/50 bg-[#141A23]/70 p-3.5 transition duration-200 hover:border-[#3B82F6]/40">
                <div className="mt-0.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-2 text-indigo-400">
                  <BarChart3 size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#E6EDF3]">Smart Alerts & Analytics</h3>
                  <p className="mt-0.5 text-xs text-[#8B949E]">
                    Instant threat escalation, sector risk mapping, and situational reports.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Sub Footer Status */}
          <div className="flex items-center justify-between border-t border-[#2A3441]/60 pt-4 font-mono text-[10px] text-[#8B949E]">
            <div className="flex items-center gap-2">
              <Lock size={12} className="text-cyan-400" />
              <span>CONTROL ROOM NODE 01 // ENCRYPTED</span>
            </div>
            <span>V2.4-STABLE</span>
          </div>
        </div>

        {/* Right / Center Glass Login Card Column */}
        <div className="flex items-center justify-center lg:col-span-6">
          <div className="w-full max-w-md rounded-2xl border border-[#2A3441] bg-[#141A23]/80 p-6 sm:p-8 shadow-2xl shadow-black/80 backdrop-blur-xl">
            {/* Mobile Branding (Visible only on mobile/tablet) */}
            <div className="mb-6 flex items-center justify-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#3B82F6]/50 bg-[#3B82F6]/10 text-[#3B82F6]">
                <Shield size={22} aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-[0.18em] text-white">
                  NETRAKON AI
                </h1>
                <p className="text-[9px] font-semibold tracking-[0.2em] text-[#06B6D4]">
                  BORDER INTELLIGENCE SYSTEM
                </p>
              </div>
            </div>

            {/* Login Title Header */}
            <div className="mb-6 space-y-1.5 text-left">
              <h2 className="text-xl font-bold tracking-wide text-white sm:text-2xl">
                Admin Login
              </h2>
              <p className="text-xs text-[#8B949E]">
                Access the NetraKon AI control center
              </p>
            </div>

            {/* Form */}
            <LoginForm onNavigate={onNavigate} />

            {/* Footer Notice */}
            <div className="mt-8 border-t border-[#2A3441]/60 pt-4 text-center">
              <p className="text-[10px] leading-relaxed text-[#8B949E]">
                Restricted access. All login actions are recorded and audited under national defense data protocol.
              </p>
            </div>
          </div>
        </div>

      </div>
    </AuthPageLayout>
  );
};

export default LoginPage;

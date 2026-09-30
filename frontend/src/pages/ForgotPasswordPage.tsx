import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, Mail, Shield } from "lucide-react";
import AuthInput from "../components/auth/AuthInput";
import AuthButton from "../components/auth/AuthButton";
import AuthPageLayout from "../components/auth/AuthPageLayout";

interface ForgotPasswordPageProps {
  onNavigate: (path: string) => void;
}

export const ForgotPasswordPage: React.FC<ForgotPasswordPageProps> = ({ onNavigate }) => {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || isLoading) return;

    setIsLoading(true);

    // Stage 1 Mock simulation only
    setTimeout(() => {
      setIsLoading(false);
      setIsSubmitted(true);
    }, 900);
  };

  return (
    <AuthPageLayout>
      {/* Main Glass Card */}
      <div className="w-full max-w-md rounded-2xl border border-[#2A3441] bg-[#141A23]/80 p-6 sm:p-8 shadow-2xl shadow-black/80 backdrop-blur-xl">
        {/* NetraKon AI Branding */}
        <div className="mb-6 flex items-center gap-3">
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

        {/* Header */}
        <div className="mb-6 space-y-1 text-left">
          <h2 className="text-xl font-bold tracking-wide text-white sm:text-2xl">
            Reset Password Request
          </h2>
          <p className="text-xs text-[#8B949E]">
            Enter your registered email to request password assistance.
          </p>
        </div>

        {!isSubmitted ? (
          <form onSubmit={handleSubmit} className="space-y-5">
            <AuthInput
              id="reset-email"
              type="email"
              label="Registered Email Address"
              placeholder="admin@netrakon.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={Mail}
              autoComplete="email"
              required
              disabled={isLoading}
            />

            <AuthButton isLoading={isLoading} type="submit">
              SEND REQUEST
            </AuthButton>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col items-center justify-center rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-5 text-center">
              <CheckCircle2 size={36} className="mb-3 text-emerald-400" />
              <p className="text-sm font-semibold text-emerald-200">
                Request Dispatched
              </p>
              <p className="mt-2 text-xs leading-relaxed text-[#E6EDF3]">
                Your password reset request has been sent to the Main Administrator.
              </p>
            </div>
          </div>
        )}

        {/* Back to Login Action */}
        <div className="mt-6 border-t border-[#2A3441]/60 pt-4 text-center">
          <button
            type="button"
            onClick={() => onNavigate("/login")}
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#8B949E] transition hover:text-[#3B82F6] focus:outline-none focus:underline"
          >
            <ArrowLeft size={14} />
            Back to Login
          </button>
        </div>
      </div>
    </AuthPageLayout>
  );
};

export default ForgotPasswordPage;

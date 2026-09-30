import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, KeyRound, Shield } from "lucide-react";
import PasswordInput from "../components/auth/PasswordInput";
import AuthButton from "../components/auth/AuthButton";
import AuthPageLayout from "../components/auth/AuthPageLayout";
import { apiFetch, ApiError } from "../api/client";

interface ResetPasswordPageProps {
  onNavigate: (path: string) => void;
}

export const ResetPasswordPage: React.FC<ResetPasswordPageProps> = ({ onNavigate }) => {
  const [token] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      return params.get("token") || "";
    }
    return "";
  });

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    if (!token) {
      setErrorMessage("Invalid or missing password reset token. Please request a new reset link.");
      return;
    }

    if (newPassword.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await apiFetch<{ message: string }>("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });
      setIsSuccess(true);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to reset password. The link may be expired or invalid.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthPageLayout>
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
            Set New Password
          </h2>
          <p className="text-xs text-[#8B949E]">
            Create a new secure password for your administrator account.
          </p>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="mb-5 rounded-md border border-red-500/50 bg-red-500/10 p-3.5 text-xs text-red-300">
            {errorMessage}
          </div>
        )}

        {!isSuccess ? (
          <form onSubmit={handleSubmit} className="space-y-5">
            <PasswordInput
              id="new-password"
              label="New Password"
              placeholder="••••••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              disabled={isLoading}
            />

            <PasswordInput
              id="confirm-password"
              label="Confirm New Password"
              placeholder="••••••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isLoading}
            />

            <AuthButton isLoading={isLoading} type="submit">
              <span className="flex items-center justify-center gap-2">
                <KeyRound size={16} />
                UPDATE PASSWORD
              </span>
            </AuthButton>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col items-center justify-center rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-5 text-center">
              <CheckCircle2 size={36} className="mb-3 text-emerald-400" />
              <p className="text-sm font-semibold text-emerald-200">
                Password Reset Complete
              </p>
              <p className="mt-2 text-xs leading-relaxed text-[#E6EDF3]">
                Your administrator password has been updated successfully. You may now log in with your new credentials.
              </p>
            </div>
          </div>
        )}

        {/* Back to Login */}
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

export default ResetPasswordPage;

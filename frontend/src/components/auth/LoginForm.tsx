import React, { useState } from "react";
import { AlertCircle, ArrowRight, Mail, ShieldAlert, CheckCircle2 } from "lucide-react";
import AuthInput from "./AuthInput";
import PasswordInput from "./PasswordInput";
import AuthButton from "./AuthButton";
import { useAuthStore } from "../../state/authStore";

interface LoginFormProps {
  onNavigate: (path: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onNavigate }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { login: authLogin, isLoading } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading || !email || !password) return;

    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const user = await authLogin(email, password, rememberMe);
      setSuccessMessage("Authentication successful. Redirecting to NetraKon AI...");
      
      setTimeout(() => {
        if (user.role === "MAIN_ADMIN") {
          onNavigate("/admin-control");
        } else {
          onNavigate("/dashboard");
        }
      }, 800);
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid email or password");
    }
  };

  const isAccountDisabled = errorMessage?.toLowerCase().includes("disabled");

  return (
    <div className="space-y-6">
      {/* Error Banners */}
      {errorMessage && (
        <div
          className={`flex items-start gap-3 rounded-md border p-3.5 text-xs leading-relaxed ${
            isAccountDisabled
              ? "border-amber-500/50 bg-amber-500/10 text-amber-300"
              : "border-red-500/50 bg-red-500/10 text-red-300"
          }`}
          role="alert"
        >
          {isAccountDisabled ? (
            <ShieldAlert size={18} className="mt-0.5 shrink-0 text-amber-400" />
          ) : (
            <AlertCircle size={18} className="mt-0.5 shrink-0 text-red-400" />
          )}
          <div>
            <p className="font-semibold">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Success Banner */}
      {successMessage && (
        <div
          className="flex items-center gap-3 rounded-md border border-emerald-500/50 bg-emerald-500/10 p-3.5 text-xs text-emerald-300"
          role="status"
        >
          <CheckCircle2 size={18} className="shrink-0 text-emerald-400" />
          <p className="font-semibold">{successMessage}</p>
        </div>
      )}

      {/* Login Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <AuthInput
          id="admin-email"
          type="email"
          label="Email Address"
          placeholder="admin@netrakon.ai"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          icon={Mail}
          autoComplete="email"
          required
          disabled={isLoading}
        />

        <PasswordInput
          id="admin-password"
          label="Password"
          placeholder="••••••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={isLoading}
        />

        <div className="flex items-center justify-between text-xs">
          <label className="flex items-center gap-2 cursor-pointer text-[#8B949E] select-none hover:text-[#E6EDF3]">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={isLoading}
              className="size-4 rounded border-[#2A3441] bg-[#0A0E14] text-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] accent-[#3B82F6]"
            />
            <span>Remember me</span>
          </label>

          <button
            type="button"
            onClick={() => onNavigate("/forgot-password")}
            disabled={isLoading}
            className="font-medium text-[#3B82F6] hover:text-cyan-400 focus:outline-none focus:underline transition-colors"
          >
            Forgot Password?
          </button>
        </div>

        <AuthButton isLoading={isLoading} type="submit">
          <span className="flex items-center gap-2">
            LOG IN TO CONTROL CENTER
            <ArrowRight size={16} />
          </span>
        </AuthButton>
      </form>
    </div>
  );
};

export default LoginForm;

import React, { useState } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label?: string;
  error?: string;
}

export const PasswordInput: React.FC<PasswordInputProps> = ({
  id,
  label = "PASSWORD",
  error,
  className = "",
  disabled,
  ...props
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="space-y-1.5 text-left">
      <label
        htmlFor={id}
        className="block text-xs font-semibold tracking-wider text-[#8B949E] uppercase"
      >
        {label}
      </label>
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-[#8B949E]">
          <Lock size={16} />
        </div>
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          disabled={disabled}
          className={`w-full rounded-md border border-[#2A3441] bg-[#0A0E14]/90 py-2.5 pl-10 pr-10 text-sm text-[#E6EDF3] placeholder-[#484F58] transition duration-150 focus:border-[#3B82F6] focus:bg-[#141A23] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] disabled:cursor-not-allowed disabled:opacity-50 ${
            error ? "border-red-500/80 focus:border-red-500 focus:ring-red-500/50" : ""
          } ${className}`}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          disabled={disabled}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#8B949E] transition-colors hover:text-[#E6EDF3] focus:outline-none"
          aria-label={showPassword ? "Hide password" : "Show password"}
          tabIndex={0}
        >
          {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {error && (
        <p className="mt-1 text-xs text-red-400" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default PasswordInput;

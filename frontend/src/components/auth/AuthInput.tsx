import React, { type ComponentType } from "react";

interface AuthInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  icon?: ComponentType<{ size?: number; className?: string }>;
  error?: string;
}

export const AuthInput: React.FC<AuthInputProps> = ({
  id,
  label,
  icon: Icon,
  error,
  className = "",
  disabled,
  ...props
}) => {
  return (
    <div className="space-y-1.5 text-left">
      <label
        htmlFor={id}
        className="block text-xs font-semibold tracking-wider text-[#8B949E] uppercase"
      >
        {label}
      </label>
      <div className="relative">
        {Icon && (
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-[#8B949E]">
            <Icon size={16} />
          </div>
        )}
        <input
          id={id}
          disabled={disabled}
          className={`w-full rounded-md border border-[#2A3441] bg-[#0A0E14]/90 py-2.5 text-sm text-[#E6EDF3] placeholder-[#484F58] transition duration-150 focus:border-[#3B82F6] focus:bg-[#141A23] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] disabled:cursor-not-allowed disabled:opacity-50 ${
            Icon ? "pl-10" : "pl-3.5"
          } pr-3.5 ${error ? "border-red-500/80 focus:border-red-500 focus:ring-red-500/50" : ""} ${className}`}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1 text-xs text-red-400" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default AuthInput;

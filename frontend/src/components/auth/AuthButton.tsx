import React from "react";
import { LoaderCircle } from "lucide-react";

interface AuthButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  children: React.ReactNode;
}

export const AuthButton: React.FC<AuthButtonProps> = ({
  isLoading = false,
  children,
  className = "",
  disabled,
  type = "submit",
  ...props
}) => {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={`group relative flex w-full items-center justify-center rounded-md border border-[#3B82F6]/60 bg-gradient-to-r from-[#2563EB] to-[#0284C7] px-4 py-2.5 text-sm font-semibold tracking-wider text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:border-cyan-400 hover:from-[#1D4ED8] hover:to-[#0369A1] hover:shadow-cyan-500/25 focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:ring-offset-2 focus:ring-offset-[#0A0E14] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...props}
    >
      {isLoading ? (
        <div className="flex items-center justify-center gap-2">
          <LoaderCircle size={18} className="animate-spin text-white" aria-hidden="true" />
          <span>AUTHENTICATING...</span>
        </div>
      ) : (
        children
      )}
    </button>
  );
};

export default AuthButton;

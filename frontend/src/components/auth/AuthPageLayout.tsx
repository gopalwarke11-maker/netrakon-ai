import React from "react";

interface AuthPageLayoutProps {
  children: React.ReactNode;
}

export const AuthPageLayout: React.FC<AuthPageLayoutProps> = ({ children }) => {
  return (
    <div
      className="relative flex min-h-screen w-full items-center justify-center bg-[#0A0E14] text-[#E6EDF3] overflow-hidden bg-cover bg-center bg-no-repeat p-4"
      style={{ backgroundImage: "url('/assets/netrakon-login-bg.png')" }}
    >
      {/* Subtle Navy/Black Darkening Overlay for Form Readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-[#0A0E14]/90 via-[#0A0E14]/75 to-[#0A0E14]/85 backdrop-blur-[1px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#1E293B_1px,transparent_1px)] [background-size:24px_24px] opacity-15" />
      <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-cyan-500/10 blur-[120px]" />

      {/* Main Content Container */}
      <div className="relative z-10 flex w-full items-center justify-center">
        {children}
      </div>
    </div>
  );
};

export default AuthPageLayout;

import SettingsPanel from "../components/settings/SettingsPanel";

function Settings() {
  return (
    <PageSection
      title="SETTINGS"
      subtitle="LOCAL UI PREFERENCES // BACKEND HEALTH AWARE"
    >
      <SettingsPanel />
    </PageSection>
  );
}
function PageSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-[900px] space-y-4 p-4 sm:p-6">
      <header className="border-b border-[#2A3441] pb-4">
        <h1 className="text-lg font-semibold tracking-[0.12em]">{title}</h1>
        <p className="mt-1 text-[10px] tracking-wider text-[#8B949E]">
          {subtitle}
        </p>
      </header>
      {children}
    </div>
  );
}
export default Settings;

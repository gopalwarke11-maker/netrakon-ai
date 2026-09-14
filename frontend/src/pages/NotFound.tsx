import { AlertOctagon } from "lucide-react";

function NotFound({ onReturn }: { onReturn: () => void }) {
  return (
    <div className="grid min-h-[calc(100vh-64px)] place-items-center p-6">
      <div className="text-center">
        <AlertOctagon
          size={34}
          className="mx-auto text-orange-300"
          aria-hidden="true"
        />
        <p className="mt-5 text-5xl font-bold tracking-widest text-[#E6EDF3]">
          404
        </p>
        <h1 className="mt-3 text-sm font-semibold tracking-[0.2em]">
          PAGE NOT FOUND
        </h1>
        <button
          type="button"
          onClick={onReturn}
          className="mt-7 border border-[#3B82F6] px-4 py-2 text-[10px] font-bold tracking-wider text-[#3B82F6] hover:bg-[#3B82F6]/10"
        >
          RETURN TO COMMAND CENTER
        </button>
      </div>
    </div>
  );
}
export default NotFound;

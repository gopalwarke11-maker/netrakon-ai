import { useEffect, useMemo, useState } from "react";
import {
  Camera,
  CheckCircle2,
  CircleDot,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCameraStore } from "../../state/cameraStore";
import { cameraToRecord } from "../../api/adapters";
import {
  createCamera,
  deleteCamera,
  startCamera,
  stopCamera,
  updateCamera,
} from "../../api/cameras";
import { useCameras } from "../../api/hooks";
import type { ApiCameraStatus } from "../../types/api";

const emptyForm = {
  name: "",
  sector: "",
  location: "",
  status: "ONLINE" as ApiCameraStatus,
  stream_url: "",
  source_type: "FILE" as "FILE" | "RTSP" | "MJPEG" | "DEVICE",
};

function CameraManager() {
  const queryClient = useQueryClient();
  const selectedCamera = useCameraStore((state) => state.selectedCamera);
  const setSelectedCamera = useCameraStore((state) => state.setSelectedCamera);
  const camerasQuery = useCameras();
  const cameras = useMemo(
    () => camerasQuery.data?.map(cameraToRecord) ?? [],
    [camerasQuery.data],
  );
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedCamera && cameras[0]) {
      setSelectedCamera(cameras[0].cameraId);
    }
    if (
      selectedCamera &&
      !cameras.some((camera) => camera.cameraId === selectedCamera)
    ) {
      setSelectedCamera(cameras[0]?.cameraId ?? "");
    }
  }, [cameras, selectedCamera, setSelectedCamera]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setSubmitError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    const payload = {
      name: form.name.trim(),
      sector: form.sector.trim(),
      location: form.location.trim(),
      status: form.status,
      source_type: form.source_type,
      stream_url: form.stream_url.trim() || null,
    };

    if (!payload.name || !payload.sector || !payload.location) {
      setSubmitError("Name, sector, and location are required.");
      return;
    }

    try {
      if (editingId) {
        await updateCamera(editingId, payload);
      } else {
        await createCamera(payload);
      }
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      resetForm();
      await camerasQuery.refetch();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Camera update failed.";
      setSubmitError(message);
    }
  };

  const handleEdit = (cameraId: string) => {
    const camera = camerasQuery.data?.find((item) => item.id === cameraId);
    if (!camera) return;
    setEditingId(cameraId);
    setForm({
      name: camera.name,
      sector: camera.sector,
      location: camera.location,
      status: camera.status,
      source_type: camera.source_type,
      stream_url: camera.stream_url ?? "",
    });
    setSelectedCamera(cameraId);
  };

  const handleDelete = async (cameraId: string) => {
    try {
      await deleteCamera(cameraId);
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      if (selectedCamera === cameraId) {
        setSelectedCamera(
          cameras.find((camera) => camera.cameraId !== cameraId)?.cameraId ??
            "",
        );
      }
      if (editingId === cameraId) {
        resetForm();
      }
      await camerasQuery.refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Delete failed.");
    }
  };

  const handleLifecycleToggle = async (
    cameraId: string,
    action: "start" | "stop",
  ) => {
    try {
      if (action === "start") {
        const camera = cameras.find((item) => item.cameraId === cameraId);
        await startCamera(cameraId, camera?.sourceType === "FILE");
      } else {
        await stopCamera(cameraId);
      }
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      await queryClient.invalidateQueries({
        queryKey: ["cameras", cameraId, "processing"],
      });
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Lifecycle action failed.",
      );
    }
  };

  return (
    <section className="border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between gap-3 border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <Camera size={15} className="text-[#3B82F6]" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">
            CAMERA MANAGEMENT
          </h2>
        </div>
        <button
          type="button"
          onClick={() => void camerasQuery.refetch()}
          className="inline-flex items-center gap-2 border border-[#2A3441] px-2 py-1 text-[9px] font-bold text-[#E6EDF3]"
        >
          <RefreshCw size={11} aria-hidden="true" /> REFRESH
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        className="grid gap-3 border-b border-[#2A3441] p-4 lg:grid-cols-5"
      >
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          NAME
          <input
            value={form.name}
            onChange={(event) =>
              setForm((current) => ({ ...current, name: event.target.value }))
            }
            className="mt-2 h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
            placeholder="North Gate"
          />
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          SECTOR
          <input
            value={form.sector}
            onChange={(event) =>
              setForm((current) => ({ ...current, sector: event.target.value }))
            }
            className="mt-2 h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
            placeholder="North Zone"
          />
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          LOCATION
          <input
            value={form.location}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                location: event.target.value,
              }))
            }
            className="mt-2 h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
            placeholder="Gate 03"
          />
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          STATUS
          <select
            value={form.status}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                status: event.target.value as ApiCameraStatus,
              }))
            }
            className="mt-2 block h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
          >
            <option value="ONLINE">ONLINE</option>
            <option value="OFFLINE">OFFLINE</option>
            <option value="MAINTENANCE">MAINTENANCE</option>
          </select>
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          SOURCE TYPE
          <select
            value={form.source_type}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                source_type: event.target.value as typeof current.source_type,
              }))
            }
            className="mt-2 block h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
          >
            <option value="FILE">FILE</option>
            <option value="MJPEG">IP CAMERA / MJPEG</option>
            <option value="RTSP">RTSP</option>
            <option value="DEVICE">DEVICE</option>
          </select>
        </label>
        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-1">
          STREAM URL
          <input
            value={form.stream_url}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                stream_url: event.target.value,
              }))
            }
            className="mt-2 h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
            placeholder={form.source_type === "FILE" ? "D:\\camera.mp4" : "http://192.168.x.x:8080/video"}
          />
        </label>
        <div className="flex items-end gap-2 lg:col-span-5">
          <button
            type="submit"
            className="inline-flex items-center gap-2 bg-[#3B82F6] px-3 py-2 text-[10px] font-bold text-white"
          >
            {editingId ? (
              <Pencil size={12} aria-hidden="true" />
            ) : (
              <Plus size={12} aria-hidden="true" />
            )}
            {editingId ? "UPDATE CAMERA" : "ADD CAMERA"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="border border-[#2A3441] px-3 py-2 text-[10px] font-bold text-[#E6EDF3]"
            >
              CANCEL
            </button>
          )}
          {submitError && (
            <span className="text-[10px] text-orange-300">{submitError}</span>
          )}
        </div>
      </form>

      <div className="divide-y divide-[#2A3441]">
        {cameras.length === 0 ? (
          <div className="p-4 text-[10px] text-[#8B949E]">
            NO CAMERAS AVAILABLE FROM THE BACKEND.
          </div>
        ) : (
          cameras.map((camera) => (
            <div
              key={camera.cameraId}
              className={`p-3 ${camera.cameraId === selectedCamera ? "bg-[#0A0E14]" : ""}`}
            >
              <div className="flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedCamera(camera.cameraId)}
                  className="flex min-w-0 items-center gap-3 text-left"
                >
                  <span
                    className={`grid size-7 shrink-0 place-items-center border ${camera.cameraId === selectedCamera ? "border-[#3B82F6] text-[#3B82F6]" : "border-[#2A3441] text-[#8B949E]"}`}
                  >
                    <Camera size={13} aria-hidden="true" />
                  </span>
                  <span>
                    <span className="block text-xs font-bold">
                      {camera.cameraId}
                    </span>
                    <span className="mt-1 block text-[10px] text-[#8B949E]">
                      {camera.sector}
                    </span>
                  </span>
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleLifecycleToggle(
                        camera.cameraId,
                        camera.status === "ONLINE" ? "stop" : "start",
                      )
                    }
                    className={`flex items-center gap-1.5 text-[9px] font-bold ${camera.status === "ONLINE" ? "text-green-300" : "text-[#8B949E]"}`}
                  >
                    <CheckCircle2 size={12} aria-hidden="true" />
                    {camera.status === "ONLINE" ? "STOP" : "START"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEdit(camera.cameraId)}
                    className="text-[9px] font-bold text-[#8B949E]"
                  >
                    EDIT
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(camera.cameraId)}
                    className="flex items-center gap-1 text-[9px] font-bold text-red-300"
                  >
                    <Trash2 size={11} aria-hidden="true" /> DELETE
                  </button>
                </div>
              </div>
              <div className="mt-3 grid gap-2 pl-10 text-[9px] text-[#8B949E] sm:grid-cols-3">
                <span>
                  STATUS:{" "}
                  <span className="text-[#E6EDF3]">{camera.status}</span>
                </span>
                <span>
                  TYPE:{" "}
                  <span className="text-[#E6EDF3]">{camera.sourceType}</span>
                </span>
                <span>
                  STREAM:{" "}
                  <span className="text-[#E6EDF3]">
                    {camera.streamUrl ? "CONFIGURED" : "NOT CONFIGURED"}
                  </span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="flex items-center gap-2 border-t border-[#2A3441] px-4 py-3 text-[10px] text-[#8B949E]">
        <CircleDot size={13} className="text-[#3B82F6]" aria-hidden="true" />
        Runtime lifecycle actions call the existing backend
        /api/cameras/:id/start and /stop endpoints.
      </div>
    </section>
  );
}

export default CameraManager;

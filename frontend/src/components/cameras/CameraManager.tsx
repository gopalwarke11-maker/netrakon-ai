import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  CircleDot,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  Wifi,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCameraStore } from "../../state/cameraStore";
import { cameraToRecord } from "../../api/adapters";
import {
  confirmUpload,
  createCamera,
  deleteCamera,
  getPresignedUploadUrl,
  startCamera,
  stopCamera,
  testCameraConnection,
  updateCamera,
  uploadFileToPresignedUrl,
} from "../../api/cameras";
import { useCameras } from "../../api/hooks";
import type {
  ApiCameraStatus,
  ApiCameraTestResponse,
} from "../../types/api";

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

  // Connection Test state
  const [testResult, setTestResult] = useState<ApiCameraTestResponse | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // S3 Direct Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
    setTestResult(null);
    setSelectedFile(null);
    setUploadProgress(null);
  };

  const handleTestConnection = async () => {
    if (!form.stream_url && form.source_type !== "DEVICE") {
      setTestResult({
        is_reachable: false,
        status: "INVALID_URL",
        message: "Please enter a stream URL before testing connection.",
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testCameraConnection({
        source_type: form.source_type,
        stream_url: form.stream_url || "0",
      });
      setTestResult(res);
    } catch (error) {
      setTestResult({
        is_reachable: false,
        status: "UNREACHABLE",
        message: error instanceof Error ? error.message : "Connection test failed.",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleFileUploadAndRegister = async () => {
    if (!selectedFile) {
      setSubmitError("Please select an MP4 video file first.");
      return;
    }
    const name = form.name.trim() || selectedFile.name;
    const sector = form.sector.trim() || "Default Sector";
    const location = form.location.trim() || "Uploaded Video";

    setIsUploading(true);
    setSubmitError(null);
    setUploadProgress("Requesting S3 presigned upload URL...");

    try {
      const presigned = await getPresignedUploadUrl({
        filename: selectedFile.name,
        content_type: selectedFile.type || "video/mp4",
        camera_id: editingId || undefined,
      });

      setUploadProgress(
        `Uploading MP4 directly to ${presigned.storage_type === "S3" ? "S3 Object Storage" : "Storage"}...`,
      );
      await uploadFileToPresignedUrl(presigned.upload_url, selectedFile, presigned.headers);

      setUploadProgress("Confirming upload with backend...");
      await confirmUpload({
        object_key: presigned.object_key,
        camera_id: editingId || undefined,
        name,
        sector,
        location,
        file_size_bytes: selectedFile.size,
      });

      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      resetForm();
      await camerasQuery.refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Direct S3 upload failed.");
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
    }
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
    setTestResult(null);
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
            CAMERA MANAGEMENT & OBJECT STORAGE
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
            <option value="FILE">FILE / S3 OBJECT</option>
            <option value="MJPEG">IP CAMERA / MJPEG</option>
            <option value="RTSP">RTSP STREAM</option>
            <option value="DEVICE">OPENCV DEVICE</option>
          </select>
        </label>

        <label className="text-[9px] font-bold tracking-wider text-[#8B949E] lg:col-span-3">
          STREAM URL / REMOTE PATH
          <input
            value={form.stream_url}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                stream_url: event.target.value,
              }))
            }
            className="mt-2 h-8 w-full border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3]"
            placeholder={
              form.source_type === "FILE"
                ? "https://s3.amazonaws.com/bucket/video.mp4 or videos/sample.mp4"
                : "http://192.168.x.x:8080/video or rtsp://..."
            }
          />
        </label>

        {/* S3 Direct Video Upload Option */}
        <div className="flex flex-col justify-end text-[9px] font-bold text-[#8B949E] lg:col-span-2">
          <span>OR DIRECT MP4 S3 UPLOAD</span>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="file"
              accept="video/mp4,video/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              className="h-8 text-[10px] text-[#8B949E] file:mr-2 file:h-full file:border-0 file:bg-[#2A3441] file:px-2 file:text-[10px] file:text-white"
            />
            {selectedFile && (
              <button
                type="button"
                onClick={handleFileUploadAndRegister}
                disabled={isUploading}
                className="inline-flex items-center gap-1.5 bg-emerald-600 px-3 py-2 text-[10px] font-bold text-white disabled:opacity-50"
              >
                <Upload size={12} />
                {isUploading ? "UPLOADING..." : "UPLOAD TO S3"}
              </button>
            )}
          </div>
        </div>

        {uploadProgress && (
          <div className="text-[10px] text-emerald-400 lg:col-span-5">
            {uploadProgress}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 lg:col-span-5">
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

          <button
            type="button"
            onClick={handleTestConnection}
            disabled={isTesting}
            className="inline-flex items-center gap-1.5 border border-[#3B82F6] px-3 py-2 text-[10px] font-bold text-[#3B82F6] hover:bg-[#3B82F6]/10"
          >
            <Wifi size={12} />
            {isTesting ? "TESTING..." : "TEST CONNECTION"}
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

        {testResult && (
          <div
            className={`mt-2 p-2.5 text-[10px] border lg:col-span-5 ${
              testResult.status === "REACHABLE" || testResult.status === "DEVICE_AVAILABLE"
                ? "border-green-500/40 bg-green-950/20 text-green-300"
                : testResult.status === "PRIVATE_NETWORK_NOT_REACHABLE"
                ? "border-amber-500/40 bg-amber-950/20 text-amber-300"
                : "border-red-500/40 bg-red-950/20 text-red-300"
            }`}
          >
            <div className="flex items-center gap-2 font-bold">
              {testResult.is_reachable ? (
                <CheckCircle2 size={13} className="text-green-400" />
              ) : testResult.status === "PRIVATE_NETWORK_NOT_REACHABLE" ? (
                <AlertTriangle size={13} className="text-amber-400" />
              ) : (
                <AlertTriangle size={13} className="text-red-400" />
              )}
              STATUS: {testResult.status}
            </div>
            <p className="mt-1">{testResult.message}</p>
            {typeof testResult.details?.note === "string" && (
              <p className="mt-1 text-[9px] opacity-80">{testResult.details.note}</p>
            )}
          </div>
        )}
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
                      {camera.cameraId} - {camera.name}
                    </span>
                    <span className="mt-1 block text-[10px] text-[#8B949E]">
                      {camera.sector} | {camera.location}
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
              <div className="mt-3 grid gap-2 pl-10 text-[9px] text-[#8B949E] sm:grid-cols-4">
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
                <span>
                  STORAGE:{" "}
                  <span className="text-[#E6EDF3]">
                    {camera.storageKey ? "S3 / OBJECT KEY" : "LOCAL / DIRECT"}
                  </span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="flex items-center gap-2 border-t border-[#2A3441] px-4 py-3 text-[10px] text-[#8B949E]">
        <CircleDot size={13} className="text-[#3B82F6]" aria-hidden="true" />
        Production uploads upload MP4 files directly from browser to S3 object storage via presigned URLs.
      </div>
    </section>
  );
}

export default CameraManager;

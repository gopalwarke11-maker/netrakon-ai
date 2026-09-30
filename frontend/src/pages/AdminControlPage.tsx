import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Users,
  KeyRound,
  History,
  CheckCircle,
  XCircle,
  AlertTriangle,
  UserCheck,
  UserX,
  Trash2,
  RefreshCw,
  Plus,
  Shield,
  X,
} from "lucide-react";
import { apiFetch } from "../api/client";
import { useAuthStore } from "../state/authStore";

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: "ADMIN" | "MAIN_ADMIN";
  is_active: boolean;
  last_login?: string | null;
}

interface PasswordRequest {
  id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "COMPLETED";
  requested_at: string;
  handled_by?: string | null;
  handled_at?: string | null;
}

interface ActivityLog {
  id: string;
  email_attempted: string;
  login_time: string;
  ip_address?: string | null;
  user_agent?: string | null;
  success: boolean;
  failure_reason?: string | null;
}

interface AdminControlPageProps {
  onNavigate?: (path: string) => void;
  currentSubPath?: string;
}

export const AdminControlPage: React.FC<AdminControlPageProps> = ({
  currentSubPath = "/admin-control",
}) => {
  const { user: currentUser } = useAuthStore();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [resetRequests, setResetRequests] = useState<PasswordRequest[]>([]);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Active tab state
  const [activeTab, setActiveTab] = useState<"users" | "requests" | "activity">(() => {
    if (currentSubPath.includes("password-requests")) return "requests";
    if (currentSubPath.includes("activity")) return "activity";
    return "users";
  });

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showTempPwModal, setShowTempPwModal] = useState<PasswordRequest | null>(null);

  // Form states for Add User
  const [addName, setAddName] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addPassword, setAddPassword] = useState("");
  const [addConfirmPassword, setAddConfirmPassword] = useState("");
  const [addRole, setAddRole] = useState<"ADMIN" | "MAIN_ADMIN">("ADMIN");

  // Form states for Temp Password
  const [tempPassword, setTempPassword] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [uData, rData, aData] = await Promise.all([
        apiFetch<AdminUser[]>("/api/admin/users"),
        apiFetch<PasswordRequest[]>("/api/admin/password-requests"),
        apiFetch<ActivityLog[]>("/api/admin/activity"),
      ]);
      setUsers(uData);
      setResetRequests(rData);
      setActivityLogs(aData);
    } catch (err: any) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const triggerToast = (msg: string) => {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 4000);
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (addPassword !== addConfirmPassword) {
      setError("Passwords do not match");
      return;
    }
    try {
      await apiFetch<AdminUser>("/api/admin/users", {
        method: "POST",
        body: JSON.stringify({
          name: addName,
          email: addEmail,
          password: addPassword,
          role: addRole,
        }),
      });
      setShowAddModal(false);
      setAddName("");
      setAddEmail("");
      setAddPassword("");
      setAddConfirmPassword("");
      triggerToast("New administrator created successfully");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleToggleUserStatus = async (targetUser: AdminUser) => {
    try {
      await apiFetch<AdminUser>(`/api/admin/users/${targetUser.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !targetUser.is_active }),
      });
      triggerToast(
        `Administrator account ${targetUser.is_active ? "disabled" : "enabled"} successfully`,
      );
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (targetUser: AdminUser) => {
    if (!window.confirm(`Are you sure you want to delete admin '${targetUser.name}'?`)) {
      return;
    }
    try {
      await apiFetch<{ message: string }>(`/api/admin/users/${targetUser.id}`, {
        method: "DELETE",
      });
      triggerToast("Administrator deleted successfully");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSetTempPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showTempPwModal) return;
    try {
      await apiFetch<{ message: string }>(
        `/api/admin/password-requests/${showTempPwModal.id}/action`,
        {
          method: "POST",
          body: JSON.stringify({
            action: "approve_temp",
            temp_password: tempPassword,
          }),
        },
      );
      setShowTempPwModal(null);
      setTempPassword("");
      triggerToast("Temporary password updated successfully");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRejectRequest = async (req: PasswordRequest) => {
    try {
      await apiFetch<{ message: string }>(`/api/admin/password-requests/${req.id}/action`, {
        method: "POST",
        body: JSON.stringify({ action: "reject" }),
      });
      triggerToast("Password request rejected");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const totalAdmins = users.length;
  const activeAdmins = users.filter((u) => u.is_active).length;
  const mainAdmins = users.filter((u) => u.role === "MAIN_ADMIN").length;
  const pendingRequests = resetRequests.filter((r) => r.status === "PENDING").length;

  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-4 sm:p-6">
      {/* Page Title Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#2A3441] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Shield className="text-[#3B82F6]" size={22} />
            <h1 className="text-xl font-bold tracking-wider text-white uppercase">
              ADMIN CONTROL CENTER
            </h1>
          </div>
          <p className="mt-1 text-xs text-[#8B949E]">
            Administrator management, password requests, and security audit logs
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchData}
            className="flex items-center gap-2 rounded border border-[#2A3441] bg-[#141A23] px-3 py-2 text-xs font-semibold text-[#E6EDF3] transition hover:bg-[#2A3441]"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            REFRESH
          </button>

          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 rounded border border-blue-500/50 bg-gradient-to-r from-blue-600 to-cyan-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:from-blue-500 hover:to-cyan-500"
          >
            <Plus size={16} />
            ADD ADMINISTRATOR
          </button>
        </div>
      </div>

      {/* Error & Success Toasts */}
      {error && (
        <div className="flex items-center justify-between rounded-md border border-red-500/50 bg-red-500/10 p-4 text-xs text-red-300">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button type="button" onClick={() => setError(null)} className="text-red-400">
            <X size={16} />
          </button>
        </div>
      )}

      {successToast && (
        <div className="flex items-center justify-between rounded-md border border-emerald-500/50 bg-emerald-500/10 p-4 text-xs text-emerald-300">
          <div className="flex items-center gap-3">
            <CheckCircle size={18} className="shrink-0 text-emerald-400" />
            <span>{successToast}</span>
          </div>
          <button type="button" onClick={() => setSuccessToast(null)} className="text-emerald-400">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-[#2A3441] bg-[#141A23] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#8B949E] uppercase">
              Total Administrators
            </span>
            <Users className="text-[#3B82F6]" size={18} />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {loading ? "—" : error ? "—" : totalAdmins}
          </div>
        </div>

        <div className="rounded-xl border border-[#2A3441] bg-[#141A23] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#8B949E] uppercase">
              Active Accounts
            </span>
            <UserCheck className="text-emerald-400" size={18} />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400">
            {loading ? "—" : error ? "—" : activeAdmins}
          </div>
        </div>

        <div className="rounded-xl border border-[#2A3441] bg-[#141A23] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#8B949E] uppercase">
              Main Administrators
            </span>
            <ShieldAlert className="text-cyan-400" size={18} />
          </div>
          <div className="mt-2 text-2xl font-bold text-cyan-400">
            {loading ? "—" : error ? "—" : mainAdmins}
          </div>
        </div>

        <div className="rounded-xl border border-[#2A3441] bg-[#141A23] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#8B949E] uppercase">
              Pending Reset Requests
            </span>
            <KeyRound className="text-amber-400" size={18} />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-400">
            {loading ? "—" : error ? "—" : pendingRequests}
          </div>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex border-b border-[#2A3441] text-xs font-bold uppercase tracking-wider">
        <button
          type="button"
          onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 transition ${
            activeTab === "users"
              ? "border-[#3B82F6] text-[#3B82F6]"
              : "border-transparent text-[#8B949E] hover:text-white"
          }`}
        >
          <Users size={15} />
          Administrators ({users.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("requests")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 transition ${
            activeTab === "requests"
              ? "border-[#3B82F6] text-[#3B82F6]"
              : "border-transparent text-[#8B949E] hover:text-white"
          }`}
        >
          <KeyRound size={15} />
          Password Requests ({pendingRequests})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("activity")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 transition ${
            activeTab === "activity"
              ? "border-[#3B82F6] text-[#3B82F6]"
              : "border-transparent text-[#8B949E] hover:text-white"
          }`}
        >
          <History size={15} />
          Audit Logs ({activityLogs.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "users" && (
        <div className="overflow-x-auto rounded-xl border border-[#2A3441] bg-[#141A23]">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#2A3441] bg-[#0A0E14] text-[#8B949E] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Last Login</th>
                <th className="px-4 py-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2A3441]/60 text-[#E6EDF3]">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-[#1C2533]/50 transition duration-150">
                  <td className="px-4 py-3.5 font-medium text-white">{u.name}</td>
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">{u.email}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                        u.role === "MAIN_ADMIN"
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                        u.is_active
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-red-500/10 text-red-400"
                      }`}
                    >
                      <span
                        className={`size-1.5 rounded-full ${
                          u.is_active ? "bg-emerald-400" : "bg-red-400"
                        }`}
                      />
                      {u.is_active ? "ACTIVE" : "DISABLED"}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">
                    {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => handleToggleUserStatus(u)}
                        disabled={u.id === currentUser?.id}
                        className={`p-1.5 rounded transition ${
                          u.is_active
                            ? "text-amber-400 hover:bg-amber-500/20"
                            : "text-emerald-400 hover:bg-emerald-500/20"
                        } disabled:opacity-30 disabled:cursor-not-allowed`}
                        title={u.is_active ? "Disable Account" : "Enable Account"}
                      >
                        {u.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteUser(u)}
                        disabled={u.id === currentUser?.id}
                        className="p-1.5 rounded text-red-400 hover:bg-red-500/20 transition disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Delete Account"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "requests" && (
        <div className="overflow-x-auto rounded-xl border border-[#2A3441] bg-[#141A23]">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#2A3441] bg-[#0A0E14] text-[#8B949E] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-semibold">User</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Requested At</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2A3441]/60 text-[#E6EDF3]">
              {resetRequests.map((r) => (
                <tr key={r.id} className="hover:bg-[#1C2533]/50 transition duration-150">
                  <td className="px-4 py-3.5 font-medium text-white">
                    {r.user_name || r.user_id}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">{r.user_email || "N/A"}</td>
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">
                    {new Date(r.requested_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                        r.status === "PENDING"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : r.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          : "bg-red-500/20 text-red-300 border border-red-500/40"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    {r.status === "PENDING" ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setShowTempPwModal(r)}
                          className="flex items-center gap-1.5 rounded bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-blue-500 transition"
                        >
                          <KeyRound size={13} />
                          Set Temp Password
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRejectRequest(r)}
                          className="flex items-center gap-1 rounded bg-red-600/20 border border-red-500/40 px-2 py-1 text-[11px] font-semibold text-red-300 hover:bg-red-600 hover:text-white transition"
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="text-[11px] font-mono text-[#8B949E]">Processed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "activity" && (
        <div className="overflow-x-auto rounded-xl border border-[#2A3441] bg-[#141A23]">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#2A3441] bg-[#0A0E14] text-[#8B949E] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-semibold">Timestamp</th>
                <th className="px-4 py-3 font-semibold">Attempted Email</th>
                <th className="px-4 py-3 font-semibold">Result</th>
                <th className="px-4 py-3 font-semibold">IP Address</th>
                <th className="px-4 py-3 font-semibold">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2A3441]/60 text-[#E6EDF3]">
              {activityLogs.map((log) => (
                <tr key={log.id} className="hover:bg-[#1C2533]/50 transition duration-150">
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">
                    {new Date(log.login_time).toLocaleString()}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-white">{log.email_attempted}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                        log.success
                          ? "bg-emerald-500/20 text-emerald-300"
                          : "bg-red-500/20 text-red-300"
                      }`}
                    >
                      {log.success ? <CheckCircle size={12} /> : <XCircle size={12} />}
                      {log.success ? "SUCCESS" : "FAILED"}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[#8B949E]">
                    {log.ip_address || "127.0.0.1"}
                  </td>
                  <td className="px-4 py-3.5 text-[#8B949E]">{log.failure_reason || "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Administrator Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-[#2A3441] bg-[#141A23] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2A3441] pb-3">
              <h3 className="text-base font-bold text-white uppercase tracking-wider">
                Add Administrator
              </h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-[#8B949E] hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddUser} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                  placeholder="admin@netrakon.ai"
                />
              </div>

              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Role</label>
                <select
                  value={addRole}
                  onChange={(e) => setAddRole(e.target.value as any)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                >
                  <option value="ADMIN">ADMIN (Normal Surveillance)</option>
                  <option value="MAIN_ADMIN">MAIN_ADMIN (Full Admin Control)</option>
                </select>
              </div>

              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={addPassword}
                  onChange={(e) => setAddPassword(e.target.value)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                  placeholder="••••••••••••"
                />
              </div>

              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Confirm Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={addConfirmPassword}
                  onChange={(e) => setAddConfirmPassword(e.target.value)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                  placeholder="••••••••••••"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="rounded border border-[#2A3441] px-4 py-2 text-[#8B949E] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded bg-[#3B82F6] px-4 py-2 font-semibold text-white hover:bg-blue-500"
                >
                  Create Admin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Set Temporary Password Modal */}
      {showTempPwModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-[#2A3441] bg-[#141A23] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2A3441] pb-3">
              <h3 className="text-base font-bold text-white uppercase tracking-wider">
                Set Temporary Password
              </h3>
              <button
                type="button"
                onClick={() => setShowTempPwModal(null)}
                className="text-[#8B949E] hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSetTempPassword} className="mt-4 space-y-4 text-xs">
              <p className="text-[#8B949E]">
                Set a temporary password for user{" "}
                <span className="font-semibold text-white">
                  {showTempPwModal.user_name || showTempPwModal.user_email}
                </span>
                . The administrator can use this password to log in.
              </p>

              <div>
                <label className="block text-[#8B949E] font-semibold mb-1">Temporary Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={tempPassword}
                  onChange={(e) => setTempPassword(e.target.value)}
                  className="w-full rounded border border-[#2A3441] bg-[#0A0E14] p-2.5 text-white focus:border-[#3B82F6] focus:outline-none"
                  placeholder="••••••••••••"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTempPwModal(null)}
                  className="rounded border border-[#2A3441] px-4 py-2 text-[#8B949E] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded bg-[#3B82F6] px-4 py-2 font-semibold text-white hover:bg-blue-500"
                >
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminControlPage;


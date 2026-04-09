"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type User = { id: string; email: string; role: string; is_active: boolean };

const ROLES = ["admin", "manager", "reviewer", "candidate"];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", role: "candidate" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setUsers((await api.get("/users")).data);
  }
  useEffect(() => { load(); }, []);

  async function handleCreate() {
    setSaving(true); setError("");
    try {
      await api.post("/users", form);
      setShowForm(false);
      setForm({ email: "", password: "", role: "candidate" });
      load();
    } catch (e: any) { setError(e?.response?.data?.detail ?? "Failed"); }
    finally { setSaving(false); }
  }

  async function handleDeactivate(id: string) {
    if (!confirm("Deactivate this user?")) return;
    await api.delete(`/users/${id}`);
    load();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <button onClick={() => setShowForm(true)} className="btn-primary">+ New User</button>
      </div>
      <div className="space-y-2">
        {users.map((u) => (
          <div key={u.id} className="card flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">{u.email}</p>
              <p className="text-xs text-gray-400">{u.role} · {u.is_active ? "Active" : "Inactive"}</p>
            </div>
            {u.is_active && (
              <button onClick={() => handleDeactivate(u.id)} className="text-xs text-red-500 hover:underline">Deactivate</button>
            )}
          </div>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h2 className="text-lg font-bold">New User</h2>
            {error && <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>}
            <div><label className="label">Email</label><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input w-full" /></div>
            <div><label className="label">Password</label><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="input w-full" /></div>
            <div><label className="label">Role</label>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input w-full">
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleCreate} disabled={saving} className="btn-primary">{saving ? "Creating…" : "Create"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

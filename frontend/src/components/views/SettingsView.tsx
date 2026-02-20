"use client";

import { useState, useEffect } from "react";
import { Settings, Save, User, Shield, Target, Bell, Globe, Lock, LogOut } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";
import type { UserProfile } from "@/types";

const RISK_OPTIONS = [
  { value: "conservative", label: "Conservador", desc: "Bajo riesgo, preservar capital" },
  { value: "moderate", label: "Moderado", desc: "Balance riesgo/retorno" },
  { value: "aggressive", label: "Agresivo", desc: "Alto riesgo, máximo crecimiento" },
];

const HORIZON_OPTIONS = [
  { value: "short", label: "Corto plazo", desc: "< 1 año" },
  { value: "medium", label: "Medio plazo", desc: "1-5 años" },
  { value: "long", label: "Largo plazo", desc: "5+ años" },
];

const NOTIFICATION_OPTIONS = [
  { value: "all", label: "Todas" },
  { value: "important", label: "Importantes" },
  { value: "critical_only", label: "Solo críticas" },
  { value: "none", label: "Ninguna" },
];

const GOAL_PRESETS = [
  "Jubilación", "Libertad financiera", "Ahorro para vivienda",
  "Ingresos pasivos", "Crecimiento de capital", "Diversificación",
];

export default function SettingsView() {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState<UserProfile>({
    display_name: "",
    risk_tolerance: "moderate",
    investment_horizon: "medium",
    goals: [],
    preferred_currency: "EUR",
    notification_frequency: "important",
    notification_channels: ["telegram"],
    language: "es",
    theme: "dark",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMessage, setPwMessage] = useState<{type: string; text: string} | null>(null);

  useEffect(() => {
    fetchAPI<UserProfile>("/api/v1/user/profile")
      .then(setProfile)
      .catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const token = getToken();
      const res = await fetch("/api/v1/user/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  };

  const toggleGoal = (goal: string) => {
    setProfile((p) => ({
      ...p,
      goals: p.goals.includes(goal)
        ? p.goals.filter((g) => g !== goal)
        : [...p.goals, goal],
    }));
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setPwMessage({ type: "error", text: "Las contraseñas no coinciden" });
      return;
    }
    if (newPassword.length < 6) {
      setPwMessage({ type: "error", text: "La contraseña debe tener al menos 6 caracteres" });
      return;
    }
    setPwLoading(true);
    setPwMessage(null);
    try {
      const token = getToken();
      await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ new_password: newPassword }),
      });
      setPwMessage({ type: "ok", text: "Contraseña cambiada correctamente" });
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setPwMessage({ type: "error", text: "Error al cambiar la contraseña" });
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4 px-3 sm:px-0 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-oracle-accent" />
          <h2 className="text-lg font-semibold text-oracle-text">Configuración</h2>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-oracle-accent text-white rounded text-sm hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors w-full sm:w-auto"
        >
          <Save className="w-3.5 h-3.5" />
          {saved ? "Guardado" : saving ? "Guardando..." : "Guardar"}
        </button>
      </div>

      {/* Account info */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <User className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Cuenta</h3>
        </div>
        <div className="space-y-3 text-sm">
          <div>
            <span className="text-oracle-muted text-xs block mb-1">Email</span>
            <div className="bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text">
              {user?.email}
            </div>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-oracle-border">
            <span className="text-oracle-muted">Rol</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              user?.role === "admin"
                ? "bg-oracle-accent/20 text-oracle-accent"
                : "bg-oracle-border text-oracle-muted"
            }`}>
              {user?.role === "admin" ? "Administrador" : "Usuario"}
            </span>
          </div>
          <div className="pt-2 border-t border-oracle-border">
            <p className="text-xs text-oracle-muted mb-2">
              La gestión de contraseña y datos de cuenta se realiza en AIdentity.
            </p>
            <a
              href="https://aidentity.darc3.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-oracle-accent text-white rounded text-sm hover:bg-oracle-accent/80 transition-colors"
            >
              <Settings className="w-3.5 h-3.5" />
              Gestionar cuenta en AIdentity
            </a>
          </div>
        </div>
      </section>

      {/* Display name */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <User className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Nombre</h3>
        </div>
        <input
          type="text"
          value={profile.display_name}
          onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
          placeholder="Tu nombre"
          className="w-full bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
        />
      </section>

      {/* Risk tolerance */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Tolerancia al riesgo</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {RISK_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile({ ...profile, risk_tolerance: opt.value as UserProfile["risk_tolerance"] })}
              className={`p-3 rounded border text-left transition-colors ${
                profile.risk_tolerance === opt.value
                  ? "border-oracle-accent bg-oracle-accent/10"
                  : "border-oracle-border hover:border-oracle-muted"
              }`}
            >
              <p className="text-sm font-medium text-oracle-text">{opt.label}</p>
              <p className="text-[10px] text-oracle-muted mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Investment horizon */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Horizonte de inversión</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {HORIZON_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile({ ...profile, investment_horizon: opt.value as UserProfile["investment_horizon"] })}
              className={`p-3 rounded border text-left transition-colors ${
                profile.investment_horizon === opt.value
                  ? "border-oracle-accent bg-oracle-accent/10"
                  : "border-oracle-border hover:border-oracle-muted"
              }`}
            >
              <p className="text-sm font-medium text-oracle-text">{opt.label}</p>
              <p className="text-[10px] text-oracle-muted mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Display name */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <User className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Nombre</h3>
        </div>
        <input
          type="text"
          value={profile.display_name}
          onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
          placeholder="Tu nombre"
          className="w-full bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
        />
      </section>

      {/* Risk tolerance */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Tolerancia al riesgo</h3>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {RISK_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile({ ...profile, risk_tolerance: opt.value as UserProfile["risk_tolerance"] })}
              className={`p-3 rounded border text-left transition-colors ${
                profile.risk_tolerance === opt.value
                  ? "border-oracle-accent bg-oracle-accent/10"
                  : "border-oracle-border hover:border-oracle-muted"
              }`}
            >
              <p className="text-sm font-medium text-oracle-text">{opt.label}</p>
              <p className="text-[10px] text-oracle-muted mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Investment horizon */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Horizonte de inversión</h3>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {HORIZON_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile({ ...profile, investment_horizon: opt.value as UserProfile["investment_horizon"] })}
              className={`p-3 rounded border text-left transition-colors ${
                profile.investment_horizon === opt.value
                  ? "border-oracle-accent bg-oracle-accent/10"
                  : "border-oracle-border hover:border-oracle-muted"
              }`}
            >
              <p className="text-sm font-medium text-oracle-text">{opt.label}</p>
              <p className="text-[10px] text-oracle-muted mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Goals */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Objetivos financieros</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {GOAL_PRESETS.map((goal) => (
            <button
              key={goal}
              onClick={() => toggleGoal(goal)}
              className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                profile.goals.includes(goal)
                  ? "border-oracle-accent bg-oracle-accent/10 text-oracle-accent"
                  : "border-oracle-border text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {goal}
            </button>
          ))}
        </div>
      </section>

      {/* Notifications */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Bell className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Notificaciones</h3>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {NOTIFICATION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setProfile({ ...profile, notification_frequency: opt.value as UserProfile["notification_frequency"] })}
              className={`p-2 rounded border text-xs text-center transition-colors ${
                profile.notification_frequency === opt.value
                  ? "border-oracle-accent bg-oracle-accent/10 text-oracle-accent"
                  : "border-oracle-border text-oracle-muted hover:text-oracle-text"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>

      {/* Currency */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Globe className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Moneda preferida</h3>
        </div>
        <select
          value={profile.preferred_currency}
          onChange={(e) => setProfile({ ...profile, preferred_currency: e.target.value })}
          className="w-full bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text"
        >
          <option value="EUR">EUR (€)</option>
          <option value="USD">USD ($)</option>
          <option value="GBP">GBP (£)</option>
          <option value="CHF">CHF</option>
          <option value="JPY">JPY (¥)</option>
        </select>
      </section>

      {/* Change password */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 mb-3">
          <Lock className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-medium text-oracle-text text-sm">Cambiar contraseña</h3>
        </div>
        <div className="space-y-3">
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Nueva contraseña"
            className="w-full bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirmar contraseña"
            className="w-full bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
          />
          {pwMessage && (
            <p className={`text-xs ${pwMessage.type === "ok" ? "text-green-400" : "text-red-400"}`}>
              {pwMessage.text}
            </p>
          )}
          <button
            onClick={handleChangePassword}
            disabled={pwLoading || !newPassword}
            className="w-full sm:w-auto px-3 py-2 bg-oracle-accent text-white rounded text-sm hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
          >
            {pwLoading ? "Cambiando..." : "Cambiar contraseña"}
          </button>
        </div>
      </section>

      {/* Logout */}
      <section className="bg-oracle-panel border border-oracle-border rounded-lg p-3 sm:p-4">
        <button
          onClick={logout}
          className="flex items-center justify-center gap-2 px-4 py-2 w-full sm:w-auto text-red-400 hover:bg-red-400/10 rounded transition-colors text-sm"
        >
          <LogOut className="w-4 h-4" />
          Cerrar sesión
        </button>
      </section>
    </div>
  );
}

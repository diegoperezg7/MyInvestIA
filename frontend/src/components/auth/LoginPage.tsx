"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Lock, Mail, Eye, EyeOff, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-oracle-bg px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-wider">
            <span className="text-oracle-text">MyInvest</span>
            <span style={{ color: "var(--oracle-primary)" }}>IA</span>
          </h1>
          <p className="text-oracle-muted text-sm mt-1">
            AI Investment Intelligence
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-oracle-panel border border-oracle-border rounded-lg p-6 space-y-4"
        >
          <h2 className="text-lg font-semibold text-oracle-text text-center">
            Iniciar sesión
          </h2>

          {error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs text-oracle-muted mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-oracle-muted" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="tu@email.com"
                className="w-full bg-oracle-bg border border-oracle-border rounded pl-10 pr-3 py-2.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-oracle-muted mb-1">
              Contraseña
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-oracle-muted" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="Tu contraseña"
                className="w-full bg-oracle-bg border border-oracle-border rounded pl-10 pr-10 py-2.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-oracle-muted hover:text-oracle-text transition-colors"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-oracle-accent text-white rounded text-sm font-medium hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className="text-center text-oracle-muted text-[11px] mt-6">
          Acceso restringido. Contacta al administrador para obtener una cuenta.
        </p>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export function ResetForm() {
  const { updatePassword } = useAuth();
  const router = useRouter();

  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await updatePassword(newPassword);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password update failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>Set new password</h2>

        {error && <div className="auth-flash">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="auth-field">
            <span>New password</span>
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
            <span className="auth-hint">At least 8 characters</span>
          </label>

          <button type="submit" className="ink-btn" disabled={submitting}>
            {submitting ? "Updating..." : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

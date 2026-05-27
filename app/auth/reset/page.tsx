"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function ResetPage() {
  const { user, updatePassword } = useAuth();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!user) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h2>Reset password</h2>
          <p style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", textAlign: "center", color: "var(--color-ink-soft)" }}>
            Open the reset link from your email first.
          </p>
          <div className="auth-links">
            <Link href="/auth/forgot">Request a new link</Link>
          </div>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await updatePassword(password);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not update password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>New password</h2>
        {error && <div className="auth-flash">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="password">New password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
            />
          </div>
          <button type="submit" className="ink-btn" disabled={submitting}>
            {submitting ? "Updating..." : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

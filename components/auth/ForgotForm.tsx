"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export function ForgotForm() {
  const { resetPassword } = useAuth();

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await resetPassword(email);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password reset failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h2>Check your inbox</h2>
          <div className="auth-flash">
            If an account exists for that email, we sent a password-reset link.
          </div>
          <p className="auth-links">
            <Link href="/auth/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>Forgot password</h2>

        {error && <div className="auth-flash">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>

          <button type="submit" className="ink-btn" disabled={submitting}>
            {submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="auth-links">
          <Link href="/auth/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function ForgotPage() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await resetPassword(email.trim().toLowerCase());
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not send reset email.");
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h2>Check your email</h2>
          <p style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", textAlign: "center", color: "var(--color-ink-soft)" }}>
            If that email is registered, we just sent a reset link.
          </p>
          <div className="auth-links">
            <Link href="/auth/login">Back to sign in</Link>
          </div>
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
          <div className="auth-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>
          <button type="submit" className="ink-btn" disabled={submitting}>
            {submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/auth/login">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}

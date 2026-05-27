"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function SignupPage() {
  const { signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password || !displayName.trim()) {
      setError("All fields are required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await signUp(email.trim().toLowerCase(), password, displayName.trim());
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h2>Check your inbox</h2>
          <p style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", textAlign: "center", color: "var(--color-ink-soft)" }}>
            We sent a confirmation link to your email. Click it to activate your account.
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
        <h2>Create account</h2>
        {error && <div className="auth-flash">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="display_name">Display name</label>
            <input
              id="display_name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
            />
          </div>
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
          <div className="auth-field">
            <label htmlFor="password">Password</label>
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
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/auth/login">Already have an account? Sign in</Link>
        </div>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export function Masthead() {
  const { user } = useAuth();
  const pathname = usePathname();
  const isProfile = pathname === "/profile";

  const accountHref = user ? "/profile" : "/auth/login";
  const accountLabel = user ? "Your cellar" : "Sign in";

  return (
    <header className="masthead">
      <div className="vol">
        {isProfile ? (
          <Link href="/" className="nav-strip__link">
            &larr; Front page
          </Link>
        ) : (
          <>
            <span>A broadsheet for the discerning drinker</span>
            <Link href={accountHref} className="nav-strip__link">
              {accountLabel}
            </Link>
          </>
        )}
      </div>
      <h1>
        <Link href="/" className="masthead-home">
          The Beer <span className="amp">&amp;</span> Predictor
        </Link>
      </h1>
      <p className="kicker">
        Seven sliders, an honest catalogue, and the patience to read a chart.
      </p>
      <hr className="doublerule" />
    </header>
  );
}

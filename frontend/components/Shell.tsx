"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { ThemeToggle } from "./ThemeToggle";

export function Shell({ children }: { children: ReactNode }) {
  const { isAuthenticated, logout } = useAuth();

  return (
    <>
      <header className="flex items-center justify-between border-b border-black/10 px-6 py-3 dark:border-white/10">
        <Link href="/" className="font-semibold">
          Academic Writing Editor
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {isAuthenticated && (
            <button
              onClick={logout}
              className="rounded border border-black/20 px-2 py-1 text-sm dark:border-white/20"
            >
              Log out
            </button>
          )}
        </div>
      </header>
      <main className="flex flex-1 flex-col">{children}</main>
    </>
  );
}

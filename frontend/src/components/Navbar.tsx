"use client";

import { signOut, useSession } from 'next-auth/react';
import Link from 'next/link';
import { LogOut, Ruler } from 'lucide-react';

export function Navbar() {
  const { data: session } = useSession();

  return (
    <header className="border-b border-line/70 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-ink text-paper shadow-glow">
            <Ruler className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.32em] text-moss">Length Lab</p>
            <p className="text-xs text-ink/60">Google login measurement workspace</p>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium text-ink">{session?.user?.name ?? 'Signed in user'}</p>
            <p className="text-xs text-ink/60">{session?.user?.email ?? 'Ready to measure'}</p>
          </div>
          <button
            type="button"
            onClick={() => signOut({ callbackUrl: '/' })}
            className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-ink transition hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-glow"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { signIn, useSession } from 'next-auth/react';
import { ArrowRight, ChartNoAxesCombined, Layers3, Ruler, ShieldCheck } from 'lucide-react';

export default function LandingPage() {
  const { status } = useSession();
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const error = new URLSearchParams(window.location.search).get('error');
    setAuthError(error);
  }, []);

  return (
    <main className="min-h-screen bg-hero-radial px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col overflow-hidden rounded-[2rem] border border-line bg-white/90 shadow-glow backdrop-blur">
        <header className="flex items-center justify-between border-b border-line px-6 py-5 sm:px-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.35em] text-moss">Length Lab</p>
            <p className="text-sm text-ink/60">Measure every object from Google-authenticated uploads</p>
          </div>
          <div className="flex items-center gap-3">
            {status === 'authenticated' ? (
              <Link href="/dashboard" className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5">
                Open dashboard
              </Link>
            ) : (
              <button
                type="button"
                onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
                className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5"
              >
                Sign in with Google
              </button>
            )}
          </div>
        </header>

        <section className="grid flex-1 gap-10 px-6 py-10 lg:grid-cols-[1.1fr_0.9fr] lg:px-8 lg:py-16">
          <div className="flex flex-col justify-center gap-6">
            {authError ? (
              <div className="rounded-2xl border border-coral/40 bg-coral/10 p-4 text-sm text-ink">
                <p className="font-semibold">Google sign-in failed: {authError}</p>
                <p className="mt-1 text-ink/75">
                  For Error 400 redirect_uri_mismatch, add this exact Authorized redirect URI in Google Cloud OAuth client:
                  <span className="mt-1 block font-mono text-xs">http://localhost:3000/api/auth/callback/google</span>
                </p>
              </div>
            ) : null}
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-line bg-sand/50 px-4 py-2 text-sm text-ink/70">
              <Ruler className="h-4 w-4 text-moss" />
              Google login, project saving, and measurement workflow
            </div>
            <div className="space-y-4">
              <h1 className="max-w-2xl font-[family-name:var(--font-space-grotesk)] text-5xl leading-tight text-balance text-ink sm:text-6xl">
                Turn uploaded images into a structured measurement workspace.
              </h1>
              <p className="max-w-xl text-lg leading-8 text-ink/70">
                Sign in with Google, open your dashboard, upload up to three images, run the measurement flow, select the objects you want, and save the result as a new project.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <button
                type="button"
                onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
                className="inline-flex items-center gap-2 rounded-full bg-moss px-6 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5 hover:bg-[#275f53]"
              >
                Start with Google
                <ArrowRight className="h-4 w-4" />
              </button>
              <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-6 py-3 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:border-ink/20">
                Preview dashboard
              </Link>
            </div>
          </div>

          <div className="grid gap-4 self-center rounded-[2rem] border border-line bg-paper p-5 shadow-sm">
            <div className="rounded-[1.5rem] bg-ink p-5 text-paper shadow-glow">
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-sand">Workflow</p>
              <div className="mt-5 space-y-4">
                <FeatureRow icon={ShieldCheck} title="Google authentication" copy="Only signed-in users can enter the workspace." />
                <FeatureRow icon={Layers3} title="Three image upload" copy="Add up to three photos before measuring." />
                <FeatureRow icon={ChartNoAxesCombined} title="Project saving" copy="Store selected measurements as a named project." />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <MiniCard value="01" label="Sign in" />
              <MiniCard value="02" label="Measure" />
              <MiniCard value="03" label="Save" />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function FeatureRow({ icon: Icon, title, copy }: { icon: React.ComponentType<{ className?: string }>; title: string; copy: string }) {
  return (
    <div className="flex gap-3 rounded-2xl bg-white/8 p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/12">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-paper/75">{copy}</p>
      </div>
    </div>
  );
}

function MiniCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[1.4rem] border border-line bg-white p-4 shadow-sm">
      <p className="font-[family-name:var(--font-space-grotesk)] text-2xl text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink/60">{label}</p>
    </div>
  );
}

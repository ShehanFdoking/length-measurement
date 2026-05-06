"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { Loader2 } from 'lucide-react';

import { AppShell } from '@/components/AppShell';
import { fetchProject, type ProjectRecord } from '@/lib/api';

function formatMetricTriplet(valueCm: number) {
  return {
    mm: `${(valueCm * 10).toFixed(1)} mm`,
    cm: `${valueCm.toFixed(2)} cm`,
    m: `${(valueCm / 100).toFixed(3)} m`
  };
}

export default function ProjectPage() {
  const { data: session, status } = useSession();
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectRecord | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!params.id) return;

    fetchProject(params.id)
      .then(setProject)
      .catch((fetchError) => setError(fetchError instanceof Error ? fetchError.message : 'Project not found.'));
  }, [params.id]);

  if (status === 'loading') {
    return <LoadingState />;
  }

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-[2rem] border border-line bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-ink">Please sign in first.</p>
          <Link href="/" className="mt-5 inline-flex rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper">
            Go to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <section className="rounded-[2rem] border border-line bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Saved project</p>
        {error ? <p className="mt-4 rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">{error}</p> : null}
        {!project ? (
          <div className="mt-6 flex items-center gap-3 text-ink/60">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading project...
          </div>
        ) : (
          <div className="mt-6 space-y-6">
            <div>
              <h1 className="font-[family-name:var(--font-space-grotesk)] text-4xl text-ink">{project.name}</h1>
              <p className="mt-2 text-sm text-ink/60">Created {new Date(project.createdAt).toLocaleString()}</p>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <InfoCard label="Measurement ID" value={project.measurementId} />
              <InfoCard label="Selected objects" value={String(project.selectedObjectIds.length)} />
              <InfoCard label="Images measured" value={String(project.summary.images.length)} />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {project.summary.images.map((image) => (
                <div key={`${image.imageName}-${image.imageIndex}`} className="rounded-[1.75rem] border border-line bg-paper/40 p-5">
                  <p className="text-sm font-semibold text-ink">{image.imageName}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.25em] text-ink/45">Background + object measurements</p>
                  <div className="mt-4 space-y-3 text-sm text-ink/65">
                    <p>Objects: {image.objects.length}</p>
                    <MetricLine label="Background height" valueCm={image.background.height} />
                    <MetricLine label="Background width" valueCm={image.background.width} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </AppShell>
  );
}

function MetricLine({ label, valueCm }: { label: string; valueCm: number }) {
  const formatted = formatMetricTriplet(valueCm);

  return (
    <div className="rounded-2xl border border-white/70 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-[0.22em] text-ink/45">{label}</p>
      <p className="mt-1 font-semibold text-ink">{formatted.mm}</p>
      <p className="text-xs text-ink/65">{formatted.cm} · {formatted.m}</p>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.5rem] border border-line bg-paper/35 p-4">
      <p className="text-xs uppercase tracking-[0.25em] text-ink/45">{label}</p>
      <p className="mt-2 break-all font-semibold text-ink">{value}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="animate-pulse rounded-[2rem] border border-line bg-white px-8 py-6 text-ink/60 shadow-sm">Loading project details...</div>
    </main>
  );
}

"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { ArrowRight, FolderOpen, Sparkles, UploadCloud } from 'lucide-react';

import { AppShell } from '@/components/AppShell';
import { fetchProjects, type ProjectRecord } from '@/lib/api';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  useEffect(() => {
    if (!session) return;

    setLoadingProjects(true);
    fetchProjects()
      .then(setProjects)
      .finally(() => setLoadingProjects(false));
  }, [session]);

  if (status === 'loading') {
    return <DashboardLoading />;
  }

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="max-w-lg rounded-[2rem] border border-line bg-white p-8 text-center shadow-glow">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Authentication required</p>
          <h1 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-4xl text-ink">Sign in to open the workspace.</h1>
          <p className="mt-3 text-ink/65">Use Google login on the home page, then return here to access the measurement dashboard.</p>
          <Link href="/" className="mt-6 inline-flex items-center justify-center rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper">
            Go to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[2rem] border border-line bg-white p-8 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Home</p>
          <h1 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-4xl text-ink sm:text-5xl">
            Welcome back, {session.user?.name?.split(' ')[0] ?? 'there'}.
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-ink/70">
            This workspace keeps your upload, measurement, review, and project-save steps together in one place.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link href="/measure" className="inline-flex items-center gap-2 rounded-full bg-moss px-6 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5 hover:bg-[#275f53]">
              Start now
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#projects" className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-6 py-3 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:border-ink/20">
              View projects
            </a>
          </div>
        </div>

        <div className="grid gap-4">
          <MetricCard icon={UploadCloud} title="Upload up to 3 images" copy="Measure products, objects, or scenes from a small batch of files." />
          <MetricCard icon={Sparkles} title="Isolated views" copy="Review object cards and background views separately before saving." />
          <MetricCard icon={FolderOpen} title="Project storage" copy="Save selected measurements with a project name for later access." />
        </div>
      </section>

      <section id="projects" className="rounded-[2rem] border border-line bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Projects</p>
            <h2 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-3xl text-ink">Saved measurements will appear here.</h2>
          </div>
          <Link href="/measure" className="inline-flex w-fit items-center gap-2 rounded-full border border-line bg-paper px-5 py-3 text-sm font-semibold text-ink">
            Create a new project
          </Link>
        </div>

        {loadingProjects ? (
          <div className="mt-6 rounded-2xl border border-line bg-paper/30 px-4 py-3 text-sm text-ink/60">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <EmptyProjectCard title="Project workspace" copy="After measurement, choose the objects you want and save them under a name." />
            <EmptyProjectCard title="Background separation" copy="The backend contract keeps object measurements and background measurements separate." />
            <EmptyProjectCard title="Review flow" copy="Open a saved project to revisit the selected objects and dimensions." />
          </div>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`} className="rounded-[1.5rem] border border-line bg-paper/30 p-5 transition hover:-translate-y-0.5 hover:border-moss/40">
                <p className="text-xs uppercase tracking-[0.25em] text-ink/45">Saved project</p>
                <p className="mt-3 text-lg font-semibold text-ink">{project.name}</p>
                <p className="mt-2 text-sm text-ink/65">{project.selectedObjectIds.length} selected objects · {project.summary.images.length} measured images</p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}

function MetricCard({ icon: Icon, title, copy }: { icon: React.ComponentType<{ className?: string }>; title: string; copy: string }) {
  return (
    <div className="rounded-[2rem] border border-line bg-white p-6 shadow-sm">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sand text-ink">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mt-4 text-xl font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-ink/65">{copy}</p>
    </div>
  );
}

function EmptyProjectCard({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="rounded-[1.75rem] border border-dashed border-line bg-sand/25 p-5">
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-2 text-sm leading-6 text-ink/65">{copy}</p>
    </div>
  );
}

function DashboardLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="animate-pulse rounded-[2rem] border border-line bg-white px-8 py-6 text-ink/60 shadow-sm">
        Loading dashboard...
      </div>
    </main>
  );
}

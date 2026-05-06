"use client";

import type { ReactNode } from 'react';

import { Footer } from '@/components/Footer';
import { Navbar } from '@/components/Navbar';
import { Sidebar } from '@/components/Sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-hero-radial">
      <Navbar />
      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:px-8">
        <Sidebar />
        <div className="space-y-6">{children}</div>
      </main>
      <Footer />
    </div>
  );
}

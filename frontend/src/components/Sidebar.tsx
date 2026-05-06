"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Camera, FolderOpen, LayoutDashboard, Scale } from 'lucide-react';
import clsx from 'clsx';

const items = [
  { href: '/dashboard', label: 'Home', icon: LayoutDashboard },
  { href: '/measure', label: 'Measure', icon: Scale },
  { href: '/dashboard#projects', label: 'Projects', icon: FolderOpen },
  { href: '/dashboard#capture', label: 'Capture', icon: Camera }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="rounded-3xl border border-line bg-white p-4 shadow-sm">
      <p className="mb-4 text-xs font-semibold uppercase tracking-[0.3em] text-ink/45">Workspace</p>
      <nav className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition',
                isActive
                  ? 'bg-ink text-paper shadow-glow'
                  : 'text-ink/70 hover:bg-sand/40 hover:text-ink'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

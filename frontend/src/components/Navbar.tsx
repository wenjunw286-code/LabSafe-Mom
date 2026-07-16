"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardList, BookOpen } from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Home" },
  { href: "/history", label: "Reports", icon: ClipboardList },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-white/85 backdrop-blur-xl border-b border-rose-100 no-print" role="navigation" aria-label="Main navigation">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2.5 group focus:outline-none focus:ring-2 focus:ring-rose-400 rounded-lg -ml-1.5 px-1.5 py-1"
          aria-label="LabSafe Mom Home"
        >
          <Image src="/cover.png" alt="LabSafe Mom" width={32} height={32} className="rounded-lg object-cover" />
          <span className="text-lg font-bold text-neutral-800">
            LabSafe <span className="text-rose-500">Mom</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-rose-50 text-rose-700"
                  : "text-neutral-500 hover:text-neutral-700 hover:bg-neutral-50",
              )}
            >
              {Icon && <Icon className="w-4 h-4" />}
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

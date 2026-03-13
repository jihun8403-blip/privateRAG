"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Tags, CalendarClock, FileText, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/chat",      label: "챗봇",         icon: MessageSquare },
  { href: "/topics",    label: "키워드 관리",   icon: Tags },
  { href: "/schedule",  label: "스케줄 관리",   icon: CalendarClock },
  { href: "/documents", label: "문서 관리",     icon: FileText },
  { href: "/models",    label: "모델 관리",     icon: Cpu },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card flex flex-col h-screen sticky top-0">
      <div className="px-5 py-4 border-b border-border">
        <span className="font-bold text-primary text-lg tracking-tight">PrivateRAG</span>
      </div>
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-border text-xs text-muted-foreground">
        Backend: {process.env.NEXT_PUBLIC_API_URL ?? "localhost:8000"}
      </div>
    </aside>
  );
}

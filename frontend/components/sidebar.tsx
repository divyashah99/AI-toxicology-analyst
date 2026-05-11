"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Beaker, FileText, Home, LayoutDashboard, MessageSquare, ScrollText } from "lucide-react";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyze", label: "Compound analysis", icon: Beaker },
  { href: "/papers", label: "Papers", icon: FileText },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/reports", label: "Reports", icon: ScrollText },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <div className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
          <Beaker className="h-4 w-4" />
        </div>
        <Link href="/" className="font-semibold tracking-tight">
          ToxAnalyst
        </Link>
      </div>
      <nav className="flex flex-col gap-1 p-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto border-t p-3 text-xs text-muted-foreground">
        <Link href="/" className="hover:text-foreground">
          <Home className="mr-1 inline h-3 w-3" /> Landing
        </Link>
      </div>
    </aside>
  );
}

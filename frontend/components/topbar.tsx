"use client";
import { ThemeToggle } from "./theme-toggle";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-4 md:px-6">
      <div>
        <h1 className="text-sm font-semibold tracking-tight md:text-base">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        <a
          href="https://modelcontextprotocol.io"
          target="_blank"
          rel="noreferrer"
          className="hidden rounded-full border px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground sm:inline-block"
        >
          Powered by MCP
        </a>
        <ThemeToggle />
      </div>
    </header>
  );
}

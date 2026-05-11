import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
  title: "AI Toxicology Analyst",
  description:
    "MCP-orchestrated AI research assistant for compound analysis and toxicity reporting.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}

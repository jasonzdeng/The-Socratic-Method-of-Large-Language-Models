import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Socratic Workspace",
  description: "Collaborative environment for exploring ideas",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-50">
      <body className="min-h-full font-sans text-slate-900">{children}</body>
    </html>
  );
}

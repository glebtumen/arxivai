import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArchiveBot Library",
  description: "Your personal AI-organized media knowledge base",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-900">
        <header className="border-b bg-white">
          <div className="mx-auto max-w-5xl px-4 py-4">
            <h1 className="text-xl font-bold">📚 ArchiveBot Library</h1>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

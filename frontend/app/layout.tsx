import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";
import "katex/dist/katex.min.css";


export const metadata: Metadata = {
  title: "Recursive Paper Study Tool",
  description: "A local MVP for recursive paper learning."
};


export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto min-h-screen max-w-7xl px-6 py-8">
          <header className="mb-8 flex flex-col gap-4 border-b border-line pb-6 md:flex-row md:items-end md:justify-between">
            <div>
              <Link href="/" className="font-serif text-3xl font-semibold text-ink">
                Recursive Paper Study Tool
              </Link>
              <p className="mt-2 max-w-2xl text-sm text-muted">
                Upload one paper, annotate first mentions, expand concepts recursively, and track what you have mastered.
              </p>
            </div>
            <nav className="flex gap-4 text-sm">
              <Link href="/">Upload</Link>
              <Link href="/mastered">Mastered</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

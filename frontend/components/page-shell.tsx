"use client";

export function PageShell({
  title,
  description,
  aside,
  children
}: {
  title: string;
  description?: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section className="rounded-2xl border border-line bg-white/90 p-6 shadow-sm">
        <header className="mb-6 border-b border-line pb-4">
          <h1 className="font-serif text-3xl text-ink">{title}</h1>
          {description ? <p className="mt-2 text-sm text-muted">{description}</p> : null}
        </header>
        {children}
      </section>
      <aside className="space-y-4">{aside}</aside>
    </div>
  );
}

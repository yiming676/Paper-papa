"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { PageShell } from "@/components/page-shell";
import { StatusBadge } from "@/components/status-badge";
import { getMasteredConcepts } from "@/lib/api";
import { MasteredConceptItem } from "@/types";


export default function MasteredPage() {
  const [items, setItems] = useState<MasteredConceptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMasteredConcepts()
      .then((response) => setItems(response.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load mastered concepts."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <LoadingState label="Loading mastered concepts..." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  return (
    <PageShell
      title="Mastered concepts"
      description="Concepts marked as mastered in the local single-user state table."
    >
      {items.length === 0 ? (
        <div className="rounded-xl border border-line bg-panel p-6 text-sm text-muted">
          No mastered concepts yet.
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <Link
              key={item.id}
              href={`/concepts/${item.id}`}
              className="block rounded-2xl border border-line bg-white p-5 shadow-sm"
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="font-serif text-xl text-ink">{item.canonical_name}</h2>
                  <p className="mt-2 text-sm text-muted">{item.short_explanation ?? "No summary available."}</p>
                </div>
                <StatusBadge label="mastered" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageShell>
  );
}

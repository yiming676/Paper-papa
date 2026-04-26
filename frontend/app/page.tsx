"use client";

import { PageShell } from "@/components/page-shell";
import { UploadForm } from "@/components/upload-form";


export default function UploadPage() {
  return (
    <PageShell
      title="Recursive Paper Study Tool"
      description="Upload an AI paper PDF to generate a structured study report with clickable beginner-facing concepts."
      aside={
        <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
          <h2 className="font-serif text-xl text-ink">Core workflow</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>Structured paper report</li>
            <li>Beginner-oriented keyword detection</li>
            <li>Clickable concept pages</li>
            <li>On-demand recursive prerequisites up to 10 levels</li>
          </ul>
        </div>
      }
    >
      <UploadForm />
    </PageShell>
  );
}

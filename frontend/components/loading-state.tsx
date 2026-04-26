"use client";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-6 text-sm text-muted shadow-sm">
      {label}
    </div>
  );
}

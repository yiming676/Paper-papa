"use client";

import { useTransition } from "react";

import { expandConcept } from "@/lib/api";
import { ConceptExpandResponse } from "@/types";


export function ExpandButton({
  conceptId,
  documentId,
  language,
  onExpanded
}: {
  conceptId: number;
  documentId?: number;
  language: "en" | "zh";
  onExpanded: (result: ConceptExpandResponse) => void;
}) {
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => {
        startTransition(async () => {
          const result = await expandConcept(conceptId, documentId);
          onExpanded(result);
        });
      }}
      className="rounded-xl border border-line bg-white px-4 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? (language === "zh" ? "正在补全..." : "Expanding...") : language === "zh" ? "刷新前置概念" : "Refresh prerequisites"}
    </button>
  );
}

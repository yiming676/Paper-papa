"use client";

import { useTransition } from "react";

import { updateConceptState } from "@/lib/api";
import { ConceptState } from "@/types";


const OPTIONS: ConceptState[] = ["unknown", "learning", "mastered"];

export function StateButtons({
  conceptId,
  currentState,
  language,
  onUpdated
}: {
  conceptId: number;
  currentState: ConceptState;
  language: "en" | "zh";
  onUpdated: (next: ConceptState) => void;
}) {
  const [pending, startTransition] = useTransition();
  const labels: Record<ConceptState, string> =
    language === "zh"
      ? { unknown: "未掌握", learning: "学习中", mastered: "已掌握" }
      : { unknown: "unknown", learning: "learning", mastered: "mastered" };

  return (
    <div className="flex flex-wrap gap-3">
      {OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          disabled={pending}
          onClick={() => {
            startTransition(async () => {
              await updateConceptState(conceptId, option);
              onUpdated(option);
            });
          }}
          className={`rounded-xl border px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60 ${
            currentState === option
              ? "border-ink bg-ink text-white"
              : "border-line bg-white text-ink"
          }`}
        >
          {labels[option]}
        </button>
      ))}
    </div>
  );
}

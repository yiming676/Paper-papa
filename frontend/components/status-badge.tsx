"use client";

import clsx from "clsx";

interface StatusBadgeProps {
  label: string;
  language?: "en" | "zh";
}

const STYLE_BY_STATUS: Record<string, string> = {
  uploaded: "bg-slate-100 text-slate-700",
  parsed: "bg-amber-100 text-amber-800",
  annotated: "bg-emerald-100 text-emerald-800",
  unknown: "bg-slate-100 text-slate-700",
  learning: "bg-blue-100 text-blue-800",
  mastered: "bg-emerald-100 text-emerald-800"
};

const TEXT_BY_STATUS_ZH: Record<string, string> = {
  uploaded: "已上传",
  parsed: "已解析",
  annotated: "已标注",
  unknown: "未掌握",
  learning: "学习中",
  mastered: "已掌握"
};

export function StatusBadge({ label, language = "en" }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.12em]",
        STYLE_BY_STATUS[label] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {language === "zh" ? TEXT_BY_STATUS_ZH[label] ?? label : label}
    </span>
  );
}

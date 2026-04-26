"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useState } from "react";

import { annotateDocument, parseDocument, PreferredLanguage, uploadPdf } from "@/lib/api";

type UploadStageStatus = "pending" | "active" | "done" | "error";

interface UploadStage {
  id: "upload" | "parse" | "annotate" | "complete";
  label: string;
  description: string;
  status: UploadStageStatus;
}

function buildStages(language: PreferredLanguage): UploadStage[] {
  const isZh = language === "zh";
  return [
    {
      id: "upload",
      label: isZh ? "上传 PDF" : "Upload PDF",
      description: isZh ? "保存文件并创建文档记录" : "Save the file and create the document record",
      status: "pending"
    },
    {
      id: "parse",
      label: isZh ? "生成结构化学习报告" : "Generate structured study report",
      description: isZh ? "30 页内优先发送完整抽取文本，会消耗较多 token" : "Papers up to 30 pages send full extracted text first, using more tokens",
      status: "pending"
    },
    {
      id: "annotate",
      label: isZh ? "创建可跳转概念" : "Create concept links",
      description: isZh ? "抽取术语、参数、公式并链接首次出现" : "Extract terms, parameters, formulas, and link first mentions",
      status: "pending"
    },
    {
      id: "complete",
      label: isZh ? "完成" : "Completed",
      description: isZh ? "准备跳转到文档阅读页" : "Ready to open the document reader",
      status: "pending"
    }
  ];
}

function updateStages(
  items: UploadStage[],
  activeId: UploadStage["id"],
  mode: UploadStageStatus
): UploadStage[] {
  const order: UploadStage["id"][] = ["upload", "parse", "annotate", "complete"];
  const activeIndex = order.indexOf(activeId);

  return items.map((item) => {
    const itemIndex = order.indexOf(item.id);

    if (mode === "active") {
      if (item.id === activeId) {
        return { ...item, status: "active" };
      }
      if (itemIndex < activeIndex) {
        return { ...item, status: "done" };
      }
      return { ...item, status: item.status === "error" ? "error" : "pending" };
    }

    if (mode === "done" && item.id === activeId) {
      return { ...item, status: "done" };
    }

    if (mode === "error" && item.id === activeId) {
      return { ...item, status: "error" };
    }

    return item;
  });
}

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preferredLanguage, setPreferredLanguage] = useState<PreferredLanguage>("zh");
  const [status, setStatus] = useState("请选择 PDF 文件并开始处理。");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stages, setStages] = useState<UploadStage[]>(() => buildStages("zh"));

  const isZh = preferredLanguage === "zh";

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setError(null);
  }

  function onLanguageChange(nextLanguage: PreferredLanguage) {
    setPreferredLanguage(nextLanguage);
    setStatus(nextLanguage === "zh" ? "请选择 PDF 文件并开始处理。" : "Select a PDF and start processing.");
    setStages(buildStages(nextLanguage));
    setError(null);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError(isZh ? "请先选择一个 PDF 文件。" : "Please choose a PDF file.");
      return;
    }

    setLoading(true);
    setError(null);
    setStages(buildStages(preferredLanguage));

    try {
      setStages((current) => updateStages(current, "upload", "active"));
      setStatus(isZh ? "正在上传 PDF..." : "Uploading PDF...");
      const uploaded = await uploadPdf(file, preferredLanguage);
      setStages((current) => updateStages(current, "upload", "done"));

      setStages((current) => updateStages(current, "parse", "active"));
      setStatus(isZh ? "正在生成结构化学习报告..." : "Generating the structured study report...");
      await parseDocument(uploaded.id);
      setStages((current) => updateStages(current, "parse", "done"));

      setStages((current) => updateStages(current, "annotate", "active"));
      setStatus(isZh ? "正在创建可跳转概念链接..." : "Creating clickable concept links...");
      await annotateDocument(uploaded.id);
      setStages((current) => updateStages(current, "annotate", "done"));

      setStages((current) => updateStages(current, "complete", "done"));
      setStatus(isZh ? "处理完成，正在进入文档页。" : "Completed. Opening the document page.");
      router.push(`/documents/${uploaded.id}`);
    } catch (err) {
      const nextError = err instanceof Error ? err.message : isZh ? "处理失败。" : "Processing failed.";
      setError(nextError);
      setStages((current) => {
        const active = current.find((item) => item.status === "active");
        return active ? updateStages(current, active.id, "error") : current;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="rounded-2xl border border-dashed border-line bg-panel p-6">
        <label htmlFor="pdf" className="block text-sm font-medium text-ink">
          {isZh ? "论文 PDF" : "PDF paper"}
        </label>
        <input
          id="pdf"
          type="file"
          accept="application/pdf"
          onChange={onFileChange}
          className="mt-3 block w-full rounded-lg border border-line bg-white px-3 py-2 text-sm"
        />

        <label htmlFor="preferred-language" className="mt-5 block text-sm font-medium text-ink">
          {isZh ? "输出语言" : "Output language"}
        </label>
        <select
          id="preferred-language"
          value={preferredLanguage}
          onChange={(event) => onLanguageChange(event.target.value as PreferredLanguage)}
          className="mt-3 block w-full rounded-lg border border-line bg-white px-3 py-2 text-sm"
        >
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
        <p className="mt-3 text-xs leading-5 text-muted">
          {isZh
            ? "提示：30 页内论文会优先把完整 PDF 抽取文本发送给模型，以减少“只读摘要”的问题；这会明显增加 API token 消耗。"
            : "Note: papers up to 30 pages send the full extracted PDF text to reduce summary-only reports; this can significantly increase API token usage."}
        </p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="rounded-xl bg-ink px-5 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? (isZh ? "处理中..." : "Processing...") : isZh ? "上传并开始处理" : "Upload and Process"}
      </button>

      <div className="rounded-2xl border border-line bg-white p-5 shadow-sm">
        <p className="text-sm font-medium text-ink">{isZh ? "处理进度" : "Processing progress"}</p>
        <p className="mt-2 text-sm text-muted">{status}</p>

        <div className="mt-4 space-y-3">
          {stages.map((stage, index) => {
            const badgeText =
              stage.status === "done"
                ? isZh
                  ? "已完成"
                  : "Done"
                : stage.status === "active"
                  ? isZh
                    ? "进行中"
                    : "In progress"
                  : stage.status === "error"
                    ? isZh
                      ? "出错"
                      : "Error"
                    : isZh
                      ? "等待中"
                      : "Pending";

            const badgeClass =
              stage.status === "done"
                ? "bg-emerald-100 text-emerald-800"
                : stage.status === "active"
                  ? "bg-blue-100 text-blue-800"
                  : stage.status === "error"
                    ? "bg-red-100 text-red-700"
                    : "bg-slate-100 text-slate-600";

            return (
              <div
                key={stage.id}
                className={`rounded-xl border px-4 py-3 ${
                  stage.status === "active"
                    ? "border-blue-200 bg-blue-50"
                    : stage.status === "done"
                      ? "border-emerald-200 bg-emerald-50"
                      : stage.status === "error"
                        ? "border-red-200 bg-red-50"
                        : "border-line bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-600 ring-1 ring-line">
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink">{stage.label}</p>
                      <p className="mt-1 text-xs text-muted">{stage.description}</p>
                    </div>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${badgeClass}`}>{badgeText}</span>
                </div>
              </div>
            );
          })}
        </div>

        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      </div>
    </form>
  );
}

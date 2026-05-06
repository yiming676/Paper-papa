"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ErrorState } from "@/components/error-state";
import { LoadingState } from "@/components/loading-state";
import { MarkdownViewer } from "@/components/markdown-viewer";
import { PageShell } from "@/components/page-shell";
import { StatusBadge } from "@/components/status-badge";
import { StudyReportViewer } from "@/components/study-report-viewer";
import { annotateDocument, getDocument, parseDocument } from "@/lib/api";
import { DocumentDetail } from "@/types";

function toHeadingId(text: string) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function reportSectionTitles(isZh: boolean) {
  return isZh
    ? [
        "一、先搞懂这篇文章属于什么领域",
        "二、搞懂研究问题本身",
        "三、核心概念与术语如何串起本文方法",
        "四、逐个公式拆解",
        "五、理解方法整体 pipeline",
        "六、搞懂本文和已有工作的关系",
        "七、读懂实验部分",
        "八、理解论文的假设和局限"
      ]
    : [
        "1. Understand the paper's field",
        "2. Understand the research problem",
        "3. How core concepts connect the method",
        "4. Break down formulas one by one",
        "5. Understand the overall pipeline",
        "6. Understand relation to prior work",
        "7. Read the experiment logic",
        "8. Understand assumptions and limitations"
      ];
}

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const rawId = Array.isArray(params.id) ? params.id[0] : params.id;
  const documentId = Number(rawId);
  const isInvalidDocumentId = !Number.isFinite(documentId);

  async function loadDocument() {
    if (isInvalidDocumentId) {
      setError("Invalid document id.");
      return;
    }

    const data = await getDocument(documentId);
    setDocument(data);
    setError(null);
  }

  useEffect(() => {
    if (isInvalidDocumentId) {
      setDocument(null);
      setError("Invalid document id.");
      return;
    }

    loadDocument().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load document.");
    });
  }, [documentId, isInvalidDocumentId]);

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!document) {
    return <LoadingState label="Loading document..." />;
  }

  const isZh = document.preferred_language === "zh";
  const contentWithContext = (document.annotated_markdown ?? "")
    .replace(/\/concepts\/(\d+)(?!\?documentId=)/g, `/concepts/$1?documentId=${document.id}`)
    .replace(/\/keywords\/(\d+)(?!\?documentId=)/g, `/keywords/$1?documentId=${document.id}`);
  const keywordLinks = document.keyword_links ?? [];
  const maxKeywordDepth = document.max_keyword_depth ?? 10;
  const sectionTitles = document.study_report
    ? reportSectionTitles(isZh)
    : Array.from((document.markdown_content ?? "").matchAll(/^##\s+(.+)$/gm), (match) => match[1].trim());

  return (
    <PageShell
      title={document.title}
      description={
        isZh
          ? "结构化学习笔记会在正文里标出首次出现的科研关键词；点击后进入和原论文强相关的递归概念页。"
          : "The structured report links first-occurrence research terms inline; click a term to open a paper-specific recursive concept page."
      }
      aside={
        <div className="space-y-4">
          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">{isZh ? "文档状态" : "Document status"}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <StatusBadge label={document.status} language={document.preferred_language} />
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                {isZh ? "正文关键词可跳转" : "Inline concept links"}
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">{isZh ? "阅读信息" : "Reading info"}</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-muted">{isZh ? "语言" : "Language"}</p>
                <p className="mt-1 font-medium text-ink">{isZh ? "中文" : "English"}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-muted">{isZh ? "概念链接" : "Concept links"}</p>
                <p className="mt-1 font-medium text-ink">{keywordLinks.length}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-muted">{isZh ? "递归上限" : "Depth limit"}</p>
                <p className="mt-1 font-medium text-ink">{maxKeywordDepth}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-muted">{isZh ? "文档 ID" : "Document ID"}</p>
                <p className="mt-1 font-medium text-ink">{document.id}</p>
              </div>
            </div>
            <p className="mt-4 break-all text-sm text-muted">{document.source_file}</p>
            <Link href="/mastered" className="mt-4 inline-block text-sm">
              {isZh ? "查看已掌握概念" : "View mastered concepts"}
            </Link>
          </div>

          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">{isZh ? "重新生成" : "Rebuild document"}</p>
            <p className="mt-3 text-sm text-muted">
              {isZh
                ? "重新解析会生成 8 个核心部分，并重新创建正文中的首次出现概念链接。"
                : "Rebuild regenerates the 8 core sections and recreates first-occurrence inline concept links."}
            </p>
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                setRefreshMessage(null);
                setError(null);
                startTransition(async () => {
                  try {
                    setRefreshMessage(isZh ? "正在重新生成学习笔记..." : "Rebuilding study report...");
                    await parseDocument(document.id);
                    setRefreshMessage(isZh ? "正在重新创建概念链接..." : "Re-creating concept links...");
                    await annotateDocument(document.id);
                    await loadDocument();
                    setRefreshMessage(isZh ? "当前文档已重新生成。" : "The document has been rebuilt.");
                  } catch (err) {
                    setError(err instanceof Error ? err.message : isZh ? "重新解析失败。" : "Rebuild failed.");
                  }
                });
              }}
              className="mt-4 rounded-xl border border-line bg-white px-4 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? (isZh ? "处理中..." : "Processing...") : isZh ? "重新解析当前文档" : "Re-parse this document"}
            </button>
            {refreshMessage ? <p className="mt-3 text-sm text-muted">{refreshMessage}</p> : null}
          </div>

          {sectionTitles.length > 0 ? (
            <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
              <p className="text-xs uppercase tracking-[0.12em] text-muted">{isZh ? "章节导航" : "Section outline"}</p>
              <div className="mt-4 space-y-2">
                {sectionTitles.slice(0, 8).map((title) => (
                  <a
                    key={title}
                    href={`#${toHeadingId(title)}`}
                    className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    {title}
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      }
    >
      {document.annotated_markdown ? (
        <div className="rounded-[28px] border border-line bg-white px-8 py-8 shadow-sm md:px-12">
          <MarkdownViewer content={contentWithContext} variant="document" />
        </div>
      ) : document.study_report ? (
        <StudyReportViewer report={document.study_report} keywordLinks={keywordLinks} />
      ) : (
        <div className="rounded-xl border border-line bg-panel p-6 text-sm text-muted">
          {isZh ? "当前还没有可展示的文档内容。" : "No document content available yet."}
        </div>
      )}
    </PageShell>
  );
}

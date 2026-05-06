"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ErrorState } from "@/components/error-state";
import { KeywordPageViewer } from "@/components/keyword-page-viewer";
import { LoadingState } from "@/components/loading-state";
import { MarkdownViewer } from "@/components/markdown-viewer";
import { PageShell } from "@/components/page-shell";
import { getKeyword, retryKeyword } from "@/lib/api";
import { KeywordDetail } from "@/types";

export default function KeywordPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const [keyword, setKeyword] = useState<KeywordDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, startRetry] = useTransition();

  const rawKeywordId = Array.isArray(params.id) ? params.id[0] : params.id;
  const keywordId = Number(rawKeywordId);
  const isInvalidKeywordId = !Number.isFinite(keywordId);

  const documentIdParam = searchParams.get("documentId");
  const parsedDocumentId = documentIdParam ? Number(documentIdParam) : undefined;
  const documentId = Number.isFinite(parsedDocumentId) ? parsedDocumentId : undefined;

  async function loadKeyword() {
    if (isInvalidKeywordId) {
      setError("Invalid keyword id.");
      return;
    }

    const data = await getKeyword(keywordId, documentId);
    setKeyword(data);
    setError(null);
  }

  useEffect(() => {
    if (isInvalidKeywordId) {
      setKeyword(null);
      setError("Invalid keyword id.");
      return;
    }

    setKeyword(null);
    setError(null);

    loadKeyword().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load keyword.");
    });
  }, [keywordId, documentId, isInvalidKeywordId]);

  function retryGeneration() {
    if (isInvalidKeywordId) {
      setError("Invalid keyword id.");
      return;
    }

    setError(null);

    startRetry(async () => {
      try {
        const data = await retryKeyword(keywordId, documentId);
        setKeyword(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to retry keyword generation.");
      }
    });
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!keyword) {
    return <LoadingState label="Generating keyword note..." />;
  }

  const effectiveDocumentId = documentId ?? keyword.paper_id;
  const documentHref = `/documents/${effectiveDocumentId}`;

  const contentWithContext = (keyword.annotated_markdown ?? "").replace(
    /\/keywords\/(\d+)(?!\?documentId=)/g,
    `/keywords/$1?documentId=${effectiveDocumentId}`
  );

  return (
    <PageShell
      title={keyword.keyword}
      description={`Paper-specific recursive keyword note. Level ${keyword.level}/${keyword.max_depth}.`}
      aside={
        <div className="space-y-4">
          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">Learning path</p>
            <Link href={documentHref} className="mt-3 inline-block text-sm">
              Back to paper note
            </Link>
            <p className="mt-3 text-sm text-muted">
              Level {keyword.level}/{keyword.max_depth}
            </p>
            <p className="mt-2 text-sm text-muted">Keyword type: {keyword.keyword_type}</p>
            {keyword.depth_limit_reached ? (
              <p className="mt-2 text-sm text-amber-700">This branch has reached the recursion limit.</p>
            ) : null}
          </div>

          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">Generation status</p>
            <p className="mt-3 text-sm text-muted">{keyword.generation_status}</p>
            {keyword.generation_status === "error" ? (
              <button
                type="button"
                disabled={retrying}
                onClick={retryGeneration}
                className="mt-4 rounded-xl border border-line bg-white px-4 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-60"
              >
                {retrying ? "Retrying..." : "Retry generation"}
              </button>
            ) : null}
          </div>

          {keyword.keyword_links.length > 0 ? (
            <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
              <p className="text-xs uppercase tracking-[0.12em] text-muted">Next keywords</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {keyword.keyword_links.map((link) => (
                  <Link key={link.keyword_id} href={link.href} className="rounded-full border border-line px-3 py-1 text-sm">
                    {link.keyword}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      }
    >
      {keyword.generation_status === "error" ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-900">
          <p className="font-medium">Keyword generation failed.</p>
          <p className="mt-2 whitespace-pre-wrap">
            {keyword.error_message || "The model/API did not return a usable keyword note."}
          </p>
          <button
            type="button"
            disabled={retrying}
            onClick={retryGeneration}
            className="mt-4 rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm text-rose-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {retrying ? "Retrying..." : "Retry generation"}
          </button>
        </div>
      ) : keyword.explanation_content ? (
        <KeywordPageViewer keyword={keyword} documentId={effectiveDocumentId} />
      ) : (
        <MarkdownViewer content={contentWithContext || "No keyword note available yet."} variant="concept" />
      )}
    </PageShell>
  );
}

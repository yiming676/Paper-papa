"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ConceptPageViewer } from "@/components/concept-page-viewer";
import { ErrorState } from "@/components/error-state";
import { ExpandButton } from "@/components/expand-button";
import { LoadingState } from "@/components/loading-state";
import { MarkdownViewer } from "@/components/markdown-viewer";
import { PageShell } from "@/components/page-shell";
import { StateButtons } from "@/components/state-buttons";
import { StatusBadge } from "@/components/status-badge";
import { getConcept } from "@/lib/api";
import { ConceptDetail, ConceptState } from "@/types";

export default function ConceptPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const [concept, setConcept] = useState<ConceptDetail | null>(null);
  const [state, setState] = useState<ConceptState>("unknown");
  const [markdown, setMarkdown] = useState("");
  const [error, setError] = useState<string | null>(null);

  const rawConceptId = Array.isArray(params.id) ? params.id[0] : params.id;
  const conceptId = Number(rawConceptId);
  const isInvalidConceptId = !Number.isFinite(conceptId);

  const documentIdParam = searchParams.get("documentId");
  const parsedDocumentId = documentIdParam ? Number(documentIdParam) : undefined;
  const documentId = Number.isFinite(parsedDocumentId) ? parsedDocumentId : undefined;

  async function loadConcept() {
    if (isInvalidConceptId) {
      setError("Invalid concept id.");
      return;
    }

    const data = await getConcept(conceptId, documentId);
    setConcept(data);
    setState(data.state);
    setMarkdown(data.concept_page_markdown);
    setError(null);
  }

  useEffect(() => {
    if (isInvalidConceptId) {
      setConcept(null);
      setError("Invalid concept id.");
      return;
    }

    setConcept(null);
    setError(null);

    loadConcept().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load concept.");
    });
  }, [conceptId, documentId, isInvalidConceptId]);

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!concept) {
    return <LoadingState label="Loading concept..." />;
  }

  const isZh = concept.output_language === "zh";
  const depth = concept.concept_page?.depth ?? 1;
  const maxDepth = concept.concept_page?.max_depth ?? 10;
  const effectiveDocumentId = documentId ?? concept.related_document_ids[0];

  const contentWithContext = effectiveDocumentId
    ? markdown.replace(/\/concepts\/(\d+)(?!\?documentId=)/g, `/concepts/$1?documentId=${effectiveDocumentId}`)
    : markdown;

  return (
    <PageShell
      title={concept.canonical_name}
      description={isZh ? `概念类型：${concept.concept_type}` : `Concept type: ${concept.concept_type}`}
      aside={
        <div className="space-y-4">
          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.12em] text-muted">{isZh ? "学习状态" : "Learning state"}</p>
            <div className="mt-3">
              <StatusBadge label={state} language={concept.output_language} />
            </div>
            <div className="mt-4">
              <StateButtons
                conceptId={concept.id}
                currentState={state}
                language={concept.output_language}
                onUpdated={setState}
              />
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-white/90 p-5 text-sm text-muted shadow-sm">
            <p>
              {isZh
                ? `关联文档：${concept.related_document_ids.length || 0}`
                : `Related documents: ${concept.related_document_ids.length || 0}`}
            </p>
            <p className="mt-2">{isZh ? "输出语言：中文" : "Language: English"}</p>
            <p className="mt-2">{isZh ? `当前深度：第 ${depth}/${maxDepth} 层` : `Depth: ${depth}/${maxDepth}`}</p>
            {concept.depth_limit_reached ? (
              <p className="mt-2 text-amber-700">
                {isZh ? "该分支已到递归上限。" : "This branch has reached the recursion limit."}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {concept.related_document_ids.map((relatedDocumentId) => (
                <Link
                  key={relatedDocumentId}
                  href={`/documents/${relatedDocumentId}`}
                  className="rounded-full border border-line px-3 py-1"
                >
                  {isZh ? `文档 ${relatedDocumentId}` : `Document ${relatedDocumentId}`}
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-sm">
            <p className="mb-3 text-xs uppercase tracking-[0.12em] text-muted">
              {isZh ? "递归概念" : "Recursive concepts"}
            </p>
            <ExpandButton
              conceptId={concept.id}
              documentId={effectiveDocumentId}
              language={concept.output_language}
              onExpanded={() => {
                loadConcept().catch((err) => setError(err instanceof Error ? err.message : "Failed to refresh concept."));
              }}
            />
          </div>
        </div>
      }
    >
      {concept.concept_page ? (
        <ConceptPageViewer concept={concept} documentId={effectiveDocumentId} />
      ) : (
        <MarkdownViewer content={contentWithContext} variant="concept" />
      )}
    </PageShell>
  );
}

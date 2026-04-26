"use client";

import Link from "next/link";

import { LinkedText, TextLinkTarget } from "@/components/linked-text";
import { ConceptDetail } from "@/types";

export function ConceptPageViewer({ concept, documentId }: { concept: ConceptDetail; documentId?: number }) {
  const page = concept.concept_page;
  const isZh = concept.output_language === "zh";
  const suffix = documentId ? `?documentId=${documentId}` : "";
  const targets: TextLinkTarget[] = concept.prerequisites.map((item) => ({
    key: String(item.id),
    href: `/concepts/${item.id}${suffix}`,
    terms: [item.canonical_name, ...item.aliases]
  }));
  const usedTargets = new Set<string>();

  if (!page) {
    return null;
  }

  return (
    <article className="prose-paper">
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
          {isZh ? `第 ${page.depth}/${page.max_depth} 层` : `Depth ${page.depth}/${page.max_depth}`}
        </span>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">{page.concept_type}</span>
        {page.depth_limit_reached ? (
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">
            {isZh ? "已到递归上限" : "Depth limit reached"}
          </span>
        ) : null}
      </div>

      {concept.learning_path.length > 1 ? (
        <nav className="mb-6 rounded-lg border border-line bg-slate-50 p-3 text-sm text-muted">
          {concept.learning_path.map((item, index) => (
            <span key={item.id}>
              {index > 0 ? <span className="mx-2">/</span> : null}
              <Link href={`/concepts/${item.id}${suffix}`}>{item.canonical_name}</Link>
            </span>
          ))}
        </nav>
      ) : null}

      <section className="rounded-lg border border-line bg-emerald-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-800">
          {isZh ? "一句话解释" : "One-line explanation"}
        </p>
        <p className="mt-2 text-lg leading-8 text-ink">
          <LinkedText text={page.one_line_explanation} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>

      <section className="report-section">
        <h2 className="document-heading">{isZh ? "直觉理解" : "Intuition"}</h2>
        <p className="document-copy">
          <LinkedText text={page.intuition} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>

      <section className="report-section">
        <h2 className="document-heading">{isZh ? "在本文中的作用" : "Role in this paper"}</h2>
        <p className="document-copy">
          <LinkedText text={page.role_in_this_paper} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>

      <section className="report-section">
        <h2 className="document-heading">{isZh ? "严格定义" : "Strict definition"}</h2>
        <p className="document-copy">
          <LinkedText text={page.strict_definition} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>

      <section className="report-section">
        <h2 className="document-heading">{isZh ? "前置概念" : "Prerequisites"}</h2>
        {concept.prerequisites.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {concept.prerequisites.map((item) => (
              <Link
                key={item.id}
                href={`/concepts/${item.id}${suffix}`}
                className="rounded-lg border border-line bg-white p-4 text-sm font-medium text-accent no-underline hover:bg-slate-50"
              >
                {item.canonical_name}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">{isZh ? "暂无必要前置概念。" : "No required prerequisites yet."}</p>
        )}
      </section>

      <section className="report-section">
        <h2 className="document-heading">{isZh ? "示例" : "Example"}</h2>
        <p className="document-copy">
          <LinkedText text={page.example} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>
    </article>
  );
}

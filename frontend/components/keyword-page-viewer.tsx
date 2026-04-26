"use client";

import Link from "next/link";

import { LinkedText, TextLinkTarget } from "@/components/linked-text";
import { KeywordDetail } from "@/types";

function linkTargets(keyword: KeywordDetail): TextLinkTarget[] {
  return keyword.keyword_links.map((link) => ({
    key: String(link.keyword_id),
    href: link.href,
    terms: [link.raw_text, link.keyword, link.normalized_keyword, ...link.aliases]
  }));
}

function Section({
  title,
  text,
  targets,
  usedTargets
}: {
  title: string;
  text?: string | null;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
}) {
  return (
    <section className="report-section">
      <h2 className="document-heading">{title}</h2>
      <p className="document-copy">
        <LinkedText text={text || "N/A"} targets={targets} usedTargets={usedTargets} />
      </p>
    </section>
  );
}

function LearningPathMap({
  keyword,
  documentHref,
  suffix
}: {
  keyword: KeywordDetail;
  documentHref: string;
  suffix: string;
}) {
  const progress = Math.min(100, Math.max(6, (keyword.level / keyword.max_depth) * 100));
  const nodes = [
    {
      id: "paper",
      label: "原论文学习笔记",
      href: documentHref,
      level: 0,
      type: "root"
    },
    ...keyword.learning_path.map((item) => ({
      id: String(item.id),
      label: item.keyword,
      href: `/keywords/${item.id}${suffix}`,
      level: item.level,
      type: item.keyword_type
    }))
  ];

  return (
    <section className="mb-6 rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-sky-50 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-emerald-800">Recursive learning path</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">第 {keyword.level}/{keyword.max_depth} 层</h2>
        </div>
        {keyword.depth_limit_reached ? (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
            已到达递归上限
          </span>
        ) : (
          <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-medium text-emerald-800">
            还可继续展开
          </span>
        )}
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white ring-1 ring-emerald-100">
        <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
      </div>

      <div className="mt-5 overflow-x-auto pb-1">
        <ol className="flex min-w-max items-center gap-2">
          {nodes.map((node, index) => {
            const isCurrent = index === nodes.length - 1;
            return (
              <li key={node.id} className="flex items-center gap-2">
                {index > 0 ? <span className="h-px w-8 bg-emerald-200" /> : null}
                <Link
                  href={node.href}
                  aria-current={isCurrent ? "page" : undefined}
                  className={
                    isCurrent
                      ? "rounded-xl border border-emerald-400 bg-emerald-600 px-4 py-3 text-sm font-semibold text-white no-underline shadow-sm hover:bg-emerald-700"
                      : "rounded-xl border border-line bg-white px-4 py-3 text-sm font-medium text-slate-700 no-underline shadow-sm hover:border-emerald-300 hover:bg-emerald-50"
                  }
                >
                  <span className="block text-[11px] uppercase opacity-75">
                    {node.level === 0 ? "Paper" : `Layer ${node.level}`}
                  </span>
                  <span className="block max-w-[220px] truncate">{node.label}</span>
                </Link>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

export function KeywordPageViewer({ keyword, documentId }: { keyword: KeywordDetail; documentId?: number }) {
  const content = keyword.explanation_content;
  const targets = linkTargets(keyword);
  const usedTargets = new Set<string>();
  const documentHref = documentId ? `/documents/${documentId}` : `/documents/${keyword.paper_id}`;
  const suffix = documentId ? `?documentId=${documentId}` : "";

  if (!content) {
    return null;
  }

  return (
    <article className="prose-paper">
      <LearningPathMap keyword={keyword} documentHref={documentHref} suffix={suffix} />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
          当前第 {keyword.level}/{keyword.max_depth} 层
        </span>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">{keyword.keyword_type}</span>
        {keyword.depth_limit_reached ? (
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">Depth limit reached</span>
        ) : null}
      </div>

      <section className="rounded-lg border border-line bg-emerald-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-800">Current keyword</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">{keyword.keyword}</h1>
        {keyword.source_sentence ? <p className="mt-3 text-sm leading-6 text-slate-700">{keyword.source_sentence}</p> : null}
      </section>

      <Section title="What it means" text={content.meaning} targets={targets} usedTargets={usedTargets} />
      <Section title="What it means in this paper" text={content.paper_specific_meaning} targets={targets} usedTargets={usedTargets} />
      <Section title="Why this paper needs it" text={content.why_needed} targets={targets} usedTargets={usedTargets} />
      <Section title="Relationship to nearby concepts" text={content.relationships} targets={targets} usedTargets={usedTargets} />

      <section className="report-section">
        <h2 className="document-heading">Common misunderstandings</h2>
        {content.common_misunderstandings.length ? (
          <ul className="document-list">
            {content.common_misunderstandings.map((item, index) => (
              <li key={`${item}-${index}`}>
                <LinkedText text={item} targets={targets} usedTargets={usedTargets} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">N/A</p>
        )}
      </section>

      <Section title="Intuitive example" text={content.intuitive_example} targets={targets} usedTargets={usedTargets} />

      {keyword.keyword_links.length > 0 && !keyword.depth_limit_reached ? (
        <section className="report-section">
          <h2 className="document-heading">Continue learning</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {keyword.keyword_links.map((link) => (
              <Link
                key={link.keyword_id}
                href={link.href}
                className="rounded-lg border border-line bg-white p-4 text-sm font-medium text-accent no-underline hover:bg-slate-50"
              >
                {link.keyword}
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </article>
  );
}

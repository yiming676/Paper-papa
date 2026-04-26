"use client";

import Link from "next/link";
import { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

function flattenChildren(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number") {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children.map(flattenChildren).join("");
  }
  if (children && typeof children === "object" && "props" in children) {
    return flattenChildren((children as { props?: { children?: ReactNode } }).props?.children ?? "");
  }
  return "";
}

function toHeadingId(children: ReactNode): string {
  const text = flattenChildren(children).trim().toLowerCase();
  return text
    .replace(/[^\w\u4e00-\u9fff\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function wrapInlineLatexSegment(segment: string): string {
  const math: string[] = [];
  const stash = (value: string) => {
    const index = math.push(value) - 1;
    return `@@LATEX_${index}@@`;
  };

  let output = segment
    .replace(/\\\|[^，。；;:：\n]+?\\\|(?:[_^]\{?[A-Za-z0-9]+\}?)?/g, stash)
    .replace(/\\[A-Za-z]+(?:\{[^{}]+\})?(?:[_^]\{?[A-Za-z0-9]+\}?)*(?:\([A-Za-z0-9_{}\\, ]+\))?/g, stash)
    .replace(/\b[A-Za-z](?:[_^]\{?[A-Za-z0-9]+\}?)+(?:\([A-Za-z0-9_{}\\, ]+\))?/g, stash);

  output = output.replace(/@@LATEX_(\d+)@@/g, (_, index) => `$${math[Number(index)]}$`);
  return output;
}

function normalizeInlineLatex(content: string): string {
  let inCodeFence = false;
  let inDisplayMath = false;
  const protectedPattern = /(`[^`]*`|\[[^\]]+\]\([^)]+\)|\$[^$\n]+\$)/g;

  return content
    .split("\n")
    .map((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith("```")) {
        inCodeFence = !inCodeFence;
        return line;
      }
      if (trimmed.startsWith("$$")) {
        inDisplayMath = !inDisplayMath;
        return line;
      }
      if (inCodeFence || inDisplayMath) {
        return line;
      }

      return line
        .split(protectedPattern)
        .map((part) => {
          if (!part || protectedPattern.test(part)) {
            protectedPattern.lastIndex = 0;
            return part;
          }
          protectedPattern.lastIndex = 0;
          return wrapInlineLatexSegment(part);
        })
        .join("");
    })
    .join("\n");
}

export function MarkdownViewer({
  content,
  variant = "document"
}: {
  content: string;
  variant?: "document" | "concept";
}) {
  const isConcept = variant === "concept";
  const normalizedContent = normalizeInlineLatex(content);

  return (
    <div className="prose-paper">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          h1({ children }) {
            return isConcept ? (
              <h1>{children}</h1>
            ) : (
              <h1 id={toHeadingId(children)} className="document-title">
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return isConcept ? (
              <section className="mt-8">
                <h2 className="section-heading">{children}</h2>
              </section>
            ) : (
              <h2 id={toHeadingId(children)} className="document-heading">
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return isConcept ? (
              <h3>{children}</h3>
            ) : (
              <h3 id={toHeadingId(children)} className="document-subheading">
                {children}
              </h3>
            );
          },
          p({ children }) {
            return isConcept ? <p className="section-copy">{children}</p> : <p className="document-copy">{children}</p>;
          },
          ul({ children }) {
            return isConcept ? <ul className="section-list">{children}</ul> : <ul className="document-list">{children}</ul>;
          },
          table({ children }) {
            return (
              <div className="my-5 overflow-x-auto rounded-lg border border-line bg-white">
                <table className="w-full min-w-[720px] table-fixed border-collapse text-sm">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return <th className="break-words border border-line bg-slate-50 px-3 py-2 text-left align-top">{children}</th>;
          },
          td({ children }) {
            return <td className="whitespace-pre-wrap break-words border border-line px-3 py-2 align-top leading-6">{children}</td>;
          },
          ol({ children }) {
            return isConcept ? <ol>{children}</ol> : <ol className="document-list">{children}</ol>;
          },
          blockquote({ children }) {
            return isConcept ? <blockquote>{children}</blockquote> : <blockquote className="document-quote">{children}</blockquote>;
          },
          hr() {
            return isConcept ? <hr /> : <hr className="document-divider" />;
          },
          a({ href, children }) {
            if (href?.startsWith("/")) {
              return (
                <Link href={href} className={isConcept ? "concept-link" : "document-entity-link"}>
                  {children}
                </Link>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" className={isConcept ? "concept-link" : "document-entity-link"}>
                {children}
              </a>
            );
          },
          img({ src, alt }) {
            return (
              <img
                src={src ?? ""}
                alt={alt ?? ""}
                className="my-4 max-h-[560px] w-auto max-w-full rounded-lg border border-line object-contain"
              />
            );
          }
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}

export function InlineMathMarkdown({ content }: { content: string }) {
  return (
    <span className="inline-block align-middle">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          p({ children }) {
            return <>{children}</>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </span>
  );
}

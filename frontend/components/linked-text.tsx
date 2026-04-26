"use client";

import Link from "next/link";
import { ReactNode } from "react";

export interface TextLinkTarget {
  key: string;
  href: string;
  terms: string[];
}

function isWordChar(value: string) {
  return /[A-Za-z0-9_]/.test(value);
}

function findTerm(text: string, term: string, from: number) {
  const lowerText = text.toLowerCase();
  const lowerTerm = term.toLowerCase();
  let index = lowerText.indexOf(lowerTerm, from);
  const termNeedsBoundary = /^[A-Za-z0-9_]/.test(term) || /[A-Za-z0-9_]$/.test(term);

  while (index >= 0) {
    if (!termNeedsBoundary) {
      return index;
    }
    const before = index > 0 ? text[index - 1] : "";
    const after = index + term.length < text.length ? text[index + term.length] : "";
    if ((!before || !isWordChar(before)) && (!after || !isWordChar(after))) {
      return index;
    }
    index = lowerText.indexOf(lowerTerm, index + 1);
  }

  return -1;
}

function cleanTerms(terms: string[]) {
  return Array.from(new Set(terms.map((term) => term.trim()).filter((term) => term.length >= 2))).sort(
    (a, b) => b.length - a.length
  );
}

export function LinkedText({
  text,
  targets,
  usedTargets,
  className
}: {
  text?: string | null;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
  className?: string;
}) {
  const value = text || "N/A";
  const nodes: ReactNode[] = [];
  let cursor = 0;

  while (cursor < value.length) {
    let best:
      | {
          target: TextLinkTarget;
          start: number;
          term: string;
        }
      | null = null;

    for (const target of targets) {
      if (usedTargets.has(target.key)) {
        continue;
      }
      for (const term of cleanTerms(target.terms)) {
        const start = findTerm(value, term, cursor);
        if (start < 0) {
          continue;
        }
        if (!best || start < best.start || (start === best.start && term.length > best.term.length)) {
          best = { target, start, term };
        }
      }
    }

    if (!best) {
      nodes.push(value.slice(cursor));
      break;
    }

    if (best.start > cursor) {
      nodes.push(value.slice(cursor, best.start));
    }
    const end = best.start + best.term.length;
    const label = value.slice(best.start, end);
    usedTargets.add(best.target.key);
    nodes.push(
      <Link key={`${best.target.key}-${best.start}`} href={best.target.href} className="document-entity-link">
        {label}
      </Link>
    );
    cursor = end;
  }

  return <span className={className}>{nodes}</span>;
}

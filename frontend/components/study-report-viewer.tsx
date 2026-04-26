"use client";

import { ReactNode } from "react";

import { LinkedText, TextLinkTarget } from "@/components/linked-text";
import { MarkdownViewer } from "@/components/markdown-viewer";
import {
  DocumentConceptLink,
  FormulaBreakdown,
  PaperReference,
  PipelineModule,
  RelatedWorkComparison,
  StudyReport
} from "@/types";

function headingId(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function linkTargets(conceptLinks: DocumentConceptLink[]): TextLinkTarget[] {
  return conceptLinks.map((link) => ({
    key: String(link.concept_id),
    href: link.href,
    terms: [link.raw_text, link.canonical_name, link.normalized_text, ...link.aliases]
  }));
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="report-section">
      <h2 id={headingId(title)} className="document-heading">
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function LinkedParagraph({
  text,
  targets,
  usedTargets
}: {
  text?: string | null;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
}) {
  return (
    <p className="document-copy">
      <LinkedText text={text} targets={targets} usedTargets={usedTargets} />
    </p>
  );
}

function LinkedList({
  title,
  items,
  targets,
  usedTargets
}: {
  title?: string;
  items?: string[] | null;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
}) {
  const values = (items ?? []).filter(Boolean);
  return (
    <div>
      {title ? <h3 className="document-subheading">{title}</h3> : null}
      {values.length ? (
        <ul className="document-list">
          {values.map((item, index) => (
            <li key={`${item}-${index}`}>
              <LinkedText text={item} targets={targets} usedTargets={usedTargets} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">N/A</p>
      )}
    </div>
  );
}

function KeyValue({
  label,
  value,
  targets,
  usedTargets
}: {
  label: string;
  value?: string | null;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
}) {
  return (
    <p className="document-copy">
      <strong>{label}:</strong> <LinkedText text={value} targets={targets} usedTargets={usedTargets} />
    </p>
  );
}

function SimpleTable({
  headers,
  rows,
  targets,
  usedTargets
}: {
  headers: string[];
  rows: string[][];
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
}) {
  if (!rows.length) {
    return <p className="text-sm text-muted">N/A</p>;
  }
  return (
    <div className="my-5 overflow-x-auto rounded-lg border border-line bg-white">
      <table className="w-full min-w-[720px] table-fixed border-collapse text-sm">
        <thead className="bg-slate-50">
          <tr>
            {headers.map((header) => (
              <th key={header} className="border border-line px-3 py-2 text-left align-top">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`} className="whitespace-pre-wrap break-words border border-line px-3 py-2 align-top leading-6">
                  <LinkedText text={cell} targets={targets} usedTargets={usedTargets} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FormulaCard({
  formula,
  targets,
  usedTargets,
  isZh
}: {
  formula: FormulaBreakdown;
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
  isZh: boolean;
}) {
  return (
    <div className="rounded-lg border border-line bg-slate-50 p-4">
      <h3 className="text-lg font-semibold text-ink">
        <LinkedText text={formula.title} targets={targets} usedTargets={usedTargets} />
      </h3>
      <div className="mt-3 overflow-x-auto">
        <MarkdownViewer content={`$$\n${formula.latex || "\\text{N/A}"}\n$$`} variant="document" />
      </div>
      <KeyValue label={isZh ? "这个公式在算什么" : "What it computes"} value={formula.computes} targets={targets} usedTargets={usedTargets} />
      {formula.symbols.length ? (
        <SimpleTable
          headers={isZh ? ["符号", "含义"] : ["Symbol", "Meaning"]}
          rows={formula.symbols.map((symbol) => [symbol.symbol, symbol.meaning])}
          targets={targets}
          usedTargets={usedTargets}
        />
      ) : null}
      <KeyValue label={isZh ? "输入变量" : "Input variables"} value={formula.input_variables.join(", ")} targets={targets} usedTargets={usedTargets} />
      <KeyValue label={isZh ? "输出结果" : "Output"} value={formula.output_result} targets={targets} usedTargets={usedTargets} />
      <KeyValue label={isZh ? "服务模块" : "Served module"} value={formula.served_module} targets={targets} usedTargets={usedTargets} />
      <KeyValue label={isZh ? "代码步骤" : "Code step"} value={formula.code_step} targets={targets} usedTargets={usedTargets} />
      <KeyValue label={isZh ? "去掉后的影响" : "Removal effect"} value={formula.removal_effect} targets={targets} usedTargets={usedTargets} />
      <KeyValue label={isZh ? "设计原因" : "Design reason"} value={formula.design_reason} targets={targets} usedTargets={usedTargets} />
    </div>
  );
}

function sectionKey(reference: PaperReference) {
  const valid = new Set(["domain", "problem", "terms", "math", "pipeline", "related", "experiments", "limitations"]);
  const section = (reference.section || "").toLowerCase();
  return valid.has(section) ? section : "pipeline";
}

function groupReferences(references: PaperReference[] = []) {
  return references.reduce<Record<string, PaperReference[]>>((groups, reference) => {
    const key = sectionKey(reference);
    groups[key] = [...(groups[key] ?? []), reference];
    return groups;
  }, {});
}

function ReferenceGroup({
  references,
  targets,
  usedTargets,
  isZh
}: {
  references?: PaperReference[];
  targets: TextLinkTarget[];
  usedTargets: Set<string>;
  isZh: boolean;
}) {
  const items = (references ?? []).filter((item) => item.label);
  if (!items.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
      <p className="font-medium">{isZh ? "图表引用线索" : "Figure/Table cues"}</p>
      <ul className="mt-2 space-y-2">
        {items.slice(0, 4).map((reference, index) => {
          const page = reference.page ? ` p.${reference.page}` : "";
          const body = reference.reason || reference.caption || reference.context || "";
          return (
            <li key={`${reference.label}-${index}`}>
              <span className="font-medium">{isZh ? "参见" : "See"} {reference.label}{page}: </span>
              <LinkedText text={body || (isZh ? "回到原文对应图表查看。" : "Return to the source paper for this figure/table.")} targets={targets} usedTargets={usedTargets} />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function StudyReportViewer({
  report,
  conceptLinks
}: {
  report: StudyReport;
  conceptLinks: DocumentConceptLink[];
}) {
  const isZh = /[\u4e00-\u9fff]/.test(report.core_insight);
  const targets = linkTargets(conceptLinks);
  const usedTargets = new Set<string>();
  const referencesBySection = groupReferences(report.paper_references ?? []);
  const warnings = report.warnings ?? [];

  return (
    <article className="prose-paper">
      <h1 className="document-title">{report.title}</h1>
      <section className="rounded-lg border border-line bg-emerald-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-800">
          {isZh ? "核心洞察" : "Core insight"}
        </p>
        <p className="mt-2 text-lg leading-8 text-ink">
          <LinkedText text={report.core_insight} targets={targets} usedTargets={usedTargets} />
        </p>
      </section>

      {warnings.length ? (
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {warnings.map((warning, index) => (
            <p key={index}>{warning}</p>
          ))}
        </div>
      ) : null}

      <Section title={isZh ? "一、先搞懂这篇文章属于什么领域" : "1. Understand the paper's field"}>
        <KeyValue label={isZh ? "一级领域" : "Primary field"} value={report.domain_positioning.primary_field} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "二级方向" : "Secondary direction"} value={report.domain_positioning.secondary_direction} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "具体问题" : "Concrete problem"} value={report.domain_positioning.concrete_problem} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "问题链条" : "Problem chain"} value={report.domain_positioning.problem_chain} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.domain} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "二、搞懂研究问题本身" : "2. Understand the research problem"}>
        <KeyValue label={isZh ? "作者想解决的问题" : "Target problem"} value={report.research_problem.target_problem} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "为什么重要" : "Importance"} value={report.research_problem.importance} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "已有方法为什么不够好" : "Prior limitations"} items={report.research_problem.prior_limitations} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "输入" : "Input"} value={report.research_problem.input} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "输出" : "Output"} value={report.research_problem.output} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "评价标准" : "Evaluation criteria"} items={report.research_problem.evaluation_criteria} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.problem} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "三、核心概念与术语如何串起本文方法" : "3. How core concepts connect the method"}>
        <LinkedParagraph text={report.terminology.narrative} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.terms} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "四、逐个公式拆解" : "4. Break down formulas one by one"}>
        {report.formula_breakdowns.length ? (
          report.formula_breakdowns.map((formula) => (
            <FormulaCard key={formula.title} formula={formula} targets={targets} usedTargets={usedTargets} isZh={isZh} />
          ))
        ) : (
          <p className="text-sm text-muted">N/A</p>
        )}
        <ReferenceGroup references={referencesBySection.math} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "五、理解方法整体 pipeline" : "5. Understand the overall pipeline"}>
        <div className="rounded-lg border border-line bg-slate-50 p-4 font-mono text-sm text-slate-800">{report.pipeline.text_diagram || "N/A"}</div>
        <KeyValue label={isZh ? "数据来源" : "Data source"} value={report.pipeline.data_source} targets={targets} usedTargets={usedTargets} />
        <SimpleTable
          headers={isZh ? ["模块", "输入", "输出", "作用", "来源"] : ["Module", "Input", "Output", "Role", "Source"]}
          rows={report.pipeline.modules.map((module: PipelineModule) => [module.name, module.input, module.output, module.role, module.source_type])}
          targets={targets}
          usedTargets={usedTargets}
        />
        <LinkedList title={isZh ? "模块连接" : "Module connections"} items={report.pipeline.connections} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "已有方法" : "Existing methods"} items={report.pipeline.existing_methods} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "本文创新" : "Innovations"} items={report.pipeline.innovations} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "工程实现" : "Engineering details"} items={report.pipeline.engineering_details} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.pipeline} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "六、搞懂本文和已有工作的关系" : "6. Understand relation to prior work"}>
        <LinkedList title="Baseline" items={report.related_work.baselines} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "继承对象" : "Inherited from"} items={report.related_work.inherited_from} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "改进对象" : "Improved from"} items={report.related_work.improved_from} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "最大区别" : "Key difference"} value={report.related_work.key_difference} targets={targets} usedTargets={usedTargets} />
        <SimpleTable
          headers={isZh ? ["方法", "核心思想", "优点", "缺点", "本文如何改进"] : ["Method", "Core idea", "Strengths", "Weaknesses", "Paper improvement"]}
          rows={report.related_work.comparison_table.map((item: RelatedWorkComparison) => [
            item.method,
            item.core_idea,
            item.strengths,
            item.weaknesses,
            item.how_this_paper_improves
          ])}
          targets={targets}
          usedTargets={usedTargets}
        />
        <ReferenceGroup references={referencesBySection.related} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "七、读懂实验部分" : "7. Read the experiment logic"}>
        <SimpleTable
          headers={isZh ? ["数据集", "选择原因"] : ["Dataset", "Reason"]}
          rows={report.experiments.datasets.map((item) => [item.name, item.reason])}
          targets={targets}
          usedTargets={usedTargets}
        />
        <LinkedList title={isZh ? "比较方法" : "Compared methods"} items={report.experiments.compared_methods} targets={targets} usedTargets={usedTargets} />
        <SimpleTable
          headers={isZh ? ["指标", "含义", "代表能力"] : ["Metric", "Meaning", "Capability"]}
          rows={report.experiments.metrics.map((item) => [item.name, item.meaning, item.capability])}
          targets={targets}
          usedTargets={usedTargets}
        />
        <LinkedList title={isZh ? "主实验" : "Main results"} items={report.experiments.main_results} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "消融实验" : "Ablations"} items={report.experiments.ablation_results} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "可视化结果" : "Visualizations"} items={report.experiments.visualization_results} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "失败案例" : "Failure cases"} items={report.experiments.failure_cases} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "结论是否充分" : "Conclusion support"} value={report.experiments.conclusion_support} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.experiments} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>

      <Section title={isZh ? "八、理解论文的假设和局限" : "8. Understand assumptions and limitations"}>
        <LinkedList title={isZh ? "依赖前提" : "Assumptions"} items={report.limitations.assumptions} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "适用场景" : "Works well when"} items={report.limitations.works_well_when} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "失败场景" : "May fail when"} items={report.limitations.may_fail_when} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "数据集偏差" : "Dataset bias"} value={report.limitations.dataset_bias} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "指标偏差" : "Metric bias"} value={report.limitations.metric_bias} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "计算成本" : "Compute cost"} value={report.limitations.compute_cost} targets={targets} usedTargets={usedTargets} />
        <KeyValue label={isZh ? "预处理依赖" : "Preprocessing dependency"} value={report.limitations.preprocessing_dependency} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "复现风险" : "Reproducibility risks"} items={report.limitations.reproducibility_risks} targets={targets} usedTargets={usedTargets} />
        <LinkedList title={isZh ? "隐藏工程技巧" : "Hidden engineering tricks"} items={report.limitations.hidden_engineering_tricks} targets={targets} usedTargets={usedTargets} />
        <ReferenceGroup references={referencesBySection.limitations} targets={targets} usedTargets={usedTargets} isZh={isZh} />
      </Section>
    </article>
  );
}

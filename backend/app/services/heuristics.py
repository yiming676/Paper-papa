import re
from collections import Counter

from app.core.normalization import normalize_text
from app.schemas.llm import (
    DomainPositioning,
    ExperimentDataset,
    ExperimentSection,
    FormulaBreakdown,
    LimitationSection,
    LearningKeyword,
    MetricExplanation,
    PaperReference,
    PipelineModule,
    PipelineSection,
    RelatedWorkComparison,
    RelatedWorkSection,
    ResearchProblem,
    StudyReport,
    TermExplanation,
    TerminologySection,
)
from app.schemas.llm import EntityCandidate


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "using",
    "into",
    "such",
    "their",
    "model",
    "paper",
    "result",
    "approach",
    "method",
    "task",
    "dataset",
    "figure",
    "table",
}


def basic_markdown_from_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines()]
    chunks: list[str] = []
    for line in lines:
        if not line:
            chunks.append("")
            continue
        if len(line) < 80 and line == line.upper():
            chunks.append(f"## {line.title()}")
            continue
        if re.match(r"^\d+(\.\d+)*\s+[A-Z]", line):
            chunks.append(f"## {line}")
            continue
        if re.match(r"^(abstract|introduction|method|methods|experiments|conclusion|related work)$", line.lower()):
            chunks.append(f"## {line.title()}")
            continue
        if re.search(r"=\s*.+", line) and len(line) < 120:
            chunks.append(f"$$\n{line}\n$$")
            continue
        chunks.append(line)
    return "\n\n".join(chunks)


def extract_entities_fallback(markdown_content: str) -> list[EntityCandidate]:
    candidates: list[EntityCandidate] = []
    seen: set[tuple[str, str]] = set()

    term_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3}|[a-z]+(?:\s+[a-z]+){1,3})\b")
    parameter_pattern = re.compile(
        r"\b([A-Za-z][A-Za-z\- ]{2,40}?)\s+([A-Za-z\u03b1-\u03c9\u0391-\u03a9])\b"
    )
    formula_pattern = re.compile(r"(\$[^$]+\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|[A-Za-z0-9_]+\s*=\s*[^,\n]+)")

    word_counter = Counter(re.findall(r"\b[a-zA-Z][a-zA-Z\-]{2,}\b", markdown_content.lower()))

    for match in formula_pattern.finditer(markdown_content):
        raw = match.group(1).strip()
        normalized = normalize_text(raw.replace("$", ""))
        key = (normalized, "formula")
        if normalized and key not in seen:
            seen.add(key)
            candidates.append(
                EntityCandidate(
                    text=raw,
                    type="formula",
                    normalized=normalized,
                    reason="Formula-like expression detected in the paper.",
                )
            )

    for match in parameter_pattern.finditer(markdown_content):
        phrase = " ".join(match.group(1).split())
        symbol = match.group(2).strip()
        if len(symbol) != 1:
            continue
        if phrase.lower() in STOPWORDS:
            continue
        combined = f"{phrase} {symbol}"
        normalized = normalize_text(combined)
        if len(phrase.split()) < 2:
            continue
        key = (normalized, "parameter")
        if key not in seen:
            seen.add(key)
            candidates.append(
                EntityCandidate(
                    text=combined,
                    type="parameter",
                    normalized=normalized,
                    reason="Parameter phrase paired with a symbol in context.",
                )
            )

    for match in term_pattern.finditer(markdown_content):
        raw = " ".join(match.group(1).split())
        normalized = normalize_text(raw)
        tokens = normalized.split()
        if len(tokens) < 2:
            continue
        if any(token in STOPWORDS for token in tokens):
            continue
        if sum(word_counter.get(token, 0) for token in tokens) < 2:
            continue
        key = (normalized, "term")
        if key not in seen:
            seen.add(key)
            candidates.append(
                EntityCandidate(
                    text=raw,
                    type="term",
                    normalized=normalized,
                    reason="Multi-word technical phrase extracted from the document.",
                )
            )

    return candidates[:30]


def infer_prerequisites_fallback(markdown_content: str) -> list[str]:
    phrases = re.findall(r"\b[a-zA-Z]+(?:\s+[a-zA-Z]+){1,3}\b", markdown_content)
    results: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        normalized = normalize_text(phrase)
        if len(normalized.split()) < 2:
            continue
        if normalized in seen:
            continue
        if any(word in STOPWORDS for word in normalized.split()):
            continue
        seen.add(normalized)
        results.append(phrase.strip())
        if len(results) >= 5:
            break
    return results


def _language_labels(output_language: str) -> dict[str, str]:
    if output_language == "zh":
        return {
            "core": "核心洞察",
            "domain": "一、先搞懂这篇文章属于什么领域",
            "problem": "二、搞懂研究问题本身",
            "terms": "三、核心概念与术语如何串起本文方法",
            "formulas": "四、逐个公式拆解",
            "pipeline": "五、理解方法整体 pipeline",
            "related": "六、搞懂本文和已有工作的关系",
            "experiments": "七、读懂实验部分",
            "limitations": "八、理解论文的假设和局限",
        }
    return {
        "core": "Core insight",
        "domain": "1. Understand the paper's field",
        "problem": "2. Understand the research problem",
        "terms": "3. How core concepts connect the method",
        "formulas": "4. Break down formulas one by one",
        "pipeline": "5. Understand the overall pipeline",
        "related": "6. Understand relation to prior work",
        "experiments": "7. Read the experiment logic",
        "limitations": "8. Understand assumptions and limitations",
    }


def _first_sentence(text: str, fallback: str) -> str:
    cleaned = " ".join(text.split())
    match = re.search(r"(.{40,280}?[.!?。])\s", cleaned + " ")
    if match:
        return match.group(1).strip()
    return fallback


def _section_excerpt(raw_text: str, section_name: str, max_chars: int = 900) -> str:
    pattern = re.compile(rf"\b{re.escape(section_name)}\b\s*\n(?P<body>[\s\S]{{0,{max_chars}}})", re.IGNORECASE)
    match = pattern.search(raw_text)
    if match:
        return " ".join(match.group("body").split())[:max_chars]
    return ""


def _detect_aliases(raw_text: str) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    pattern = re.compile(r"\b([A-Z0-9][A-Za-z0-9\- ]{5,80})\s*\(([A-Z0-9][A-Z0-9]{1,12})\)")
    for full_name, short_name in pattern.findall(raw_text):
        full = " ".join(full_name.split()).strip()
        short = short_name.strip()
        aliases.setdefault(full, [])
        if short not in aliases[full]:
            aliases[full].append(short)
        aliases.setdefault(short, [])
        if full not in aliases[short]:
            aliases[short].append(full)
    return aliases


def extract_learning_keywords_fallback(raw_text: str, limit: int = 24, output_language: str = "en") -> list[LearningKeyword]:
    alias_map = _detect_aliases(raw_text)
    candidates = extract_entities_fallback(basic_markdown_from_text(raw_text))
    keywords: list[LearningKeyword] = []
    seen: set[tuple[str, str]] = set()

    for name, aliases in sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True):
        if " " not in name and any(" " in alias for alias in aliases):
            continue
        normalized = normalize_text(name)
        key = (normalized, "term")
        if key in seen:
            continue
        seen.add(key)
        first_index = raw_text.lower().find(name.lower())
        excerpt = ""
        if first_index >= 0:
            start = max(0, first_index - 80)
            end = min(len(raw_text), first_index + len(name) + 140)
            excerpt = " ".join(raw_text[start:end].split())
        keywords.append(
            LearningKeyword(
                text=name,
                type="term",
                normalized=normalized,
                aliases=sorted(set(aliases)),
                difficulty="beginner",
                reason=(
                    "从论文中检测到的缩写或规范技术术语，新手需要先理解它与全文方法的关系。"
                    if output_language == "zh"
                    else "Abbreviation or canonical technical term detected from the paper."
                ),
                first_occurrence=excerpt,
                confidence=0.7,
            )
        )
        if len(keywords) >= limit:
            return keywords

    for candidate in candidates:
        normalized = normalize_text(candidate.normalized or candidate.text)
        key = (normalized, candidate.type)
        if key in seen:
            continue
        seen.add(key)
        first_index = raw_text.lower().find(candidate.text.lower())
        excerpt = ""
        if first_index >= 0:
            start = max(0, first_index - 80)
            end = min(len(raw_text), first_index + len(candidate.text) + 140)
            excerpt = " ".join(raw_text[start:end].split())
        aliases = sorted(set(alias_map.get(candidate.text, []) + alias_map.get(normalized, [])))
        keywords.append(
            LearningKeyword(
                text=candidate.text.strip(),
                type=candidate.type,
                normalized=normalized,
                aliases=aliases,
                difficulty="beginner" if candidate.type == "term" else "intermediate",
                reason=(
                    "从论文文本中检测到的关键学习实体，新手理解论文方法或公式前需要掌握。"
                    if output_language == "zh"
                    else candidate.reason
                ),
                first_occurrence=excerpt,
                confidence=0.55,
            )
        )
        if len(keywords) >= limit:
            break

    return keywords


def build_study_report_fallback(
    raw_text: str,
    title: str,
    output_language: str = "en",
    paper_references: list[PaperReference] | None = None,
    research_context: str | None = None,
) -> StudyReport:
    abstract = _section_excerpt(raw_text, "abstract") or raw_text[:1200]
    intro = _section_excerpt(raw_text, "introduction") or abstract
    method = (
        _section_excerpt(raw_text, "method")
        or _section_excerpt(raw_text, "approach")
        or _section_excerpt(raw_text, "methodology")
        or raw_text[:1200]
    )
    keywords = extract_learning_keywords_fallback(raw_text, output_language=output_language)
    terms = [
        TermExplanation(
            text=keyword.text,
            type=keyword.type,
            normalized=keyword.normalized,
            aliases=keyword.aliases,
            difficulty=keyword.difficulty,
            what_it_is=keyword.reason,
            problem_solved=(
                "帮助读者补齐理解论文主线所需的背景知识。"
                if output_language == "zh"
                else "Helps the reader fill background needed for the paper's main line."
            ),
            role_in_paper=keyword.first_occurrence or keyword.reason,
            relationships=(
                "该术语与论文的问题设定、方法模块或评估指标相关。"
                if output_language == "zh"
                else "This term relates to the paper's problem setup, method modules, or evaluation metrics."
            ),
            first_occurrence=keyword.first_occurrence,
            confidence=keyword.confidence,
        )
        for keyword in keywords[:12]
    ]

    if output_language == "zh":
        core = _first_sentence(
            abstract,
            "本文围绕论文提出的方法建立结构化学习笔记；由于当前只能进行启发式解析，核心贡献需结合原文进一步核对。",
        )
        if not re.search(r"[\u4e00-\u9fff]", core):
            core = "本文围绕上传论文提出的方法建立结构化学习笔记；由于当前只能进行启发式解析，核心贡献需结合原文进一步核对。"
        warnings = ["模型/API 未返回可用完整 JSON，当前报告由本地启发式 fallback 生成；公式、实验和复现细节需要结合原文核对。"]
    else:
        core = _first_sentence(
            abstract,
            "This fallback report summarizes the paper structure, but detailed claims should be checked against the source PDF.",
        )
        warnings = ["The model/API did not return usable complete JSON, so this report was produced by a local heuristic fallback; formula, experiment, and limitation details require source-PDF verification."]

    if research_context and "unavailable" not in research_context.lower():
        warnings.append(research_context[:500])

    return StudyReport(
        title=title,
        paper_identity=title,
        core_insight=core,
        domain_positioning=DomainPositioning(
            primary_field="需要结合论文标题、摘要和引言判断" if output_language == "zh" else "Infer from title, abstract, and introduction",
            secondary_direction="需要结合方法章节判断" if output_language == "zh" else "Infer from the method section",
            concrete_problem="启发式解析无法保证具体问题链条完全准确" if output_language == "zh" else "Fallback parsing cannot guarantee the exact problem chain",
            problem_chain=intro[:700],
        ),
        research_problem=ResearchProblem(
            target_problem=intro[:700],
            importance="请结合摘要和引言核对作者给出的动机。" if output_language == "zh" else "Check the author's motivation in the abstract and introduction.",
            prior_limitations=[
                "启发式解析无法可靠区分所有已有方法缺陷。" if output_language == "zh" else "Fallback parsing cannot reliably separate all prior-method limitations."
            ],
            input="见原文问题设定或方法章节" if output_language == "zh" else "See the source problem setup or method section",
            output="见原文任务定义" if output_language == "zh" else "See the source task definition",
            evaluation_criteria=[
                "见实验章节指标" if output_language == "zh" else "See metrics in the experiment section"
            ],
        ),
        terminology=TerminologySection(
            narrative=(
                "本文的核心概念应放回方法主线中理解：先确认输入和输出，再看表示方式、优化目标、训练约束和实验指标如何互相支撑。"
                if output_language == "zh"
                else "Read the paper's concepts inside the method chain: identify inputs and outputs, then connect representation, objectives, training constraints, and metrics."
            ),
            basic_concepts=terms[:4],
            method_concepts=terms[4:8],
            mathematical_concepts=terms[8:10],
            engineering_concepts=terms[10:12],
        ),
        formula_breakdowns=[
            FormulaBreakdown(
                title="核心公式需回到原文核对" if output_language == "zh" else "Core formulas require source verification",
                latex="\\text{请查看原文 PDF 中的核心公式}" if output_language == "zh" else "\\text{See source equations in the PDF}",
                computes="启发式解析不会重写公式，避免错误转写。" if output_language == "zh" else "Fallback parsing avoids rewriting formulas that may be misread.",
                output_result="见原文公式定义" if output_language == "zh" else "See source equation definition",
                served_module="见方法章节" if output_language == "zh" else "See the method section",
                code_step="对应代码通常位于 loss、render、train 或 inference 步骤。" if output_language == "zh" else "Usually maps to loss, render, train, or inference code.",
                removal_effect="需要结合消融实验或原文分析判断。" if output_language == "zh" else "Judge using ablations or source analysis.",
                design_reason="需要结合作者动机和目标函数判断。" if output_language == "zh" else "Judge using the author's motivation and objective.",
            )
        ],
        pipeline=PipelineSection(
            text_diagram=(
                "输入数据 -> 特征/表示构建 -> 方法模块处理 -> 损失约束与优化 -> 输出结果"
                if output_language == "zh"
                else "Input data -> feature/representation construction -> method modules -> loss constraints and optimization -> outputs"
            ),
            data_source="见原文数据集和方法章节" if output_language == "zh" else "See dataset and method sections",
            modules=[
                PipelineModule(
                    name="主要方法模块" if output_language == "zh" else "Main method module",
                    input="论文输入" if output_language == "zh" else "paper input",
                    output="论文输出或中间表示" if output_language == "zh" else "paper output or intermediate representation",
                    role=method[:500],
                    source_type="unknown",
                )
            ],
            connections=["启发式解析只能给出主线流程，模块连接请以原文图和方法章节为准。" if output_language == "zh" else "Fallback parsing only gives the main flow; verify module connections in source figures and method text."],
        ),
        related_work=RelatedWorkSection(
            baselines=["见相关工作和实验对比表" if output_language == "zh" else "See related work and experiment comparison tables"],
            key_difference="启发式解析无法可靠判断真实创新边界。" if output_language == "zh" else "Fallback parsing cannot reliably determine the exact novelty boundary.",
            comparison_table=[
                RelatedWorkComparison(
                    method="baseline / prior work",
                    core_idea="见原文相关工作" if output_language == "zh" else "see source related work",
                    strengths="需要结合原文判断" if output_language == "zh" else "requires source verification",
                    weaknesses="需要结合原文判断" if output_language == "zh" else "requires source verification",
                    how_this_paper_improves="需要结合作者贡献描述判断" if output_language == "zh" else "requires source contribution claims",
                )
            ],
        ),
        experiments=ExperimentSection(
            datasets=[ExperimentDataset(name="见实验章节数据集" if output_language == "zh" else "See experiment datasets")],
            compared_methods=["见实验对比方法" if output_language == "zh" else "See compared methods"],
            metrics=[MetricExplanation(name="见实验指标" if output_language == "zh" else "See metrics")],
            main_results=["启发式解析无法可靠重写主实验结论。" if output_language == "zh" else "Fallback parsing cannot reliably rewrite main results."],
            conclusion_support="需要核对实验表格、消融和可视化是否足以支撑作者结论。" if output_language == "zh" else "Check whether tables, ablations, and visualizations support the claims.",
        ),
        limitations=LimitationSection(
            assumptions=["需要结合方法假设核对。" if output_language == "zh" else "Verify against method assumptions."],
            may_fail_when=["数据分布、输入质量或场景条件偏离论文设定时可能失败。" if output_language == "zh" else "May fail when data distribution, input quality, or scene conditions depart from the paper setting."],
            compute_cost="需要结合实验章节的训练/推理时间和显存信息判断。" if output_language == "zh" else "Check training/inference time and memory in the experiment section.",
            reproducibility_risks=["PDF 抽取不足时，公式和工程细节可能遗漏。" if output_language == "zh" else "Formula and engineering details may be missing when PDF extraction is weak."],
        ),
        paper_references=paper_references or [],
        supporting_tables=[],
        visual_references=[],
        learning_keywords=keywords,
        warnings=warnings,
    )


def study_report_to_markdown(report: StudyReport, output_language: str = "en") -> str:
    labels = _language_labels(output_language)
    is_zh = output_language == "zh"
    lines: list[str] = [f"# {report.title}", "", f"## {labels['core']}", report.core_insight or "N/A", ""]

    def add_list(title: str, items: list[str]) -> None:
        lines.extend([f"### {title}"])
        if items:
            lines.extend([f"- {item}" for item in items if item])
        else:
            lines.append("- N/A")
        lines.append("")

    def add_references(section: str) -> None:
        references = [
            reference
            for reference in report.paper_references
            if (reference.section or "").lower() in {section, "", "general"}
        ]
        if not references:
            return
        title = "图表引用线索" if is_zh else "Figure/Table references"
        lines.append(f"### {title}")
        for reference in references[:4]:
            page = f" p.{reference.page}" if reference.page else ""
            reason = reference.reason or reference.caption or reference.context or ""
            prefix = "参见" if is_zh else "See"
            lines.append(f"- {prefix} {reference.label}{page}: {reason}".strip())
        lines.append("")

    lines.extend(
        [
            f"## {labels['domain']}",
            f"- {'一级领域' if is_zh else 'Primary field'}: {report.domain_positioning.primary_field or 'N/A'}",
            f"- {'二级方向' if is_zh else 'Secondary direction'}: {report.domain_positioning.secondary_direction or 'N/A'}",
            f"- {'具体问题' if is_zh else 'Concrete problem'}: {report.domain_positioning.concrete_problem or 'N/A'}",
            f"- {'问题链条' if is_zh else 'Problem chain'}: {report.domain_positioning.problem_chain or 'N/A'}",
            "",
        ]
    )
    add_references("domain")

    lines.extend(
        [
            f"## {labels['problem']}",
            f"- {'作者想解决的问题' if is_zh else 'Target problem'}: {report.research_problem.target_problem or 'N/A'}",
            f"- {'为什么重要' if is_zh else 'Why it matters'}: {report.research_problem.importance or 'N/A'}",
        ]
    )
    lines.extend([f"- {'已有方法不足' if is_zh else 'Prior limitation'}: {item}" for item in report.research_problem.prior_limitations] or ["- N/A"])
    lines.extend(
        [
            f"- {'输入' if is_zh else 'Input'}: {report.research_problem.input or 'N/A'}",
            f"- {'输出' if is_zh else 'Output'}: {report.research_problem.output or 'N/A'}",
            f"- {'评价标准' if is_zh else 'Evaluation criteria'}: {', '.join(report.research_problem.evaluation_criteria) or 'N/A'}",
            "",
            f"## {labels['terms']}",
        ]
    )
    add_references("problem")

    concept_names = [
        term.text
        for group in [
            report.terminology.basic_concepts,
            report.terminology.method_concepts,
            report.terminology.experiment_concepts,
            report.terminology.mathematical_concepts,
            report.terminology.engineering_concepts,
        ]
        for term in group
        if term.text
    ]
    terminology_text = report.terminology.narrative or (
        "本文的核心概念应放回方法主线中理解。"
        if is_zh
        else "The paper's core concepts should be read inside the method chain."
    )
    if concept_names:
        suffix = (
            "这些概念包括 " + "、".join(concept_names[:10]) + "，它们应在正文语境中理解，而不是脱离论文单独背诵。"
            if is_zh
            else " Key concepts include " + ", ".join(concept_names[:10]) + "; read them in the paper context rather than as isolated glossary items."
        )
        terminology_text = f"{terminology_text}\n\n{suffix}"
    lines.extend([terminology_text, ""])
    add_references("terms")

    lines.extend([f"## {labels['formulas']}"])
    for formula in report.formula_breakdowns:
        lines.extend([f"### {formula.title}", "$$", formula.latex, "$$"])
        lines.extend(
            [
                f"- {'这个公式在算什么' if is_zh else 'What it computes'}: {formula.computes or 'N/A'}",
                f"- {'输入变量' if is_zh else 'Input variables'}: {', '.join(formula.input_variables) or 'N/A'}",
                f"- {'输出结果' if is_zh else 'Output'}: {formula.output_result or 'N/A'}",
                f"- {'服务模块' if is_zh else 'Served module'}: {formula.served_module or 'N/A'}",
                f"- {'代码步骤' if is_zh else 'Code step'}: {formula.code_step or 'N/A'}",
                f"- {'去掉后的影响' if is_zh else 'Removal effect'}: {formula.removal_effect or 'N/A'}",
                f"- {'设计原因' if is_zh else 'Design reason'}: {formula.design_reason or 'N/A'}",
            ]
        )
        if formula.symbols:
            lines.append(f"- {'符号含义' if is_zh else 'Symbols'}: " + "; ".join(f"{item.symbol}: {item.meaning}" for item in formula.symbols))
        lines.append("")
    add_references("math")

    lines.extend([f"## {labels['pipeline']}", report.pipeline.text_diagram or "N/A", ""])
    lines.append(f"- {'数据来源' if is_zh else 'Data source'}: {report.pipeline.data_source or 'N/A'}")
    for module in report.pipeline.modules:
        lines.append(f"- **{module.name}**: {module.input} -> {module.output}; {module.role}; {module.source_type}")
    lines.append("")
    add_list("模块连接" if is_zh else "Module connections", report.pipeline.connections)
    add_list("已有方法" if is_zh else "Existing methods", report.pipeline.existing_methods)
    add_list("本文创新" if is_zh else "Innovations", report.pipeline.innovations)
    add_list("工程实现" if is_zh else "Engineering details", report.pipeline.engineering_details)
    add_references("pipeline")

    lines.extend([f"## {labels['related']}"])
    add_list("Baseline", report.related_work.baselines)
    add_list("继承对象" if is_zh else "Inherited from", report.related_work.inherited_from)
    add_list("改进对象" if is_zh else "Improved from", report.related_work.improved_from)
    lines.extend([f"- {'最大区别' if is_zh else 'Key difference'}: {report.related_work.key_difference or 'N/A'}", ""])
    if report.related_work.comparison_table:
        lines.append(f"### {'方法对比' if is_zh else 'Method comparison'}")
        for item in report.related_work.comparison_table:
            lines.append(f"- **{item.method}**")
            lines.append(f"  - {'核心思想' if is_zh else 'Core idea'}: {item.core_idea or 'N/A'}")
            lines.append(f"  - {'优点' if is_zh else 'Strengths'}: {item.strengths or 'N/A'}")
            lines.append(f"  - {'缺点' if is_zh else 'Weaknesses'}: {item.weaknesses or 'N/A'}")
            lines.append(f"  - {'本文如何改进' if is_zh else 'Paper improvement'}: {item.how_this_paper_improves or 'N/A'}")
        lines.append("")
    add_references("related")

    lines.extend([f"## {labels['experiments']}"])
    add_list("数据集" if is_zh else "Datasets", [f"{item.name}: {item.reason}" for item in report.experiments.datasets])
    add_list("比较方法" if is_zh else "Compared methods", report.experiments.compared_methods)
    add_list("指标" if is_zh else "Metrics", [f"{item.name}: {item.meaning} {item.capability}".strip() for item in report.experiments.metrics])
    add_list("主实验" if is_zh else "Main results", report.experiments.main_results)
    add_list("消融实验" if is_zh else "Ablations", report.experiments.ablation_results)
    add_list("可视化结果" if is_zh else "Visualizations", report.experiments.visualization_results)
    add_list("失败案例" if is_zh else "Failure cases", report.experiments.failure_cases)
    lines.extend([f"- {'结论是否充分' if is_zh else 'Conclusion support'}: {report.experiments.conclusion_support or 'N/A'}", ""])
    add_references("experiments")

    lines.extend([f"## {labels['limitations']}"])
    add_list("依赖前提" if is_zh else "Assumptions", report.limitations.assumptions)
    add_list("适用场景" if is_zh else "Works well when", report.limitations.works_well_when)
    add_list("失败场景" if is_zh else "May fail when", report.limitations.may_fail_when)
    lines.extend(
        [
            f"- {'数据集偏差' if is_zh else 'Dataset bias'}: {report.limitations.dataset_bias or 'N/A'}",
            f"- {'指标偏差' if is_zh else 'Metric bias'}: {report.limitations.metric_bias or 'N/A'}",
            f"- {'计算成本' if is_zh else 'Compute cost'}: {report.limitations.compute_cost or 'N/A'}",
            f"- {'预处理依赖' if is_zh else 'Preprocessing dependency'}: {report.limitations.preprocessing_dependency or 'N/A'}",
        ]
    )
    add_list("复现风险" if is_zh else "Reproducibility risks", report.limitations.reproducibility_risks)
    add_list("隐藏工程技巧" if is_zh else "Hidden engineering tricks", report.limitations.hidden_engineering_tricks)
    add_references("limitations")
    return "\n".join(lines).strip()


def build_study_markdown_fallback(raw_text: str, title: str, output_language: str = "en") -> str:
    report = build_study_report_fallback(raw_text=raw_text, title=title, output_language=output_language)
    return study_report_to_markdown(report, output_language=output_language)

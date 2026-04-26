import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.llm import ConceptPageSections, EntityCandidate, LearningKeyword, PaperAsset, PaperReference, StudyReport
from app.services.heuristics import (
    build_study_markdown_fallback,
    build_study_report_fallback,
    extract_entities_fallback,
    infer_prerequisites_fallback,
    study_report_to_markdown,
)
from app.services.research_service import research_service


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
logger = logging.getLogger(__name__)


class LLMGenerationError(RuntimeError):
    pass


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_error: str | None = None

    def _load_prompt(self, name: str) -> str:
        return (PROMPT_DIR / name).read_text(encoding="utf-8")

    def _chat_completions_url(self) -> str:
        base_url = self.settings.openai_base_url.rstrip("/")
        path = self.settings.openai_chat_completions_path.strip() or "/chat/completions"
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"

    def _call_json(self, system_prompt: str, user_prompt: str) -> Any | None:
        self.last_error = None
        if not self.settings.openai_api_key:
            self.last_error = "OPENAI_API_KEY is not configured."
            logger.warning("LLM disabled: OPENAI_API_KEY is not configured.")
            return None

        url = self._chat_completions_url()
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        base_payload = {
            "model": self.settings.model_name,
            "temperature": 0.2,
            "max_tokens": self.settings.llm_max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n\n"
                        "只返回一个完整、可被 JSON.parse 解析的原始 JSON 对象。"
                        "不要输出 Markdown 代码块、解释文字、前后缀、注释或多余标点。"
                        "如果信息不足，也必须在对应字段写出不确定原因，并保持 JSON 完整闭合。"
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        }

        payloads = [dict(base_payload)]
        if self.settings.llm_json_mode:
            payloads[0]["response_format"] = {"type": "json_object"}
            payloads.append(dict(base_payload))

        last_status_error: httpx.HTTPStatusError | None = None
        for attempt, payload in enumerate(payloads, start=1):
            using_json_mode = "response_format" in payload
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=self.settings.llm_timeout_seconds)
                response.raise_for_status()
                body = response.json()
                base_resp = body.get("base_resp") if isinstance(body, dict) else None
                if isinstance(base_resp, dict) and base_resp.get("status_code") not in {None, 0}:
                    logger.warning(
                        "LLM provider returned base_resp error: url=%s model=%s status_code=%s status_msg=%s json_mode=%s",
                        url,
                        self.settings.model_name,
                        base_resp.get("status_code"),
                        base_resp.get("status_msg"),
                        using_json_mode,
                    )
                choice = body["choices"][0]
                finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
                content = choice["message"]["content"]
                parsed = self._extract_json(content)
                if parsed is None:
                    truncated_hint = " The response may have been truncated; try increasing LLM_MAX_TOKENS." if finish_reason == "length" else ""
                    self.last_error = (
                        "LLM response did not contain valid JSON "
                        f"(attempt={attempt}, json_mode={using_json_mode}, finish_reason={finish_reason}, "
                        f"chars={len(content)}).{truncated_hint} "
                        f"preview={content[:260]!r} tail={content[-260:]!r}"
                    )
                    logger.warning(
                        "LLM response did not contain valid JSON: url=%s model=%s json_mode=%s finish_reason=%s chars=%s preview=%r tail=%r",
                        url,
                        self.settings.model_name,
                        using_json_mode,
                        finish_reason,
                        len(content),
                        content[:500],
                        content[-500:],
                    )
                    continue
                return parsed
            except httpx.HTTPStatusError as exc:
                last_status_error = exc
                body_preview = exc.response.text[:500]
                self.last_error = f"LLM HTTP error {exc.response.status_code}: {body_preview}"
                logger.warning(
                    "LLM HTTP error: url=%s model=%s status=%s json_mode=%s body_preview=%r",
                    url,
                    self.settings.model_name,
                    exc.response.status_code,
                    using_json_mode,
                    body_preview,
                )
                if using_json_mode and exc.response.status_code in {400, 404, 422}:
                    logger.warning("Retrying LLM request without response_format JSON mode.")
                    continue
                return None
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                self.last_error = f"LLM network error: {repr(exc)}"
                logger.warning(
                    "LLM network error: url=%s model=%s json_mode=%s error=%s",
                    url,
                    self.settings.model_name,
                    using_json_mode,
                    repr(exc),
                )
                return None
            except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.last_error = f"LLM response schema error: {repr(exc)}"
                logger.warning(
                    "LLM response schema error: url=%s model=%s json_mode=%s error=%s",
                    url,
                    self.settings.model_name,
                    using_json_mode,
                    repr(exc),
                )
                return None
            except Exception:
                self.last_error = "Unexpected LLM request failure."
                logger.exception("Unexpected LLM request failure: url=%s model=%s json_mode=%s", url, self.settings.model_name, using_json_mode)
                return None

        if last_status_error:
            return None
        return None

    def _extract_json(self, content: str) -> Any | None:
        if not content:
            return None

        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    def _contains_cjk(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _looks_like_requested_language(self, text: str, output_language: str) -> bool:
        if output_language == "zh":
            cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
            latin_words = len(re.findall(r"\b[a-zA-Z]{3,}\b", text))
            return cjk_count > 20 and cjk_count >= latin_words
        return True

    def _language_instruction(self, output_language: str) -> str:
        if output_language == "zh":
            return (
                "输出语言：简体中文。\n"
                "强制要求：除论文标题、方法名、数据集名、公式、变量符号、专有缩写和引用标题外，"
                "所有解释性文字都必须使用严谨简体中文。英文论文也必须翻译、概括并用中文讲解，禁止整段复制英文原文。"
            )
        return "Output language: English."

    def _iter_terms(self, report: StudyReport):
        groups = [
            ("basic", report.terminology.basic_concepts),
            ("method", report.terminology.method_concepts),
            ("experiment", report.terminology.experiment_concepts),
            ("mathematical", report.terminology.mathematical_concepts),
            ("engineering", report.terminology.engineering_concepts),
        ]
        for category, terms in groups:
            for term in terms:
                yield category, term

    def _report_language_blob(self, report: StudyReport) -> str:
        pieces: list[str] = [
            report.core_insight,
            report.domain_positioning.primary_field,
            report.domain_positioning.secondary_direction,
            report.domain_positioning.concrete_problem,
            report.domain_positioning.problem_chain,
            report.research_problem.target_problem,
            report.research_problem.importance,
            report.research_problem.input,
            report.research_problem.output,
            "\n".join(report.research_problem.prior_limitations),
            "\n".join(report.research_problem.evaluation_criteria),
            report.terminology.narrative,
            "\n".join(
                f"{term.what_it_is} {term.problem_solved} {term.role_in_paper} {term.relationships}"
                for _, term in self._iter_terms(report)
            ),
            "\n".join(
                f"{item.computes} {item.output_result} {item.served_module} {item.code_step} {item.removal_effect} {item.design_reason}"
                for item in report.formula_breakdowns
            ),
            report.pipeline.text_diagram,
            report.pipeline.data_source,
            "\n".join(f"{item.name} {item.input} {item.output} {item.role}" for item in report.pipeline.modules),
            "\n".join(report.pipeline.connections + report.pipeline.existing_methods + report.pipeline.innovations + report.pipeline.engineering_details),
            "\n".join(report.related_work.baselines + report.related_work.inherited_from + report.related_work.improved_from),
            report.related_work.key_difference,
            "\n".join(
                f"{item.method} {item.core_idea} {item.strengths} {item.weaknesses} {item.how_this_paper_improves}"
                for item in report.related_work.comparison_table
            ),
            "\n".join(f"{item.name} {item.reason}" for item in report.experiments.datasets),
            "\n".join(report.experiments.compared_methods),
            "\n".join(f"{item.name} {item.meaning} {item.capability}" for item in report.experiments.metrics),
            "\n".join(report.experiments.main_results + report.experiments.ablation_results + report.experiments.visualization_results + report.experiments.failure_cases),
            report.experiments.conclusion_support,
            "\n".join(report.limitations.assumptions + report.limitations.works_well_when + report.limitations.may_fail_when),
            f"{report.limitations.dataset_bias} {report.limitations.metric_bias} {report.limitations.compute_cost} {report.limitations.preprocessing_dependency}",
            "\n".join(report.limitations.reproducibility_risks + report.limitations.hidden_engineering_tricks),
            "\n".join(f"{item.label} {item.caption or ''} {item.context or ''} {item.section} {item.reason}" for item in report.paper_references),
            "\n".join(report.warnings),
        ]
        return "\n".join(piece for piece in pieces if piece)

    def _normalize_report(self, report: StudyReport, title: str, output_language: str = "en") -> StudyReport:
        report.title = report.title or title
        generated_keywords: list[LearningKeyword] = []
        for category, term in self._iter_terms(report):
            term.text = term.text.strip()
            if not term.text:
                continue
            term.type = term.type if term.type in {"term", "parameter", "formula"} else "term"
            term.normalized = term.normalized or re.sub(r"\s+", " ", term.text.strip().lower())
            term.aliases = sorted({alias.strip() for alias in term.aliases if alias.strip() and alias.strip() != term.text})
            generated_keywords.append(
                LearningKeyword(
                    text=term.text,
                    type=term.type,
                    category=category,
                    normalized=term.normalized,
                    aliases=term.aliases,
                    difficulty=term.difficulty or "beginner",
                    reason=term.role_in_paper or term.what_it_is,
                    first_occurrence=term.first_occurrence,
                    confidence=term.confidence,
                )
            )

        for formula in report.formula_breakdowns:
            formula.title = formula.title.strip()
            formula.latex = formula.latex.strip()
            if formula.title:
                generated_keywords.append(
                    LearningKeyword(
                        text=formula.title,
                        type="formula",
                        category="mathematical",
                        normalized=re.sub(r"\s+", " ", formula.title.lower()),
                        aliases=[],
                        difficulty="intermediate",
                        reason=formula.computes or formula.design_reason,
                        first_occurrence=formula.latex,
                        confidence=0.7,
                    )
                )

        narrative_lower = report.terminology.narrative.lower()
        missing_visible_terms: list[str] = []
        for _, term in self._iter_terms(report):
            if term.text and term.text.lower() not in narrative_lower:
                missing_visible_terms.append(term.text)
        if missing_visible_terms:
            unique_terms = list(dict.fromkeys(missing_visible_terms))[:10]
            bridge = (
                f"在本文中，{ '、'.join(unique_terms) } 这些概念共同串起问题定义、方法模块、公式约束和实验验证，需要放回原论文语境中理解。"
                if output_language == "zh"
                else f"In this paper, {', '.join(unique_terms)} connect the problem definition, method modules, formula constraints, and experimental validation, so they should be read in the source-paper context."
            )
            report.terminology.narrative = "\n\n".join(
                item for item in [report.terminology.narrative.strip(), bridge] if item
            )

        normalized_keywords = []
        seen: set[tuple[str, str]] = set()
        for keyword in [*generated_keywords, *report.learning_keywords]:
            keyword.text = keyword.text.strip()
            if not keyword.text:
                continue
            keyword.type = keyword.type or "term"
            keyword.normalized = keyword.normalized or re.sub(r"\s+", " ", keyword.text.strip().lower())
            key = (keyword.normalized, keyword.type)
            if key in seen:
                continue
            seen.add(key)
            keyword.aliases = sorted(
                {alias.strip() for alias in keyword.aliases if alias.strip() and alias.strip() != keyword.text}
            )
            normalized_keywords.append(keyword)
        report.learning_keywords = normalized_keywords[: self.settings.max_annotation_entities]
        return report

    def _validate_report_quality(self, report: StudyReport, output_language: str) -> list[str]:
        zh = output_language == "zh"

        def warn(message_zh: str, message_en: str) -> str:
            return message_zh if zh else message_en

        warnings: list[str] = []
        if not all(
            [
                report.domain_positioning.primary_field,
                report.domain_positioning.secondary_direction,
                report.domain_positioning.concrete_problem,
            ]
        ):
            warnings.append(warn("模型能力限制：领域定位信息不完整。", "Model limitation: field positioning is incomplete."))
        if not report.research_problem.target_problem or not report.research_problem.input or not report.research_problem.output:
            warnings.append(warn("模型能力限制：研究问题的输入、输出或目标问题缺失。", "Model limitation: research problem input, output, or target problem is missing."))
        terms = [term for _, term in self._iter_terms(report)]
        if not terms:
            warnings.append(warn("模型能力限制：未能抽取核心术语、参数或公式实体。", "Model limitation: no core terms, parameters, or formula entities were extracted."))
        elif any(not (term.what_it_is and term.role_in_paper and term.relationships) for term in terms):
            warnings.append(warn("模型能力限制：部分术语缺少定义、本文作用或关系解释。", "Model limitation: some terms miss definition, paper role, or relationship explanations."))
        if not report.formula_breakdowns:
            warnings.append(warn("PDF 抽取问题或模型能力限制：未能可靠拆解核心公式。", "PDF extraction issue or model limitation: no reliable core formula breakdowns were produced."))
        elif any(not (item.computes and item.output_result and item.design_reason) for item in report.formula_breakdowns):
            warnings.append(warn("模型能力限制：部分公式缺少计算目标、输出或设计原因。", "Model limitation: some formulas miss computation target, output, or design reason."))
        if not report.pipeline.text_diagram or not report.pipeline.modules:
            warnings.append(warn("模型能力限制：pipeline 流程或模块 I/O 不完整。", "Model limitation: pipeline flow or module I/O is incomplete."))
        if not report.related_work.comparison_table:
            warnings.append(warn("模型能力限制：已有工作对比表缺失。", "Model limitation: prior-work comparison table is missing."))
        if not (report.experiments.datasets and report.experiments.metrics and report.experiments.main_results):
            warnings.append(warn("模型能力限制：实验数据集、指标或主实验结论不完整。", "Model limitation: experiment datasets, metrics, or main results are incomplete."))
        if not (report.limitations.assumptions or report.limitations.may_fail_when or report.limitations.reproducibility_risks):
            warnings.append(warn("模型能力限制：假设和局限分析不完整。", "Model limitation: assumptions and limitation analysis is incomplete."))
        if not report.terminology.narrative:
            warnings.append(warn("模型能力限制：核心概念没有融入式正文解释。", "Model limitation: terminology narrative is missing."))
        return warnings

    def _normalize_report_evidence(
        self,
        report: StudyReport,
        paper_references: list[PaperReference] | None,
        assets: list[PaperAsset] | None,
    ) -> StudyReport:
        valid_sections = {"domain", "problem", "terms", "math", "pipeline", "related", "experiments", "limitations"}
        known = {(item.type, item.label): item for item in paper_references or []}
        normalized: list[PaperReference] = []
        for reference in report.paper_references:
            source = known.get((reference.type, reference.label))
            if not source:
                continue
            reference.page = reference.page or source.page
            reference.caption = reference.caption or source.caption
            reference.context = reference.context or source.context
            if reference.section not in valid_sections:
                reference.section = ""
            normalized.append(reference)
        if not normalized and paper_references:
            normalized = list(paper_references[:8])
        report.paper_references = normalized[:12]
        report.visual_references = []
        report.supporting_tables = []

        return report

    def generate_study_report(
        self,
        raw_text: str,
        title: str,
        output_language: str = "en",
        paper_references: list[PaperReference] | None = None,
        assets: list[PaperAsset] | None = None,
    ) -> StudyReport:
        prompt = self._load_prompt("document_structure.md")
        research_context = research_service.build_context(title=title, raw_text=raw_text)
        reference_context = [reference.model_dump() for reference in (paper_references or [])[:12]]
        user_prompt = (
            f"论文标题：{title}\n"
            f"{self._language_instruction(output_language)}\n"
            f"外部论文检索上下文：\n{research_context}\n\n"
            f"PDF 图表引用线索 JSON（只能用于文字引用，用户会回原文查看，不要输出图片 URL 或表格数据）：\n"
            f"{json.dumps(reference_context, ensure_ascii=False)[:9000]}\n\n"
            f"论文原文抽取文本：\n{raw_text[:18000]}"
        )
        data = self._call_json(prompt, user_prompt)
        candidate = data.get("study_report") if isinstance(data, dict) and isinstance(data.get("study_report"), dict) else data
        if isinstance(candidate, dict):
            try:
                report = StudyReport.model_validate(candidate)
                report = self._normalize_report(report, title=title, output_language=output_language)
                report = self._normalize_report_evidence(report, paper_references=paper_references, assets=assets)
                if not self._looks_like_requested_language(self._report_language_blob(report), output_language):
                    report.warnings.append(
                        "模型能力限制：模型输出语言与用户选择不完全一致。"
                        if output_language == "zh"
                        else "Model limitation: the output language did not fully match the user request."
                    )
                report.warnings.extend(self._validate_report_quality(report, output_language=output_language))
                report.warnings = list(dict.fromkeys(item for item in report.warnings if item))
                return report
            except Exception:
                self.last_error = "LLM report JSON did not match the expected study report schema."

        fallback = build_study_report_fallback(
            raw_text=raw_text,
            title=title,
            output_language=output_language,
            paper_references=paper_references,
            research_context=research_context,
        )
        if self.last_error:
            fallback.warnings.append(
                f"API 返回问题：{self.last_error}"
                if output_language == "zh"
                else f"API response issue: {self.last_error}"
            )
        fallback = self._normalize_report(fallback, title=title, output_language=output_language)
        fallback = self._normalize_report_evidence(fallback, paper_references=paper_references, assets=assets)
        fallback.warnings.extend(self._validate_report_quality(fallback, output_language=output_language))
        fallback.warnings = list(dict.fromkeys(item for item in fallback.warnings if item))
        return fallback

    def structure_document(self, raw_text: str, title: str, output_language: str = "en") -> str:
        report = self.generate_study_report(raw_text=raw_text, title=title, output_language=output_language)
        return study_report_to_markdown(report, output_language=output_language)

    def extract_entities(self, markdown_content: str) -> list[EntityCandidate]:
        prompt = self._load_prompt("entity_extraction.md")
        user_prompt = f"Markdown content:\n{markdown_content[:18000]}"
        data = self._call_json(prompt, user_prompt)
        if data and isinstance(data.get("entities"), list):
            try:
                return [EntityCandidate.model_validate(item) for item in data["entities"]]
            except Exception:
                pass
        return extract_entities_fallback(markdown_content)

    def generate_concept_page(
        self,
        concept_name: str,
        concept_type: str,
        context_snippet: str,
        output_language: str = "en",
    ) -> ConceptPageSections:
        prompt = self._load_prompt("concept_page.md")
        user_prompt = (
            f"概念名称：{concept_name}\n"
            f"概念类型：{concept_type}\n"
            f"{self._language_instruction(output_language)}\n"
            "只抽取新手理解该概念前必须掌握的前置概念。\n"
            "论文中的方法名、公式、符号和标准技术术语可保留原始记法，但必须用中文解释。\n"
            f"上下文片段：\n{context_snippet[:4000]}"
        )
        data = self._call_json(prompt, user_prompt)
        if data:
            try:
                parsed = ConceptPageSections.model_validate(data)
                text_blob = "\n".join(
                    [
                        parsed.one_line_explanation,
                        parsed.intuition,
                        parsed.role_in_this_paper,
                        parsed.strict_definition,
                        parsed.example,
                    ]
                )
                if self._looks_like_requested_language(text_blob, output_language):
                    parsed.prerequisites = [item.strip() for item in parsed.prerequisites if item.strip()][:5]
                    return parsed
            except Exception:
                pass

        prereqs = infer_prerequisites_fallback(context_snippet)
        if output_language == "zh":
            return ConceptPageSections(
                one_line_explanation=f"{concept_name} 是当前论文中出现的一个 {concept_type} 概念。",
                intuition=f"可以把 {concept_name} 理解为论文解释方法、假设、公式或实验现象时依赖的一个知识支点。",
                role_in_this_paper=f"在这篇论文里，{concept_name} 用来支撑文中的机制说明、假设解释、公式推导或实验分析。",
                strict_definition=f"这里对 {concept_name} 的定义以当前论文语境为准，而不是泛化的百科式定义。",
                prerequisites=prereqs,
                example=f"如果论文在公式或方法步骤中提到 {concept_name}，应结合它首次出现的上下文一起理解。",
            )

        return ConceptPageSections(
            one_line_explanation=f"{concept_name} is a {concept_type} that appears in the current paper.",
            intuition=f"Think of {concept_name} as a local building block the paper relies on to describe its method or analysis.",
            role_in_this_paper=f"In this paper, {concept_name} helps explain a specific mechanism, assumption, or expression appearing in the document.",
            strict_definition=f"{concept_name} is treated here according to the paper context rather than a broad encyclopedia definition.",
            prerequisites=prereqs,
            example=f"If the paper discusses {concept_name} in an equation or method step, read the concept page together with that local passage.",
        )

    def extract_recursive_prerequisites(self, markdown_content: str, output_language: str = "en") -> list[str]:
        prompt = self._load_prompt("concept_expand.md")
        user_prompt = (
            f"{self._language_instruction(output_language)}\n"
            "优先返回规范、可复用的前置概念名称。\n"
            f"概念页内容：\n{markdown_content[:6000]}"
        )
        data = self._call_json(prompt, user_prompt)
        if data and isinstance(data.get("prerequisites"), list):
            items = [str(item).strip() for item in data["prerequisites"] if str(item).strip()]
            return items[: self.settings.max_prerequisites_per_concept]
        return infer_prerequisites_fallback(markdown_content)[: self.settings.max_prerequisites_per_concept]


llm_service = LLMService()

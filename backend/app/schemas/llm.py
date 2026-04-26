from pydantic import BaseModel, Field, model_validator


class EntityCandidate(BaseModel):
    text: str
    type: str
    normalized: str
    reason: str
    aliases: list[str] = Field(default_factory=list)


class LearningKeyword(BaseModel):
    text: str
    type: str = "term"
    category: str = "basic"
    normalized: str = ""
    aliases: list[str] = Field(default_factory=list)
    difficulty: str = "beginner"
    reason: str = ""
    first_occurrence: str = ""
    confidence: float = 0.6


class PaperAsset(BaseModel):
    id: str
    type: str
    label: str
    url: str | None = None
    page: int | None = None
    caption: str | None = None
    context: str | None = None


class ReportTable(BaseModel):
    id: str | None = None
    title: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    notes: str | None = None
    page: int | None = None
    context: str | None = None


class ReportAssetReference(BaseModel):
    asset_id: str
    section: str
    reason: str
    caption: str | None = None


class PaperReference(BaseModel):
    type: str
    label: str
    page: int | None = None
    caption: str | None = None
    context: str | None = None
    section: str = ""
    reason: str = ""


class FormulaSymbol(BaseModel):
    symbol: str
    meaning: str


class FormulaBreakdown(BaseModel):
    title: str
    latex: str
    computes: str = ""
    symbols: list[FormulaSymbol] = Field(default_factory=list)
    input_variables: list[str] = Field(default_factory=list)
    output_result: str = ""
    served_module: str = ""
    code_step: str = ""
    removal_effect: str = ""
    design_reason: str = ""


class TensorShape(BaseModel):
    name: str
    shape: str
    meaning: str


class PipelineModule(BaseModel):
    name: str
    input: str
    output: str
    role: str
    source_type: str = "unknown"


class DomainPositioning(BaseModel):
    primary_field: str = ""
    secondary_direction: str = ""
    concrete_problem: str = ""
    problem_chain: str = ""


class ResearchProblem(BaseModel):
    target_problem: str = ""
    importance: str = ""
    prior_limitations: list[str] = Field(default_factory=list)
    input: str = ""
    output: str = ""
    evaluation_criteria: list[str] = Field(default_factory=list)


class TermExplanation(BaseModel):
    text: str
    type: str = "term"
    normalized: str = ""
    aliases: list[str] = Field(default_factory=list)
    difficulty: str = "beginner"
    what_it_is: str = ""
    problem_solved: str = ""
    role_in_paper: str = ""
    relationships: str = ""
    first_occurrence: str = ""
    confidence: float = 0.6


class TerminologySection(BaseModel):
    narrative: str = ""
    basic_concepts: list[TermExplanation] = Field(default_factory=list)
    method_concepts: list[TermExplanation] = Field(default_factory=list)
    experiment_concepts: list[TermExplanation] = Field(default_factory=list)
    mathematical_concepts: list[TermExplanation] = Field(default_factory=list)
    engineering_concepts: list[TermExplanation] = Field(default_factory=list)


class PipelineSection(BaseModel):
    text_diagram: str = ""
    data_source: str = ""
    modules: list[PipelineModule] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)
    existing_methods: list[str] = Field(default_factory=list)
    innovations: list[str] = Field(default_factory=list)
    engineering_details: list[str] = Field(default_factory=list)


class RelatedWorkComparison(BaseModel):
    method: str
    core_idea: str = ""
    strengths: str = ""
    weaknesses: str = ""
    how_this_paper_improves: str = ""


class RelatedWorkSection(BaseModel):
    baselines: list[str] = Field(default_factory=list)
    inherited_from: list[str] = Field(default_factory=list)
    improved_from: list[str] = Field(default_factory=list)
    key_difference: str = ""
    comparison_table: list[RelatedWorkComparison] = Field(default_factory=list)


class ExperimentDataset(BaseModel):
    name: str
    reason: str = ""


class MetricExplanation(BaseModel):
    name: str
    meaning: str = ""
    capability: str = ""


class ExperimentSection(BaseModel):
    datasets: list[ExperimentDataset] = Field(default_factory=list)
    compared_methods: list[str] = Field(default_factory=list)
    metrics: list[MetricExplanation] = Field(default_factory=list)
    main_results: list[str] = Field(default_factory=list)
    ablation_results: list[str] = Field(default_factory=list)
    visualization_results: list[str] = Field(default_factory=list)
    failure_cases: list[str] = Field(default_factory=list)
    conclusion_support: str = ""


class LimitationSection(BaseModel):
    assumptions: list[str] = Field(default_factory=list)
    works_well_when: list[str] = Field(default_factory=list)
    may_fail_when: list[str] = Field(default_factory=list)
    dataset_bias: str = ""
    metric_bias: str = ""
    compute_cost: str = ""
    preprocessing_dependency: str = ""
    reproducibility_risks: list[str] = Field(default_factory=list)
    hidden_engineering_tricks: list[str] = Field(default_factory=list)


class PrerequisiteItem(BaseModel):
    concept: str
    reason: str = ""


class PrerequisiteKnowledgeSection(BaseModel):
    immediate: list[PrerequisiteItem] = Field(default_factory=list)
    gradual: list[PrerequisiteItem] = Field(default_factory=list)
    optional: list[PrerequisiteItem] = Field(default_factory=list)


class ReproductionSection(BaseModel):
    environment: list[str] = Field(default_factory=list)
    data_preparation: list[str] = Field(default_factory=list)
    key_code_modules: list[str] = Field(default_factory=list)
    minimal_experiments: list[str] = Field(default_factory=list)
    validation_metrics: list[str] = Field(default_factory=list)
    troubleshooting_checklist: list[str] = Field(default_factory=list)


class ResearchReference(BaseModel):
    title: str
    year: int | None = None
    url: str | None = None
    venue: str | None = None


class FutureDirection(BaseModel):
    idea: str
    rationale: str
    checked_against: list[ResearchReference] = Field(default_factory=list)
    novelty_warning: str | None = None


class StudyReport(BaseModel):
    title: str = ""
    paper_identity: str | None = None
    core_insight: str = ""
    domain_positioning: DomainPositioning = Field(default_factory=DomainPositioning)
    research_problem: ResearchProblem = Field(default_factory=ResearchProblem)
    terminology: TerminologySection = Field(default_factory=TerminologySection)
    formula_breakdowns: list[FormulaBreakdown] = Field(default_factory=list)
    pipeline: PipelineSection = Field(default_factory=PipelineSection)
    related_work: RelatedWorkSection = Field(default_factory=RelatedWorkSection)
    experiments: ExperimentSection = Field(default_factory=ExperimentSection)
    limitations: LimitationSection = Field(default_factory=LimitationSection)
    prerequisite_knowledge: PrerequisiteKnowledgeSection = Field(default_factory=PrerequisiteKnowledgeSection)
    reproduction: ReproductionSection = Field(default_factory=ReproductionSection)
    supporting_tables: list[ReportTable] = Field(default_factory=list)
    visual_references: list[ReportAssetReference] = Field(default_factory=list)
    paper_references: list[PaperReference] = Field(default_factory=list)
    learning_keywords: list[LearningKeyword] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_report(cls, value):
        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        if "domain_positioning" not in migrated:
            migrated["domain_positioning"] = {
                "primary_field": "",
                "secondary_direction": "",
                "concrete_problem": "",
                "problem_chain": migrated.get("core_insight", ""),
            }
        if "research_problem" not in migrated:
            migrated["research_problem"] = {
                "target_problem": "\n".join(migrated.get("problem_and_motivation", []) or []),
                "importance": "",
                "prior_limitations": migrated.get("core_innovations", []) or [],
                "input": "",
                "output": "",
                "evaluation_criteria": [],
            }
        if "terminology" not in migrated:
            migrated["terminology"] = {
                "narrative": "",
                "basic_concepts": [],
                "method_concepts": [],
                "experiment_concepts": [],
                "mathematical_concepts": [],
                "engineering_concepts": [],
            }
        else:
            terminology = migrated.get("terminology")
            if isinstance(terminology, dict) and "narrative" not in terminology:
                terminology["narrative"] = ""
        if "formula_breakdowns" not in migrated and isinstance(migrated.get("mathematical_analysis"), list):
            migrated["formula_breakdowns"] = [
                {
                    "title": item.get("title", "") if isinstance(item, dict) else "",
                    "latex": item.get("latex", "") if isinstance(item, dict) else "",
                    "computes": item.get("intuition", "") if isinstance(item, dict) else "",
                    "symbols": [],
                    "input_variables": [],
                    "output_result": "",
                    "served_module": "",
                    "code_step": "",
                    "removal_effect": "",
                    "design_reason": item.get("derivation_logic", "") if isinstance(item, dict) else "",
                }
                for item in migrated.get("mathematical_analysis", [])
            ]
        if "pipeline" not in migrated:
            migrated["pipeline"] = {
                "text_diagram": "",
                "data_source": "",
                "modules": [],
                "connections": [],
                "existing_methods": [],
                "innovations": migrated.get("core_innovations", []) or [],
                "engineering_details": migrated.get("architecture_highlights", []) or [],
            }
        if "related_work" not in migrated:
            migrated["related_work"] = {
                "baselines": [],
                "inherited_from": [],
                "improved_from": [],
                "key_difference": "",
                "comparison_table": [],
            }
        if "experiments" not in migrated:
            migrated["experiments"] = {
                "datasets": [],
                "compared_methods": [],
                "metrics": [],
                "main_results": [],
                "ablation_results": [],
                "visualization_results": [],
                "failure_cases": [],
                "conclusion_support": "",
            }
        if isinstance(migrated.get("limitations"), list):
            migrated["limitations"] = {
                "assumptions": [],
                "works_well_when": [],
                "may_fail_when": migrated.get("limitations", []),
                "dataset_bias": "",
                "metric_bias": "",
                "compute_cost": "",
                "preprocessing_dependency": "",
                "reproducibility_risks": [],
                "hidden_engineering_tricks": [],
            }
        if "prerequisite_knowledge" not in migrated:
            migrated["prerequisite_knowledge"] = {
                "immediate": [],
                "gradual": [],
                "optional": [],
            }
        if "reproduction" not in migrated:
            migrated["reproduction"] = {
                "environment": [],
                "data_preparation": [],
                "key_code_modules": [],
                "minimal_experiments": [],
                "validation_metrics": [],
                "troubleshooting_checklist": migrated.get("reading_checklist", []) or [],
            }
        if "paper_references" not in migrated:
            migrated["paper_references"] = []
        return migrated


class ConceptPageSections(BaseModel):
    one_line_explanation: str
    intuition: str
    role_in_this_paper: str
    strict_definition: str
    prerequisites: list[str]
    example: str


class KeywordPageSections(BaseModel):
    meaning: str
    paper_specific_meaning: str
    why_needed: str
    relationships: str
    common_misunderstandings: list[str] = Field(default_factory=list)
    intuitive_example: str
    learning_keywords: list[LearningKeyword] = Field(default_factory=list)


class ConceptPageContent(ConceptPageSections):
    title: str
    concept_type: str
    aliases: list[str] = Field(default_factory=list)
    depth: int = 1
    max_depth: int = 10
    depth_limit_reached: bool = False

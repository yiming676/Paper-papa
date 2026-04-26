export type DocumentStatus = "uploaded" | "parsed" | "annotated";
export type ConceptState = "unknown" | "learning" | "mastered";

export interface LearningKeyword {
  text: string;
  type: string;
  category: string;
  normalized: string;
  aliases: string[];
  difficulty: string;
  reason: string;
  first_occurrence: string;
  confidence: number;
}

export interface PaperAsset {
  id: string;
  type: string;
  label: string;
  url?: string | null;
  page?: number | null;
  caption?: string | null;
  context?: string | null;
}

export interface ReportTable {
  id?: string | null;
  title: string;
  headers: string[];
  rows: string[][];
  notes?: string | null;
  page?: number | null;
  context?: string | null;
}

export interface ReportAssetReference {
  asset_id: string;
  section: string;
  reason: string;
  caption?: string | null;
}

export interface PaperReference {
  type: "figure" | "table" | string;
  label: string;
  page?: number | null;
  caption?: string | null;
  context?: string | null;
  section: string;
  reason: string;
}

export interface FormulaSymbol {
  symbol: string;
  meaning: string;
}

export interface FormulaBreakdown {
  title: string;
  latex: string;
  computes: string;
  symbols: FormulaSymbol[];
  input_variables: string[];
  output_result: string;
  served_module: string;
  code_step: string;
  removal_effect: string;
  design_reason: string;
}

export interface PipelineModule {
  name: string;
  input: string;
  output: string;
  role: string;
  source_type: string;
}

export interface DomainPositioning {
  primary_field: string;
  secondary_direction: string;
  concrete_problem: string;
  problem_chain: string;
}

export interface ResearchProblem {
  target_problem: string;
  importance: string;
  prior_limitations: string[];
  input: string;
  output: string;
  evaluation_criteria: string[];
}

export interface TermExplanation {
  text: string;
  type: string;
  normalized: string;
  aliases: string[];
  difficulty: string;
  what_it_is: string;
  problem_solved: string;
  role_in_paper: string;
  relationships: string;
  first_occurrence: string;
  confidence: number;
}

export interface TerminologySection {
  narrative: string;
  basic_concepts: TermExplanation[];
  method_concepts: TermExplanation[];
  experiment_concepts: TermExplanation[];
  mathematical_concepts: TermExplanation[];
  engineering_concepts: TermExplanation[];
}

export interface PipelineSection {
  text_diagram: string;
  data_source: string;
  modules: PipelineModule[];
  connections: string[];
  existing_methods: string[];
  innovations: string[];
  engineering_details: string[];
}

export interface RelatedWorkComparison {
  method: string;
  core_idea: string;
  strengths: string;
  weaknesses: string;
  how_this_paper_improves: string;
}

export interface RelatedWorkSection {
  baselines: string[];
  inherited_from: string[];
  improved_from: string[];
  key_difference: string;
  comparison_table: RelatedWorkComparison[];
}

export interface ExperimentDataset {
  name: string;
  reason: string;
}

export interface MetricExplanation {
  name: string;
  meaning: string;
  capability: string;
}

export interface ExperimentSection {
  datasets: ExperimentDataset[];
  compared_methods: string[];
  metrics: MetricExplanation[];
  main_results: string[];
  ablation_results: string[];
  visualization_results: string[];
  failure_cases: string[];
  conclusion_support: string;
}

export interface LimitationSection {
  assumptions: string[];
  works_well_when: string[];
  may_fail_when: string[];
  dataset_bias: string;
  metric_bias: string;
  compute_cost: string;
  preprocessing_dependency: string;
  reproducibility_risks: string[];
  hidden_engineering_tricks: string[];
}

export interface PrerequisiteItem {
  concept: string;
  reason: string;
}

export interface PrerequisiteKnowledgeSection {
  immediate: PrerequisiteItem[];
  gradual: PrerequisiteItem[];
  optional: PrerequisiteItem[];
}

export interface ReproductionSection {
  environment: string[];
  data_preparation: string[];
  key_code_modules: string[];
  minimal_experiments: string[];
  validation_metrics: string[];
  troubleshooting_checklist: string[];
}

export interface StudyReport {
  title: string;
  paper_identity?: string | null;
  core_insight: string;
  domain_positioning: DomainPositioning;
  research_problem: ResearchProblem;
  terminology: TerminologySection;
  formula_breakdowns: FormulaBreakdown[];
  pipeline: PipelineSection;
  related_work: RelatedWorkSection;
  experiments: ExperimentSection;
  limitations: LimitationSection;
  prerequisite_knowledge: PrerequisiteKnowledgeSection;
  reproduction: ReproductionSection;
  supporting_tables: ReportTable[];
  visual_references: ReportAssetReference[];
  paper_references: PaperReference[];
  learning_keywords: LearningKeyword[];
  warnings: string[];
}

export interface ConceptPageContent {
  title: string;
  concept_type: string;
  aliases: string[];
  one_line_explanation: string;
  intuition: string;
  role_in_this_paper: string;
  strict_definition: string;
  prerequisites: string[];
  example: string;
  depth: number;
  max_depth: number;
  depth_limit_reached: boolean;
}

export interface DocumentSummary {
  id: number;
  title: string;
  source_file: string;
  preferred_language: "en" | "zh";
  status: DocumentStatus;
  created_at: string;
  updated_at?: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  raw_text?: string | null;
  markdown_content?: string | null;
  annotated_markdown?: string | null;
  study_report?: StudyReport | null;
  asset_manifest?: PaperAsset[];
  learning_keywords?: LearningKeyword[];
  concept_links?: DocumentConceptLink[];
}

export interface DocumentConceptLink {
  concept_id: number;
  href: string;
  raw_text: string;
  canonical_name: string;
  normalized_text: string;
  entity_type: string;
  aliases: string[];
}

export interface ConceptRelationItem {
  id: number;
  canonical_name: string;
  concept_type: string;
  relation_type: string;
  aliases: string[];
}

export interface ConceptPathItem {
  id: number;
  canonical_name: string;
  concept_type: string;
  depth: number;
}

export interface ConceptDetail {
  id: number;
  canonical_name: string;
  concept_type: string;
  short_explanation?: string | null;
  long_explanation?: string | null;
  prerequisites_json?: string | null;
  output_language: "en" | "zh";
  state: ConceptState;
  concept_page_markdown: string;
  concept_page?: ConceptPageContent | null;
  related_document_ids: number[];
  prerequisites: ConceptRelationItem[];
  learning_path: ConceptPathItem[];
  depth_limit_reached: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface ConceptExpandResponse {
  concept_id: number;
  expanded: boolean;
  added_concept_ids: number[];
  concept_page_markdown: string;
  concept_page?: ConceptPageContent | null;
  depth_limit_reached: boolean;
}

export interface MasteredConceptItem {
  id: number;
  canonical_name: string;
  concept_type: string;
  short_explanation?: string | null;
  updated_at?: string | null;
}

export interface MasteredConceptListResponse {
  items: MasteredConceptItem[];
}

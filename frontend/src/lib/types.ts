// ── Risk Levels ──────────────────────────────────────────────────
export type RiskLevel = "Safe" | "Low Risk" | "Moderate Risk" | "High Risk" | "Unknown";
export type RiskLabel = "Critical" | "High" | "Moderate" | "Low";

// ── Upload ──────────────────────────────────────────────────────
export interface UploadResponse {
  id: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  extracted_text: string | null;
  status: string;
  created_at: string;
}

// ── Analysis Status ─────────────────────────────────────────────
export interface AnalyzeStatusResponse {
  id: number;
  status: string;
  progress: string;
}

// ── Evidence ─────────────────────────────────────────────────────
export interface EvidenceItem {
  source_organization: string;
  claim: string;
  claim_domain: string;
  evidence_strength: "strong" | "moderate" | "weak" | "theoretical";
  source_document: string | null;
  source_url?: string | null;
  source_year?: number | null;
  population?: string | null;
}

// ── Fired Rule ───────────────────────────────────────────────────
export interface FiredRule {
  rule_id: string;
  rule_name: string;
  score_contribution: number;
  reason: string;
  population: string;
}

// ── Substance in Report (v3) ─────────────────────────────────────
export interface SubstanceItem {
  id?: number;
  substance_name: string;
  cas_number?: string | null;
  category: string | null;
  pregnancy_risk: RiskLevel | string | null;
  fertility_risk: RiskLevel | string | null;
  lactation_risk: RiskLevel | string | null;
  pregnancy_score?: number;
  fertility_score?: number;
  lactation_score?: number;
  risk_reason: string | null;
  effects_on_fetus?: string | null;
  effects_on_reproduction?: string | null;
  effects_on_breastfeeding?: string | null;
  exposure_routes?: string[] | null;
  recommended_ppe?: string | null;
  recommended_precautions?: string | null;
  found_in_section?: string | null;
  ghs_classification?: string | null;
  hazard_statements?: string | null;
  references?: string | null;
  data_source?: string | null;
  evidence_level?: string | null;
  evidence?: EvidenceItem[];
  fired_rules?: FiredRule[];
  from_database?: boolean;
}

// ── Executive Summary (v3) ───────────────────────────────────────
export interface ExecutiveSummary {
  overall_risk: string;
  overall_score: number;
  total_substances: number;
  high_risk_count: number;
  critical_count?: number;
  population?: string;
  summary_text?: string;
  key_findings?: string[];
  general_recommendation?: string;
  // Legacy fields
  total_substances_found?: number;
  moderate_risk_count?: number;
  low_risk_count?: number;
  safe_count?: number;
}

// ── Population Risk ─────────────────────────────────────────────
export interface PopulationRiskEntry {
  max_score: number;
  risk_level: string;
  substances_at_risk: string[];
}

export interface PopulationRisk {
  pregnancy: PopulationRiskEntry;
  fertility: PopulationRiskEntry;
  lactation: PopulationRiskEntry;
}

// ── Detected Operation ──────────────────────────────────────────
export interface DetectedOperation {
  operation_id: string;
  name_en: string;
  name_zh: string;
  category: string;
  primary_exposure_route: string;
  risk_modifier: number;
  matched_keyword: string;
}

// ── Exposure Profile ────────────────────────────────────────────
export interface ExposureProfile {
  ventilation: string;
  temperature: string;
  frequency: string;
  duration_min: number | null;
  volume_ml: number | null;
  concentration_pct: number | null;
  is_powder: boolean;
  is_liquid: boolean;
  exposure_routes: string[];
  risk_modifier: number;
}

// ── Exposure Analysis ───────────────────────────────────────────
export interface ExposureAnalysis {
  operations_detected: DetectedOperation[];
  profiles: ExposureProfile[];
}

// ── Safety Controls ─────────────────────────────────────────────
export interface SafetyControls {
  engineering_controls: string[];
  recommended_ppe: string[];
  operational_procedures: string[];
}

// ── Evidence Summary ────────────────────────────────────────────
export interface EvidenceSummary {
  total_citations: number;
  sources_used: string[];
  general_evidence: EvidenceItem[];
}

// ── QC Metadata ─────────────────────────────────────────────────
export interface QCMetadata {
  passed: boolean;
  confidence_score: number;
  issues?: string[];
  warnings?: string[];
  stats?: {
    raw_extractions_count: number;
    normalized_count: number;
    resolved_count: number;
    unresolvable_count: number;
    missed_count: number;
    substances_with_evidence: number;
    total_substances: number;
    fired_rules: number;
  };
}

// ── Pipeline Metadata ───────────────────────────────────────────
export interface PipelineMetadata {
  extraction: {
    methods_used: string[];
    llm_fallback_used?: boolean;
    total_raw?: number;
    resolved?: number;
  };
  operations_detected?: number;
  rules_fired?: number;
  evidence_citations?: number;
}

// ── Report Metadata ─────────────────────────────────────────────
export interface ReportMetadata {
  version: string;
  generated_at: string;
  pipeline: PipelineMetadata;
  qc: QCMetadata;
}

// ── Legacy types (v2) ───────────────────────────────────────────
export interface RiskByCategory {
  high: number;
  moderate: number;
  low: number;
  safe: number;
}

export interface HighRiskItem {
  substance_name: string;
  category: string;
  pregnancy_risk: string;
  fertility_risk: string;
  lactation_risk: string;
  recommended_precautions: string | null;
}

export interface PrecautionItem {
  substance_name: string;
  risk: string;
  precautions: string[];
}

// ── Report History ──────────────────────────────────────────────
export interface ReportListItem {
  id: number;
  original_filename: string;
  file_type: string;
  overall_risk: string | null;
  overall_score: number | null;
  status: string;
  created_at: string | null;
}

export interface ReportListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ReportListItem[];
}

export interface SubstanceSearchResult {
  id: number;
  chemical_name: string;
  cas_number: string | null;
  category: string;
  pregnancy_risk: string;
  fertility_risk: string;
  lactation_risk: string;
  ghs_classification?: string | null;
  hazard_statements?: string | null;
  effects_on_fetus?: string | null;
  effects_on_reproduction?: string | null;
  effects_on_breastfeeding?: string | null;
  recommended_ppe?: string | null;
  recommended_precautions?: string | null;
  references?: string | null;
}

export interface SubstanceSearchResponse {
  total: number;
  items: SubstanceSearchResult[];
}

// ── Full Report (v3 + backward compatible v2) ────────────────────
export interface ReportDetail {
  id?: number;
  original_filename: string;
  overall_risk: string | null;
  overall_score: number | null;

  // v3 fields
  executive_summary: ExecutiveSummary | null;
  identified_hazardous_materials: SubstanceItem[];
  population_risk?: PopulationRisk;
  exposure_analysis?: ExposureAnalysis;
  safety_controls?: SafetyControls;
  evidence_summary?: EvidenceSummary;
  metadata?: ReportMetadata;
  qc_warnings?: string[];
  _v3?: {
    population_risk?: PopulationRisk;
    exposure_analysis?: ExposureAnalysis;
    safety_controls?: SafetyControls;
    evidence_summary?: EvidenceSummary;
    metadata?: ReportMetadata;
    qc_warnings?: string[];
    executive_summary?: ExecutiveSummary;
  };

  // v2 legacy fields
  high_risk_items?: HighRiskItem[];
  recommended_precautions?: PrecautionItem[];
  risk_by_category?: Record<string, RiskByCategory> | null;

  disclaimer?: string;
  created_at?: string | null;
}

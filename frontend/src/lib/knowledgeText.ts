import type { SubstanceSearchResult } from "./types";

const categoryMap: Record<string, string> = {
  固定液: "Fixative",
  有机溶剂: "Organic solvent",
  染料: "Dye / stain",
  抗生素: "Antibiotic",
  生物试剂: "Biological reagent",
  化学试剂: "Chemical reagent",
  麻醉剂: "Anesthetic",
  放射性物质: "Radioactive material",
};

const englishEvidence: Record<string, Partial<Record<"fetal" | "reproductive" | "breastfeeding", string>>> = {
  Formaldehyde: {
    fetal: "Known developmental hazard. Animal studies report fetal developmental abnormalities, reduced birth weight, and increased spontaneous abortion risk.",
    reproductive: "May impair male and female fertility. Reported concerns include reduced sperm quality, menstrual disruption, and difficulty conceiving.",
    breastfeeding: "Direct exposure should be avoided during lactation because formaldehyde is highly reactive and irritating even though it is rapidly metabolized in tissue.",
  },
  Paraformaldehyde: {
    fetal: "Depolymerizes to formaldehyde gas, so the pregnancy hazard is treated similarly to formaldehyde. Heating can release high concentrations of formaldehyde vapor.",
    reproductive: "Shares the same hazard mechanism as formaldehyde. Long-term exposure may impair reproductive function.",
    breastfeeding: "Use during lactation should be avoided or delegated, especially when preparing PFA solutions from powder.",
  },
  Glutaraldehyde: {
    fetal: "Animal evidence does not show strong teratogenicity, but high-concentration exposure can cause maternal toxicity that may indirectly affect fetal development.",
    reproductive: "Limited evidence suggests possible effects on sperm motility. High-concentration exposure to this strong crosslinker should be avoided.",
    breastfeeding: "Dermal absorption is limited because of its molecular size. Use in a fume hood keeps lactation exposure relatively low.",
  },
  "Osmium Tetroxide": {
    fetal: "Extremely toxic oxidizer. Vapor can injure eyes and tissue, and systemic distribution creates a conservative pregnancy concern despite limited developmental data.",
    reproductive: "Potential genotoxic concern for rapidly dividing cells, including germ cells.",
    breastfeeding: "May distribute into body tissues and should be avoided during lactation.",
  },
  Methanol: {
    fetal: "Known developmental toxicant. Methanol metabolites can cross the placenta, and animal studies report developmental delay and skeletal abnormalities.",
    reproductive: "May affect spermatogenesis and ovarian function. Chronic exposure has been associated with menstrual abnormalities.",
    breastfeeding: "Can enter breast milk; formate accumulation is a theoretical concern.",
  },
  Ethanol: {
    fetal: "High systemic intake is a known fetal hazard, but routine laboratory use in a hood produces very low exposure.",
    reproductive: "Reproductive risk is mainly associated with substantial systemic intake, not standard laboratory handling.",
    breastfeeding: "Routine hood-based laboratory handling is expected to create minimal lactation exposure.",
  },
  Acetone: {
    fetal: "No clear developmental toxicity is expected at occupational exposure levels.",
    reproductive: "Generally regarded as low reproductive risk under controlled laboratory conditions.",
    breastfeeding: "Low expected risk when handled with ventilation and standard PPE.",
  },
  Xylene: {
    fetal: "High-concentration inhalation in animal studies has been associated with fetal developmental effects and skeletal variation.",
    reproductive: "Occupational solvent exposure has been associated with menstrual disruption and longer time to pregnancy; male fertility effects are also possible.",
    breastfeeding: "Organic solvents can enter breast milk and may persist in adipose tissue.",
  },
  Toluene: {
    fetal: "Classified for suspected developmental toxicity. Animal studies report developmental delay and behavioral effects.",
    reproductive: "May affect reproductive function, including menstrual disruption and reduced sperm quality.",
    breastfeeding: "Lipid-soluble solvent that may enter milk and accumulate in fat tissue.",
  },
  Chloroform: {
    fetal: "Animal studies report developmental toxicity at high exposure levels, with greatest concern during early pregnancy.",
    reproductive: "Animal data suggest possible effects on spermatogenesis and ovulation.",
    breastfeeding: "May enter breast milk; hepatic toxicity concerns support avoiding unnecessary exposure.",
  },
  DMSO: {
    fetal: "Powerful penetration enhancer that can carry dissolved chemicals through skin and cell membranes. Risk depends strongly on what is dissolved in it.",
    reproductive: "High concentrations can affect cell differentiation in vitro; occupational evidence is limited.",
    breastfeeding: "Rapid dermal absorption and carrier effects are the primary lactation concerns.",
  },
  "DMF (Dimethylformamide)": {
    fetal: "Reproductive toxicant with animal evidence of developmental toxicity, including cardiovascular and skeletal findings.",
    reproductive: "Animal studies and occupational evidence indicate concern for fertility and adverse reproductive outcomes.",
    breastfeeding: "Dermal absorption is important; metabolites may enter milk.",
  },
  Acetonitrile: {
    fetal: "Metabolizes to cyanide. High-dose animal studies show developmental toxicity; routine hood use is usually a moderate concern.",
    reproductive: "High-dose animal studies show effects on reproductive organs; controlled occupational exposure is lower risk.",
    breastfeeding: "Cyanide metabolites are a theoretical lactation concern, reduced by fume hood use.",
  },
  "n-Hexane": {
    fetal: "Can cross the placenta. Its neurotoxic metabolite creates conservative developmental concern.",
    reproductive: "Classified for suspected reproductive toxicity; male testicular and sperm effects are a concern.",
    breastfeeding: "Lipid-soluble solvent that may enter milk and accumulate in fat tissue.",
  },
  "Dichloromethane (DCM)": {
    fetal: "Metabolism can produce carbon monoxide, which may impair fetal oxygen delivery at high exposure.",
    reproductive: "Animal fertility effects are not prominent, but exposure should still be minimized.",
    breastfeeding: "Can enter breast milk; carbon monoxide metabolite concerns support exposure minimization.",
  },
  "Ethyl Acetate": {
    fetal: "Animal studies do not show strong developmental toxicity and it is generally considered one of the lower-risk solvents.",
    reproductive: "No known reproductive toxicity under normal laboratory handling.",
    breastfeeding: "Rapid metabolism to ethanol and acetate supports low lactation concern.",
  },
  Isopropanol: {
    fetal: "Metabolizes to acetone and has not shown clear developmental toxicity at occupational exposure levels.",
    reproductive: "No known reproductive toxicity in routine laboratory use.",
    breastfeeding: "Very low expected risk with ventilation and standard PPE.",
  },
  "Ethidium Bromide (EtBr)": {
    fetal: "DNA-intercalating mutagen. Direct handling should be avoided during pregnancy even though routine gel concentrations are low.",
    reproductive: "Mutagenic properties raise concern for germ-cell DNA integrity.",
    breastfeeding: "Avoid direct exposure because DNA-binding properties remain a conservative concern.",
  },
  DAPI: {
    fetal: "DNA-binding stain with limited developmental toxicity data; premixed mounting media greatly reduce exposure.",
    reproductive: "Theoretical concern because it binds DNA, but working concentrations are very low.",
    breastfeeding: "Low expected risk with routine precautions and premixed solutions.",
  },
  "SYBR Safe DNA Gel Stain": {
    fetal: "Designed as an EtBr replacement with negative Ames testing according to manufacturer data.",
    reproductive: "No known reproductive toxicity; designed for safer laboratory use.",
    breastfeeding: "Low expected risk with standard handling.",
  },
};

export function hasCjk(text: string | null | undefined): boolean {
  return /[\u3400-\u9fff]/.test(text || "");
}

export function englishCategory(category: string | null | undefined): string {
  if (!category) return "Unclassified";
  return categoryMap[category] || category;
}

export function englishEvidenceText(
  item: SubstanceSearchResult,
  field: "fetal" | "reproductive" | "breastfeeding",
): string {
  const source =
    field === "fetal"
      ? item.effects_on_fetus
      : field === "reproductive"
        ? item.effects_on_reproduction
        : item.effects_on_breastfeeding;

  if (source && !hasCjk(source)) return source;

  const mapped = englishEvidence[item.chemical_name]?.[field];
  if (mapped) return mapped;

  if (item.hazard_statements && !hasCjk(item.hazard_statements)) return item.hazard_statements;
  return "No English evidence summary is available for this entry yet.";
}

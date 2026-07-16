"""Async chemical extraction service with structured JSON output.

Uses `response_format={"type": "json_object"}` for broad LLM provider compatibility
(OpenAI, DeepSeek, and other OpenAI-compatible APIs).
"""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas.ai_models import ChemicalExtractionResult
from app.services.retry_handler import ai_retry

logger = structlog.get_logger(__name__)

# ── Prompt ────────────────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You are a laboratory safety expert and chemical informatician with deep knowledge of:
- Molecular biology, cell biology, biochemistry, immunology, and histology protocols
- Common laboratory reagents, buffers, enzymes, antibiotics, and solvents
- Reproductive toxicology and chemical hazard classification

Analyze the provided laboratory protocol text and extract ALL chemical substances, biological agents,
reagents, and hazardous steps that may pose risks to pregnant, trying-to-conceive, or breastfeeding researchers.

You must respond with valid JSON only — no markdown, no code blocks, no explanatory text.

Format:
{
  "substances": [
    {
      "name": "Substance name in English (preferred). Use full chemical name or standard abbreviation (e.g., 'DMSO' for Dimethyl Sulfoxide, 'EDTA' for Ethylenediaminetetraacetic Acid). Include concentration if it indicates risk level.",
      "category": "One of: 化学试剂/生物试剂/染料/固定液/有机溶剂/抗生素/放射性物质/麻醉剂/其他",
      "found_in_section": "Original context from protocol, including concentration if mentioned (max 200 chars)"
    }
  ],
  "hazardous_steps": [
    {
      "description": "Hazardous step description with context",
      "hazards": ["Specific hazard 1", "Specific hazard 2"]
    }
  ]
}

IMPORTANT DETECTION GUIDELINES:

1. Extract ALL chemicals mentioned, even if they seem benign (e.g., PBS, Tris, HEPES, glycerol).
   Our database includes risk data for 200+ substances. Let matching determine risk level.

2. Pay special attention to:
   - Fixatives: Formaldehyde, PFA, Paraformaldehyde, Glutaraldehyde, Osmium Tetroxide, Glyoxal
   - Organic Solvents: Methanol, Ethanol, Acetone, Xylene, Toluene, Chloroform, DMSO, DMF, Acetonitrile, Hexane, DCM, Isopropanol, Ethyl Acetate, THF, Pyridine, Diethyl Ether, Formic Acid, TFA
   - Dyes & Stains: DAPI, Ethidium Bromide (EtBr), SYBR Safe, Hoechst 33342, Propidium Iodide (PI), Coomassie Blue (R-250/G-250), DAB, Silver Nitrate, NBT/BCIP, TMB, Ponceau S, Bromophenol Blue, Trypan Blue, Crystal Violet, Eosin, Hematoxylin
   - Antibiotics & Selection: Puromycin, G418 (Geneticin), Hygromycin B, Blasticidin S, Zeocin, Penicillin-Streptomycin, Carbenicillin, Kanamycin, Tetracycline, Chloramphenicol, Amphotericin B
   - Chemical Reagents: TEMED, β-Mercaptoethanol (2-ME), DTT, TCEP, PMSF, AEBSF, DEPC, SDS, Acrylamide (unpolymerized), Bis-acrylamide, APS, Triton X-100, Tween-20, NP-40, TRIzol/TRI Reagent, Sodium Azide, Phenol, Urea, Guanidine Hydrochloride, Imidazole, Hydrogen Peroxide (H₂O₂), β-Estradiol, Tamoxifen, Dexamethasone
   - Buffers & Solutions: Tris, HEPES, MOPS, PBS, TBE, TAE, Sodium Citrate, EDTA, EGTA
   - Enzymes & Proteins: Trypsin, Trypsin-EDTA, Collagenase, Proteinase K, DNase I, RNase A, Lysozyme, BSA, FBS, Lipofectamine
   - Biological Agents: Lentivirus, Retrovirus, Adenovirus, AAV, LPS/Endotoxin, Concanavalin A, Polybrene
   - Radioactive: ³²P (Phosphorus-32), ³⁵S (Sulfur-35), ³H (Tritium), ¹²⁵I (Iodine-125), ¹⁴C (Carbon-14)
   - Anesthetics: Isoflurane, Ketamine, Xylazine, Pentobarbital, Tribromoethanol (Avertin), Urethane

3. Detect mixtures and commercial products:
   - "TRIzol" or "TRI Reagent" → extract as TRIzol/TRI Reagent (contains phenol and guanidine)
   - "RIPA Buffer" → extract as RIPA Buffer (contains SDS, NP-40, sodium deoxycholate)
   - "Laemmli Buffer" → extract as Laemmli Buffer (contains SDS, β-mercaptoethanol or DTT)
   - "PFA 4%" → extract as PFA/Formaldehyde
   - "Pen-Strep" or "P/S" → extract as Penicillin-Streptomycin

4. Extract hazardous steps such as:
   - Heating/boiling of volatile solvents
   - Centrifugation of infectious agents
   - Sonication generating aerosols
   - Open handling of powders
   - Steps explicitly noting "in fume hood" (indicates hazard)
   - Animal perfusion with fixatives
   - Liquid nitrogen handling

5. For each substance found, quote the exact sentence or phrase from the protocol where it appears.

Only extract substances you can clearly identify from the text. Err on the side of inclusion — our risk
database will filter non-hazardous substances. If genuinely nothing found, return empty arrays."""


class ChemicalExtractor:
    """Extract chemical substances from protocol text using async LLM calls.

    Features:
    - Non-blocking async OpenAI-compatible calls
    - Structured JSON output via `response_format={"type": "json_object"}`
    - Automatic retry on transient failures via tenacity
    - Batch extraction for multiple text sections
    """

    MAX_CHARS = 30_000

    def __init__(self) -> None:
        kwargs: dict = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        kwargs["timeout"] = settings.ai.request_timeout
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.ai.model
        self._temperature = settings.ai.temperature
        self._max_tokens = settings.ai.max_tokens_extraction

    @ai_retry
    async def _call_ai(self, text: str) -> ChemicalExtractionResult:
        """Make the API call with retry. Uses json_object response_format."""
        truncated = text[: self.MAX_CHARS]
        if len(text) > self.MAX_CHARS:
            truncated += "\n...[truncated]"

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Protocol text:\n{truncated}"},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("ai_extraction_empty_response")
            return ChemicalExtractionResult()

        try:
            data = json.loads(content)
            return ChemicalExtractionResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("ai_extraction_parse_error", error=str(exc))
            # Attempt to strip markdown code blocks and retry parse
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
                try:
                    data = json.loads(cleaned)
                    return ChemicalExtractionResult.model_validate(data)
                except (json.JSONDecodeError, ValidationError):
                    pass
            return ChemicalExtractionResult()

    async def extract(self, text: str) -> ChemicalExtractionResult:
        """Extract substances from a single protocol text.

        Args:
            text: Raw protocol text from the uploaded file.

        Returns:
            ChemicalExtractionResult with identified substances and hazardous steps.
        """
        if not text or not text.strip():
            logger.info("extraction_skipped", reason="empty_text")
            return ChemicalExtractionResult()

        logger.info("extraction_started", text_length=len(text))
        try:
            result = await self._call_ai(text)
            logger.info(
                "extraction_completed",
                substance_count=len(result.substances),
                step_count=len(result.hazardous_steps),
            )
            return result
        except Exception as exc:
            logger.error("extraction_failed", error=str(exc), exc_info=True)
            return ChemicalExtractionResult()

    async def extract_batch(self, texts: list[str]) -> list[ChemicalExtractionResult]:
        """Extract substances from multiple text sections concurrently."""
        import asyncio

        if not texts:
            return []

        logger.info("extraction_batch_started", count=len(texts))
        tasks = [self.extract(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[ChemicalExtractionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("extraction_batch_item_failed", index=i, error=str(result))
                output.append(ChemicalExtractionResult())
            else:
                output.append(result)

        total = sum(len(r.substances) for r in output)
        logger.info("extraction_batch_completed", total_substances=total)
        return output

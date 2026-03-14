# Formulation Intelligence Engine: A BOM-Driven AI Verification System for Cosmetic Formulation Design

**EVAS Cosmetic R&D Technical White Paper**
**Version 1.0 — March 2026**

**Authors**: EVAS Cosmetic R&D Team
**Contact**: Sk Ji, CEO — EVAS Cosmetic

---

## Abstract

Cosmetic formulation design has traditionally relied on formulator experience and textbook knowledge. This paper presents a 3-Layer AI formulation verification system built entirely from a mid-size cosmetic company's own manufacturing records (BOM — Bill of Materials): 1,254 products × 766 ingredients = 39,415 actual formulation records.

**Key Results:**
- **L1 Knowledge Base**: 766 ingredient profiles + 42,781 co-occurrence pairs + 20 formulation clusters
- **L2 Prediction**: pH prediction MAE 0.213, viscosity within 1.6× range, appearance classification 79.3%
- **L3 Agentic Verification**: 4-agent pipeline for automated formulation validation
- **Dual Engine**: Company BOM-based verification (Engine A) + market expansion from 565,329 inferred compositions (Engine B)

A controlled comparison demonstrated that BOM-based formulations scored 65/100 reliability versus 35/100 for textbook-based formulations — a **1.86× improvement**.

**Keywords**: Cosmetic Formulation, Knowledge Graph, Machine Learning, Bill of Materials, Agentic AI, Market Intelligence

---

## 1. Introduction

### 1.1 Problem Statement

Traditional cosmetic formulation design suffers from four fundamental limitations:

1. **Textbook Dependency**: Formulations rely on generic ingredient textbooks and supplier-recommended compositions, ignoring the company's own manufacturing experience
2. **Tacit Knowledge Loss**: Experienced formulators' know-how is not systematized, leading to knowledge loss during personnel changes
3. **Prediction Gap**: Physical properties (pH, viscosity, appearance) cannot be predicted before prototyping, causing costly trial-and-error cycles
4. **Market Blindness**: No systematic method exists to explore ingredient combinations or concentration trends beyond the company's own experience

### 1.2 Background

EVAS Cosmetic has accumulated BOM data from 1,572 products developed over 15 years. However, this data existed only as manufacturing records — never leveraged as a knowledge asset for formulation design. This research transforms that data into a **formulation intelligence system**.

### 1.3 Approach

Inspired by Karpathy's (2026) AutoResearch concept — "AI agents autonomously experimenting and evaluating results in a feedback loop" — we designed a 3-Layer architecture adapted for formulation design:

```
┌─────────────────────────────────────────────────┐
│ L3: Agentic Verification                        │
│   Retriever → Predictor → Critic → Optimizer    │
│   + Market Expansion (Engine B)                 │
├─────────────────────────────────────────────────┤
│ L2: Prediction Models                           │
│   pH (GBR) | Viscosity (GBR) | Appearance (RFC) │
├─────────────────────────────────────────────────┤
│ L1: Knowledge Base                              │
│   Ingredient Profiles | Co-occurrence Matrix    │
│   Product Clusters | Base Formulas              │
└─────────────────────────────────────────────────┘
         ↕ Supabase (12 tables, 724,086 rows)
```

---

## 2. Data Assets

### 2.1 Primary Data (Company BOM)

| Dataset | Scale | Description | Reliability |
|---|---:|---|---|
| evas_labdoc_products | 1,572 | Product master (code, name, spec) | 🟢 High |
| evas_product_compositions | 39,415 | Actual formulation ratios (INCI, %, rank) | 🟢 High |
| Effective products | 1,254 | Products with BOM data (80% of total) | 🟢 High |
| Unique ingredients | 766 | Distinct INCI ingredients in BOM | 🟢 High |

BOM data represents actual manufacturing compositions — not estimates or inferences. **This is the system's core differentiator.**

### 2.2 Secondary Data (Market)

| Dataset | Scale | Description | Reliability |
|---|---:|---|---|
| incidecoder_products | 34,905 | Global market product master | 🟢 High |
| incidecoder_composition_inferred | 565,329 | Inferred compositions (rule-based-v2) | 🟡 Medium |
| incidecoder_ingredients | 1,320 | Ingredient detail profiles | 🟢 High |

Inferred composition confidence distribution:
- High: ~4%
- Medium: ~34%
- Low: ~62%

While exact percentages carry uncertainty, **patterns** (which ingredients appear in which categories) remain statistically valid.

### 2.3 Tertiary Data (Regulatory/Safety)

| Dataset | Scale | Description |
|---|---:|---|
| cosing_substances | ~6,000 | EU Cosmetic Ingredient Registry |
| cosing_function_contexts | 29,961 | Mechanisms, incompatibilities, concentrations (LLM-extracted) |
| incidecoder_research_ingredient_safety_v2 | ~1,320 | Safety concentration limits |

---

## 3. Layer 1: Knowledge Base

### 3.1 Ingredient Profiles

For each of the 766 ingredients across 1,254 products, we computed:

- **usage_count**: Number of products containing the ingredient
- **avg_pct / median_pct / max_pct / min_pct**: Concentration distribution
- **avg_rank**: Average position in INCI list
- **categories**: Product category distribution
- **top_cooccurrence**: Top 5 most frequently co-occurring ingredients

#### Key Findings

**Top 10 Most Used Ingredients:**

| Rank | Ingredient | Products | Usage Rate |
|---:|---|---:|---:|
| 1 | Fragrance | 1,186 | 94.6% |
| 2 | Water | 1,165 | 92.9% |
| 3 | Disodium EDTA | 1,053 | 84.0% |
| 4 | Butylene Glycol | 920 | 73.4% |
| 5 | Glycerin | 877 | 69.9% |

### 3.2 Co-occurrence Matrix

We computed pairwise co-occurrence for all ingredients used ≥3 times:

- **Total pairs**: 54,506
- **Valid pairs (co_count ≥ 2)**: 42,781
- **Metric**: Jaccard similarity = |A ∩ B| / |A ∪ B|

#### Key Findings

**Jaccard 1.0 Sets (Always Together):**
A set of 6 EVAS signature flower extracts — Daisy, Chrysanthemum, Evening Primrose, Cherry Blossom, Rose, and Elder — appeared together in all 206 products without exception. This demonstrates how company-specific formulation practices emerge clearly from data.

**Practical Never-Together Pairs:**
Alcohol (360 products) ↔ Cocamidopropyl Betaine (270 products): co-occurrence of only 5. This reflects fundamental structural incompatibility between toner/essence (alcohol-based) and cleansing (betaine-based) formulations.

### 3.3 Product Clustering

We performed KMeans clustering on 1,144 products using 766-dimensional composition vectors.

#### Cluster Count Selection: k=9 vs k=20

Initial k=9 produced one dominant cluster (C0) containing 623 products, mixing shampoos, toners, and essences under a single "water-soluble" label. Switching to k=20 yielded meaningful sub-patterns:

| Cluster | Products | Type | Signature Ingredient |
|---|---:|---|---|
| C0 | 338 | Mist/Toner/Essence | Alcohol |
| C5 | 162 | SLS/SLES Body Wash | Sodium Lauryl Sulfate |
| C11 | 259 | Emulsion/Cream | Alcohol |
| C12 | 17 | ALS Shampoo | Acrylates Copolymer |
| C15 | 254 | O/W Cream/Lotion | Glycerin |
| C17 | 21 | Foam Cleanser | Glycerin |
| C19 | 47 | Hair Conditioner | Dimethicone |

Each cluster centroid is stored as a **Base Formula** — a starting point for new formulations.

---

## 4. Layer 2: Prediction Models

### 4.1 Feature Engineering

BOM compositions were converted to 468-dimensional vectors, where each dimension represents the percentage of a specific ingredient. Ingredients used fewer than 3 times were excluded as noise.

### 4.2 pH Prediction

| Parameter | Value |
|---|---|
| Model | Gradient Boosting Regressor |
| Training data | 478 samples (pH 3.5–10.0) |
| Validation | 5-fold Cross Validation |
| MAE | 0.213 ± 0.014 |
| Top Features | Glyceryl Stearate (0.144), KOH (0.098), Stearyl Alcohol (0.075) |

MAE of 0.213 is well within the typical measurement tolerance of ±0.5–1.0 pH units.

**Live Validation (AOSP003 — Houttuynia Shampoo):**
- Predicted: pH 5.77
- Actual: pH 5.80 ± 1.0
- Error: **0.03** ✅

### 4.3 Viscosity Prediction

| Parameter | Value |
|---|---|
| Model | Gradient Boosting Regressor (log10 scale) |
| Training data | 365 samples (13–85,000 cps) |
| MAE | 0.212 log10 (~1.6× range) |
| Top Features | Water (0.200), Chamomilla Extract (0.047), Dimethicone (0.038) |

Due to the extreme range (13–85,000 cps), viscosity was log10-transformed before training. MAE 0.212 in log10 means predictions fall within approximately 1.6× of actual values.

**Live Validation (AOSP003):**
- Predicted: 5,405 cps
- Actual: 5,500 ± 2,000 cps
- Error: **95 cps** ✅

### 4.4 Appearance Prediction

| Parameter | Value |
|---|---|
| Model | Random Forest Classifier |
| Training data | 1,004 samples, 8 classes |
| Accuracy | 79.3% ± 2.6% |
| Classes | cream, gel, transparent, oil, translucent, other, pearl, powder |

**Live Validation (AOSP003):**
- Predicted: gel (45%), transparent (35%)
- Actual: "Green gel-like" (gel category)
- Verdict: **Correct** ✅

---

## 5. Layer 3: Agentic Verification

### 5.1 Architecture

Four sequential agents validate each formulation:

```
Input: Composition + Constraints
         ↓
[Agent 1: Retriever] — Searches L1 for relevant data
         ↓
[Agent 2: Predictor] — L2 model predictions
         ↓
[Agent 3: Critic]    — 4-axis validation
         ↓
[Agent 4: Optimizer] — Improvement suggestions
         ↓
Output: Verification Report (Reliability Score + Detailed Feedback)
```

### 5.2 Agent 1: Retriever

Retrieves from L1 Knowledge Base:
- Ingredient profiles for input ingredients (usage frequency, concentration ranges)
- Similar EVAS products (up to 10 products containing the same key ingredients)
- Matching cluster (based on product category)
- Co-occurrence data for key ingredients

### 5.3 Agent 2: Predictor

Feeds the composition through L2 models to predict pH, viscosity, and appearance. Appearance predictions include full probability distributions (e.g., "transparent 48%, gel 45%").

### 5.4 Agent 3: Critic — 4-Axis Validation

#### Axis 1: Ingredient Verification Rate
Each ingredient is classified by EVAS usage history:
- **10+ products** → ✅ Verified: extensively used in actual manufacturing
- **3–9 products** → ⚠️ Limited verification: used in some products
- **0–2 products** → 🚨 Unverified: rarely or never used at EVAS

**Significance**: An ingredient recommended as "gentle" in textbooks but never actually used by the company carries unverified risks in sourcing, stability, and compatibility.

#### Axis 2: Incompatibility Check
Two data sources:
1. **CosIng incompatibility field**: EU cosmetic ingredient database
2. **Zero co-occurrence pairs**: Ingredient pairs never used together across 1,254 EVAS products

#### Axis 3: Safety Concentration Limits
Checks proposed concentrations against INCIDecoder safety database thresholds (max_conc_body / max_conc_face).

#### Axis 4: Predicted Properties vs Targets
Compares L2 predictions against user-defined targets (target_ph, target_viscosity, transparency requirement).

### 5.5 Reliability Score

```
Score = 100 - (ISSUES × 15) - (WARNINGS × 5)
Range: 0–100
```

| Score | Interpretation | Action |
|---:|---|---|
| 80–100 | Ready for prototyping | Proceed |
| 60–79 | Caution needed | Review flagged ingredients |
| 40–59 | Risky | Consider replacing unverified ingredients |
| 0–39 | Redesign needed | Change formulation structure |

---

## 6. Engine B: Market Expansion

### 6.1 Motivation

Engine A (BOM-based) alone limits formulations to "what EVAS has already done." To break this ceiling, we incorporate market data — but compare by **formulation structure (composition vectors)**, not by category labels.

### 6.2 Methodology

#### 6.2.1 Category Labels vs Formulation Structure

| Approach | Example | Problem |
|---|---|---|
| Category label | "shampoo" | Mixes SLS, sulfate-free, dry, 2-in-1 |
| **Formulation structure** | **Composition vector → cosine similarity** | **Compares like-for-like** |

#### 6.2.2 Cluster Mapping

16,034 market products were mapped to EVAS k=20 clusters:

1. Convert each market product's inferred composition to a 766-dimensional vector
2. Compute cosine similarity against all 20 EVAS cluster centroids
3. Assign to the most similar cluster (threshold: similarity > 0.1)

**Result: 11,221 products successfully mapped (70%)**

### 6.3 Results

| Cluster | EVAS | Market | Similarity | Key Finding |
|---|---:|---:|---:|---|
| C0 (Toner) | 338 | 249 | 0.957 | High structural match |
| C5 (SLS Body Wash) | 162 | 65 | 0.909 | Market uses SLES alongside SLS |
| C12 (Shampoo) | **17** | **179** | 0.877 | **EVAS has 10× less experience** |
| C19 (Emulsion) | 47 | **9,617** | 0.975 | Massive market benchmark available |

### 6.4 Application: Dual Report

Every formulation check produces a combined Engine A + Engine B report:

```
🟢 Engine A (Company Standard)
  Reliability 65/100 | Ingredient verification 94%
  → "This formulation is safe within EVAS experience"

🔵 Engine B (Market Expansion)
  Mapped to C12 | EVAS 17 vs Market 179 products
  Panthenol: Ours 0.1% vs Market 1.5% (15× gap)
  Cetrimonium Chloride: 124 market products use it, EVAS 0
  → "The market uses significantly more conditioning agents"
```

---

## 7. Experimental Validation

### 7.1 Textbook vs BOM-Based Formulation Comparison

For the same product brief (transparent sulfate-free Houttuynia shampoo), two formulations were designed and verified:

**V1 — Textbook-based:**
- Primary surfactant: Sodium Lauroyl Methyl Isethionate (SLMI) 8%
- Thickener: PEG-150 Distearate 0.8%
- Ingredients selected from textbook "gentle SF surfactant" recommendations

**V2 — BOM-based:**
- Primary surfactant: Sodium C14-16 Olefin Sulfonate 5% (from AOSP003)
- Co-surfactant: Potassium Cocoyl Glycinate 2%
- Ingredients selected from EVAS products with proven track records

### 7.2 Results

| Metric | V1 (Textbook) | V2 (BOM-based) | Winner |
|---|:---:|:---:|:---:|
| **Reliability Score** | **35/100** | **65/100** | V2 ×1.86 |
| Ingredient Verification | 79% | **94%** | V2 |
| Unverified Ingredients | 2 (SLMI, PEG-150 DS) | **0** | V2 |
| Warnings | 10 | 7 | V2 |
| Issues | 1 🚨 | **0** | V2 |
| pH Prediction | 5.55 | 5.86 | V1 closer to target |
| Viscosity | 8,123 cps | 8,008 cps | Similar |
| Transparency Probability | 50% | 43% | Similar |

### 7.3 Interpretation

V1 achieved a slightly better pH prediction but included **two EVAS-unverified ingredients** (SLMI and PEG-150 Distearate). These ingredients:
- Have never been used in EVAS's 15-year manufacturing history
- Carry unverified risks in sourcing, supplier quality, and compatibility
- Require preliminary small-batch stability testing before production

V2 requires minor pH adjustment (adding 0.05% Citric Acid) but consists of **94% verified ingredients** — ready for immediate prototyping.

**Conclusion: "Good-looking" ingredients from textbooks are less reliable than ingredients validated across 1,254 actual products.**

---

## 8. System Architecture

### 8.1 Infrastructure

| Component | Technology | Role |
|---|---|---|
| Database | Supabase PostgreSQL (Pro) | 12 tables, 724K+ rows |
| ML Models | scikit-learn (GBR, RFC) | pH / viscosity / appearance |
| Orchestration | Python + OpenClaw | Agent pipeline |
| Sub-agent | ⚗️ EVAS Formulator | Parallel formulation checks |
| Documentation | Obsidian | Architecture + evolution log |
| Caching | Local JSON + heartbeat refresh | Rate limit protection |

### 8.2 Parallel Processing via Sub-agents

```
User: "Verify all 4 shampoo formulations"
         ↓
  🔬 EVAS LAB (main agent)
         ↓ spawn × 4 (parallel)
  ⚗️ Formulator #1 → PURIFY result
  ⚗️ Formulator #2 → BALANCE result
  ⚗️ Formulator #3 → STRENGTHEN result
  ⚗️ Formulator #4 → REPAIR result
         ↓
  Consolidated report
```

Supports up to 8 concurrent sub-agents.

### 8.3 Self-Evolution Loop

A daily cron job (08:00 KST) executes:
1. System health check (DB connection, model files)
2. Data change detection (new BOM entries)
3. Random product reverse-verification (tracking prediction errors)
4. R&D trend web search
5. Improvement proposal → archived in Obsidian

All findings are archived in `Formulation_Intelligence/Improvement_Log/YYYY-MM-DD.md`, creating a cumulative record of how the system evolves over time.

---

## 9. Limitations

### 9.1 Absence of Ground Truth Feedback Loop

The system currently **predicts but never verifies against actual measurements**. When L2 predicts "pH 5.77," the system has no way to know whether the actual prototype measured 6.1 or 5.3.

```
Current:  Composition → Prediction → End
Needed:   Composition → Prediction → Prototype → Measurement → Error Learning → Better Prediction
```

AutoResearch (Karpathy, 2026) derives its power from val_bpb being ground truth. Our equivalent would be actual prototype results — stability tests, sensory evaluations, measured properties. When this data accumulates, the system can evolve to a fundamentally different level.

### 9.2 Data Quality Issues

- 62% of inferred market compositions have "low" confidence
- INCI naming inconsistencies (Water vs Aqua vs Aqua/Water)
- INCIDecoder parsing artifacts ("Read all the geeky details...")
- Engine B mapping failure rate of 30% due to these issues

### 9.3 Model Limitations

- pH training data limited to 478 samples (1,000+ recommended for industrial-grade accuracy)
- Extreme viscosity values (85,000 cps) prediction instability
- 8-class appearance model cannot distinguish fine-grained descriptions like "green gel-like"

### 9.4 Scoring Limitations

The reliability score is **rule-based** (WARNING −5, ISSUE −15), not calibrated against actual prototype outcomes. Whether a 65-point formulation truly outperforms a 35-point formulation in practice requires validation through accumulated prototype data.

---

## 10. Future Work

### Phase 1: Short-term (1–3 months)

| Task | Impact |
|---|---|
| INCI normalization mapping table | Engine B mapping 70% → 85%+ |
| INCIDecoder parsing cleanup | Data quality improvement |
| High-confidence composition filtering | Engine B accuracy |
| Score weight tuning | Practical reliability |

### Phase 2: Mid-term (3–6 months)

| Task | Impact |
|---|---|
| **Prototype result input system** | Ground truth feedback loop begins |
| L2 model retraining pipeline | Automatic improvement with new data |
| Stability prediction axis | 3-month accelerated stability prediction |
| Cost prediction axis | Formulation-stage cost optimization |
| Sensory evaluation prediction | Predict user experience before prototype |

### Phase 3: Long-term (6–12 months)

| Task | Impact |
|---|---|
| **AutoResearch loop** | Predict → Prototype → Measure → Correct |
| Automated formulation generation | Brief → optimal formulation proposal |
| Competitor formulation reverse-engineering | Market product strategy analysis |
| LLM-based formulation rationale | "Why this ingredient at this concentration" |

### Phase 4: Expansion (12+ months)

| Task | Impact |
|---|---|
| Multi-company federated BOM learning | Industry-wide knowledge base |
| Supplier data integration | Real-time sourcing, pricing, lead times |
| Automated regulatory check (NMPA, EU CPR, FDA) | Export formulation verification |

---

## 11. Conclusion

This research demonstrates that a mid-size cosmetic company can build an AI-powered formulation verification system **from its own BOM data alone**, without large-scale infrastructure investment.

**Key Contributions:**

1. **Quantitative validation of the BOM-first principle**: BOM-based formulations scored 65/100 reliability versus 35/100 for textbook-based approaches — a 1.86× improvement
2. **Structure-based market comparison**: Using cosine similarity on composition vectors (not category labels) to map 16,000+ market products to company clusters, revealing expansion opportunities
3. **Practical 3-Layer architecture**: Knowledge Graph → ML Prediction → Agentic Verification, proven implementable at mid-size company scale
4. **Dual Engine approach**: Simultaneous company-standard verification (safety) and market expansion analysis (growth), balancing between "staying in place" and "reckless experimentation"

**Data beats intuition.** Fifteen years of manufacturing records from 1,254 products constitute a more accurate formulation guide than any textbook. This system simply made that data speak.

---

## References

1. Karpathy, A. (2026). AutoResearch: Autonomous AI Research Agents. GitHub: autoresearch-macos.
2. Anthropic. (2026). Claude API Prompt Caching Documentation.
3. EU CosIng Database. European Commission Cosmetic Ingredient Database.
4. INCIDecoder. Global Cosmetic Product & Ingredient Database.
5. EVAS Cosmetic Internal BOM Archive (2011–2026). 1,572 products.

---

## Appendix A: System Specifications

| Component | Specification |
|---|---|
| Hardware | Apple Mac mini (M-series, ARM64) |
| OS | macOS Darwin 25.3.0 |
| Runtime | Node.js v25.5.0 + Python 3.14 |
| Database | Supabase PostgreSQL (Pro Plan) |
| ML Framework | scikit-learn |
| Orchestration | OpenClaw 2026.3.2 |
| AI Models | Anthropic Claude Sonnet 4.5, xAI Grok 4.1 |
| Storage | 724,086 rows across 12 tables |

## Appendix B: Reproducibility

All code is available at:

```
projects/formulations/
  ├── formulation_engine.py        — L3 integrated engine (Engine A + B)
  ├── build_l1_profiles.py         — Ingredient profile computation
  ├── build_l1_cooccurrence.py     — Co-occurrence matrix
  ├── build_l1_clusters.py         — Product clustering
  ├── build_l2_predictors.py       — ML model training
  ├── build_engine_b_clustered.py  — Market profile construction
  ├── WHITEPAPER.md                — Korean version
  └── WHITEPAPER-EN.md             — This document

projects/arpt/
  ├── l2_models.pkl                — Trained ML models
  ├── l1_clusters_k20.json         — Cluster data
  ├── engine_b_clustered_profiles.json — Market profiles
  └── .venv/                       — Python virtual environment
```

---

*© 2026 EVAS Cosmetic. All rights reserved.*

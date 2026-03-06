# HDSR Proposal Submission

## Title
Intuitiveness as the Next Stage of Open Data: A Meta-Design Framework for Dataset Complexity Adaptation

## Authors
- **Sarazin Arthur**^a,d,* — Researcher in Design Science, Veltys, France
- **Mourey Mathis**^b,d — Researcher in Data Science, The Hague University of Applied Sciences, Netherlands
- ^d UNESCO Chair "AI and Data Science for Society"
- *Corresponding author: asarazin@veltys.com

## Keywords
open data, meta-design, data literacy, dataset complexity, human-data interaction, knowledge graphs

---

## Executive Summary

### The Problem

Open data platforms have achieved remarkable scale—France's data.gouv.fr hosts over 45,000 datasets, the World Bank Open Data provides thousands more—yet utilization rates remain disappointing. Research consistently identifies a fundamental design flaw: datasets are created for expert users while the potential user base spans from citizens seeking single facts to data scientists building complex products. Current platforms offer one-size-fits-all presentations that fail to accommodate varying data literacy levels and analytical needs.

### Our Contribution

We propose a **conceptual meta-design framework** that reconceptualizes datasets as navigable structures with five levels of abstraction (L0–L4), enabling complexity to adapt to user capabilities:

| Level | Structure | Example |
|-------|-----------|---------|
| L0 | Single datum (entity-attribute-value) | "Average school score = 72%" |
| L1 | Single vector (one entity, multiple attributes) | Score distribution across schools |
| L2 | Single table (multiple entities and attributes) | Schools with scores and demographics |
| L3 | Linkable multi-level datasets | Schools linked to regional statistics |
| L4 | Unlinkable datasets | Disconnected CSV files |

The framework operationalizes two movements: **descent** (L4→L0) transforms chaotic, unlinkable datasets into atomic, interpretable metrics; **ascent** (L0→L3) reconstructs datasets with user-specified analytical dimensions tailored to specific questions.

### Theoretical Foundation

We ground our framework in design science research methodology and Csikszentmihalyi's flow theory, mapping the five abstraction levels to stages of intuitive cognition (preparation, incubation, insight, evaluation, elaboration). We provide a **formal complexity analysis** demonstrating that transitions between adjacent levels achieve 75–100% complexity reduction, measured by the combinatorial relationships extractable from each structure.

### Validation

We validate the framework through two mechanisms:

1. **Case Study**: A major international logistics operator managing 8,368 indicators across multiple sources. The descent phase revealed 40,279 relationships and enabled systematic identification of redundancy clusters. The ascent phase reconstructed intuitive tables directly answering business questions about indicator consolidation.

2. **Implementation**: The open-source `intuitiveness` Python package (https://github.com/ArthurSrz/intuitiveness) operationalizes the framework with AI-assisted entity discovery (via LLM), semantic domain matching (using multilingual embeddings), and interactive navigation. An accompanying Streamlit interface integrates with France's data.gouv.fr platform, demonstrating applicability to real open data ecosystems.

### Significance for Data Science

This work contributes to HDSR's foundational research agenda by:

- **Formalizing dataset complexity** as a measurable, reducible property
- **Bridging design science and data science** through a principled meta-design approach
- **Addressing data literacy barriers** that limit open data's societal impact
- **Providing reproducible tools** for practitioners (open-source package with documentation)

The framework has immediate practical implications for open data platforms seeking to serve diverse "data publics" and for organizations struggling to make sense of fragmented data ecosystems.

### Fit with HDSR

This article aligns with HDSR's emphasis on **foundational thinking with practical impact**. The theoretical framework offers lasting educational value for data science curricula addressing human-data interaction, while the case study and implementation provide a model for principled methodology in applied contexts. The work addresses the journal's interest in data literacy and accessibility—critical challenges as data science expands beyond technical specialists.

---

## Submission Checklist

- [ ] Submit via [HDSR Editorial Manager](https://www.editorialmanager.com/hdsr/)
- [ ] Include this proposal (1-2 pages)
- [ ] Wait for invitation (2-3 weeks)
- [ ] If invited, submit full manuscript (`intuitiveness_hdsr.pdf`)

## Files in This Folder

| File | Description |
|------|-------------|
| `HDSR_PROPOSAL.md` | This proposal document |
| `intuitiveness_hdsr.tex` | LaTeX source file |
| `intuitiveness_hdsr.pdf` | Compiled manuscript (18 pages) |
| `0.png` - `3.png` | Figure files |

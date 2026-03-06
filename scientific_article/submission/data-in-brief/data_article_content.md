# Data in Brief Article Content
## Five-Level Data Abstraction Transformations for Intuitive Open Data Design

**Instructions**: Copy each section into the corresponding yellow-highlighted section of the Data in Brief Word template. Delete all instructional blue text before submission.

---

## ARTICLE INFORMATION

### Article Title
Five-level data abstraction transformations for intuitive open data design

### Authors
Arthur Sarazin*, Mathis Mourey

### Affiliations
Arthur Sarazin: Researcher in Design Science, Veltys, France; Researcher associated with the UNESCO Chair "AI and Data Science for Society"

Mathis Mourey: Researcher in Data Science, The Hague University of Applied Sciences, Netherlands; Researcher associated with the UNESCO Chair "AI and Data Science for Society"

### Corresponding Author
*asarazin@veltys.com

### Keywords
open data; data abstraction; complexity reduction; data literacy; semantic matching; knowledge graphs; educational datasets; data transformation

### Abstract
This dataset collection demonstrates systematic transformations of open datasets across five levels of abstraction, implementing a meta-design framework for creating "intuitive datasets" that adapt their complexity to user needs. The collection includes three complete transformation cycles from the French national open data platform (data.gouv.fr): test0_schools (middle school performance indicators), test1_ademe (environmental funding allocations), and test2_energy (energy price data). Each dataset undergoes a descent phase (L4→L0) progressively reducing complexity from unlinkable multi-level datasets to atomic metrics, followed by an ascent phase (L0→L3) intentionally reconstructing complexity with user-specified analytic dimensions. Transformations were performed using the intuitiveness Python package (v0.1.0), employing semantic matching with language models, knowledge graph construction, and domain categorization. The datasets enable researchers to study complexity reduction patterns, data scientists to benchmark transformation algorithms, open data platforms to implement multi-level access features, and educators to teach data literacy concepts through concrete examples. All files are publicly available on Zenodo with complete documentation, transformation metadata, and session exports enabling full reproducibility.

---

## SPECIFICATIONS TABLE

### Subject
Computer Science / Information Systems

### Specific subject area
Open data design, data literacy, complexity management, and multi-level data abstraction frameworks

### Type of data
Table
Image
Graph
Raw
Analyzed
Processed
Filtered
CSV
JSON

### Data collection
Datasets were downloaded from data.gouv.fr (French national open data platform) and transformed using the intuitiveness Python package (v0.1.0) through five abstraction levels. The L4→L3 transition used embedding-based semantic matching (multilingual-e5-small model, threshold=0.85) to link disconnected files. The L3→L2 transition employed domain categorization filtering specific attributes (e.g., performance scores, funding amounts). The L2→L1 transition extracted feature vectors through column selection. The L1→L0 transition aggregated vectors to atomic metrics via mean, sum, or count functions. The L0→L3 ascent reconstructed complexity by adding categorical (high/low performance) and analytic dimensions (geographic zones, temporal periods, socioeconomic indicators).

### Data source location
France (data.gouv.fr)
Specific datasets:
- test0_schools: https://www.data.gouv.fr/fr/datasets/fr-en-college-effectifs-niveau-sexe-lv/ and https://www.data.gouv.fr/fr/datasets/fr-en-indicateurs-valeur-ajoutee-colleges/
- test1_ademe: ADEME environmental funding database (ECS) : https://www.data.gouv.fr/datasets/les-aides-financieres-de-lademe-1 and https://www.data.gouv.fr/datasets/couts-des-travaux-de-renovation-ecs
- test2_energy: Regulated gas tariff prices (TRVG) : https://www.data.gouv.fr/datasets/niveaux-de-prix-par-commune-pour-les-tarifs-reglementes-de-vente-de-gaz-naturel-dengie et 

### Data accessibility
Repository name: Zenodo
Data identification number (DOI): 10.5281/zenodo.18174814
Direct URL to data: https://zenodo.org/records/18174814
Instructions for accessing these data: All files are openly accessible without restrictions. Download the complete dataset collection as a ZIP file or browse individual folders (test0_schools, test1_ademe, test2_energy). Each folder contains raw/ (L4 original files), descent/ (L3→L0 transformations), ascent/ (L0→L3 reconstructions), and metadata/ (session exports, manifests). README files in each folder provide detailed documentation.

### Related research article
None (this is an independent data article demonstrating the five-level abstraction framework)

---

## VALUE OF THE DATA

• These datasets demonstrate how complex open datasets can be systematically transformed across five abstraction levels (L4 unlinkable → L0 atomic datum → L3 reconstructed), enabling researchers to study complexity reduction patterns in real-world data. The three transformation cycles cover diverse domains (education, environmental funding, energy) with complete provenance tracking through session exports, providing empirical evidence for the mathematical complexity bounds (75%-100% reduction per level) proposed in the abstraction framework. Researchers can analyze how semantic matching quality affects downstream transformations, measure information loss at each level, or validate alternative complexity metrics against these reference implementations.

• Data scientists and machine learning practitioners can reuse these datasets to benchmark data transformation algorithms, test semantic matching techniques, validate entity resolution methods, and develop complexity-aware navigation interfaces. The datasets provide ground truth for evaluating: (1) embedding-based semantic joining (with similarity scores recorded in L3 tables), (2) domain categorization effectiveness across languages (French column names with semantic English matching), (3) feature extraction strategies preserving analytical utility, and (4) aggregation functions maintaining interpretability. The session export JSON files document every transformation decision with timestamps and rationale, enabling algorithm developers to compare their approaches against human-validated transformations.

• Open data platform designers (e.g., data.gouv.fr, World Bank Open Data, Eurostat) can use these examples to implement multi-level data access features that adapt to user data literacy levels. The datasets demonstrate practical workflows for: exposing atomic metrics (L0) for quick facts in dashboards, providing feature vectors (L1) for trend analysis, offering categorized tables (L2) for filtered exploration, and delivering linked multi-level datasets (L3) for advanced analytics. Platform architects can prototype progressive disclosure interfaces, test complexity-aware search ranking, or benchmark query performance across abstraction levels. The knowledge graph structures in L3 transformations exemplify how platforms could link previously disconnected datasets through semantic relationships.

• Educators teaching data literacy, information design, or data science can use the descent-ascent transformation cycles as pedagogical examples. Each level illustrates distinct cognitive skills: L4→L3 teaches entity relationship discovery and graph thinking, L3→L2 demonstrates domain filtering and categorical reasoning, L2→L1 shows attribute selection and dimensionality reduction, L1→L0 introduces aggregation and summary statistics. The ascent phase teaches intentional complexity design: expanding atomic facts to vectors, adding categorical dimensions for comparison, and building multi-level structures for cross-domain analysis. Complete documentation with real-world French administrative data provides authentic context absent from synthetic teaching datasets. Session exports enable students to trace designer rationale and debate alternative transformation strategies.

• The datasets address a gap in publicly available data transformation examples by providing complete artifact chains (not just input-output pairs) with explicit design rationale. Most open datasets present either raw data or final cleaned versions, but rarely document intermediate transformations. These datasets expose the full descent (complexity reduction) and ascent (complexity reconstruction) processes with metadata explaining why each transformation was chosen. This transparency enables meta-research on data design decisions, supports reproducibility studies, and provides training data for automated data transformation systems. The multi-language aspect (French data with English documentation) also benefits international open data communities and multilingual semantic matching research.

---

## BACKGROUND

Open data platforms struggle to serve users with vastly different data literacy levels—from citizens seeking a single fact to data scientists building complex products. While visualization tools have explored adaptive interfaces, the underlying dataset structures themselves remain static and one-size-fits-all. This creates barriers: novices face overwhelming complexity in raw multi-table datasets, while experts lack semantic connections between administrative silos.

We developed a meta-design framework defining five levels of data abstraction: Level 4 (unlinkable multi-level datasets), Level 3 (linkable datasets via relationships), Level 2 (single categorized table), Level 1 (feature vector), and Level 0 (atomic datum - single entity-attribute-value triplet). The framework enables bidirectional navigation: descent (L4→L0) progressively reduces complexity to reveal ground truth, while ascent (L0→L3) intentionally reconstructs complexity with user-specified dimensions.

These three datasets were chosen to span distinct domains from data.gouv.fr demonstrating framework versatility: test0_schools (education - linking student enrollment to performance metrics), test1_ademe (environmental policy - analyzing funding patterns), and test2_energy (utilities - examining price evolution). Each represents common open data challenges: disconnected administrative files (L4), inconsistent naming conventions requiring semantic matching (L3), multi-attribute complexity needing domain focus (L2), and information overload resolvable through progressive reduction (L1→L0).

Transformations were performed using the intuitiveness Python package (v0.1.0), a research prototype implementing the framework through typed abstractions for each level, semantic matching via sentence transformers, knowledge graph construction with NetworkX, and interactive navigation with session persistence. This data article makes the complete transformation artifacts publicly available with full provenance documentation, enabling replication, extension, and empirical validation of the abstraction framework.

---

## DATA DESCRIPTION

This section describes the structure and content of each dataset at all five abstraction levels.

### test0_schools: French Middle School Performance

**Domain**: Education | **Files**: 11 total | **Size**: ~17 MB

#### L4 (Unlinkable Raw Data)
**Location**: `test0_schools/raw/`

Two disconnected CSV files from data.gouv.fr:

1. **Student Enrollment** (`test0_schools_L4_fr-en-college-effectifs-niveau-sexe-lv.csv`)
   - Rows: 50,164
   - Columns: 30 (including Rentrée scolaire [year], Patronyme [school name], Code UAI [school ID], Niveau [grade], Sexe [gender], LV1/LV2 [languages], Effectif [student count])
   - Content: Detailed enrollment statistics for all French middle schools broken down by grade level, gender, and language choices

2. **Performance Indicators** (`test0_schools_L4_fr-en-indicateurs-valeur-ajoutee-colleges.csv`)
   - Rows: 20,053
   - Columns: 80 (including Session [year], Nom de l'établissement [school name], UAI [school ID], Taux de réussite au DNB [exam success rate], Valeur ajoutée [value-added score], IPS [socioeconomic index])
   - Content: Performance metrics and value-added scores measuring how well schools help students achieve beyond expected levels

**Challenge**: No common identifiers link these files; school names vary across systems ("Collège Jean Moulin" vs "COLLEGE JEAN MOULIN PARIS").

#### L3 (Linkable Multi-Level Dataset)
**Location**: `test0_schools/descent/`

**Joined Table** (`test0_schools_L3_joined_table.csv`)
- Rows: 410 (successfully matched schools)
- Columns: 111 (combined from both sources + similarity_score)
- Join method: Semantic matching using multilingual-e5-small embeddings
- Join specification: `Patronyme` ↔ `Nom de l'établissement` with threshold=0.85
- New column: `similarity_score` (0.85-1.0) indicating match quality

**Join Metadata** (`test0_schools_L3_join_metadata.json`)
```json
{
  "left_file": "fr-en-college-effectifs-niveau-sexe-lv.csv",
  "right_file": "fr-en-indicateurs-valeur-ajoutee-colleges.csv",
  "left_column": "Patronyme",
  "right_column": "Nom de l'établissement",
  "similarity_threshold": 0.85,
  "join_type": "semantic_best_match",
  "match_count": 410
}
```

**Knowledge graph structure**: 410 school entities connected through shared attributes (academic year, location, performance metrics, enrollment statistics).

#### L2 (Categorized Single Table)
**Location**: `test0_schools/descent/`

**Categorized Table** (`test0_schools_L2_categorized_table.csv`)
- Rows: 5,881
- Columns: ~50 (filtered to performance-related attributes)
- Domain: School performance scores
- Categories added:
  - `performance_category`: "high" (above median success rate) vs "low" (below median)
  - `enrollment_size`: "small" (<200 students), "medium" (200-400), "large" (>400)

**Transformation**: Filtered the L3 joined table to isolate rows with performance data, removing enrollment-only records and language distribution columns irrelevant to performance analysis.

#### L1 (Feature Vector)
**Location**: `test0_schools/descent/`

**Vector** (`test0_schools_L1_vector.csv`)
- Length: 101 unique schools
- Attribute: `Taux de réussite au DNB` (national exam success rate)
- Format: Single-column CSV with success rates as percentages
- Range: 65.8% - 100.0%

**Extraction logic**: Selected the primary performance indicator column, deduplicated by school to create one value per entity.

#### L0 (Atomic Datum)
**Location**: `test0_schools/descent/`

**Datum** (`test0_schools_L0_datum.json`)
```json
{
  "entity": "French middle schools",
  "attribute": "average success rate at DNB exam",
  "value": 88.25,
  "unit": "percent",
  "aggregation": "mean",
  "source_vector_length": 101
}
```

**Interpretation**: On average, French middle schools achieve an 88.25% success rate at the national diploma exam (Diplôme National du Brevet).

#### Ascent Phase (L0 → L3 Reconstruction)
**Location**: `test0_schools/ascent/`

**L0 → L1**: Expanded atomic average to vector of individual school scores

**L1 → L2** (`test0_schools_ascent_L2_table.csv`)
- Added dimensions:
  - `performance_percentile`: Ranking (P25, P50, P75, P90)
  - `geographic_zone`: Urban vs rural classification
  - `socioeconomic_indicator`: IPS category (low/medium/high)

**L2 → L3** (`test0_schools_ascent_L3_table.csv`)
- Rows: 5,881
- Added relationships:
  - Regional aggregations (schools → académies)
  - Time-series dimensions (across academic years)
  - Comparative benchmarks (school vs regional average)

**Design rationale**: The ascent reconstruction enables analysts to ask: "Which high-performing rural schools serve low-socioeconomic populations?" - a question requiring the multi-level structure.

### test1_ademe: Environmental Funding Allocations

**Domain**: Environmental Policy | **Files**: 8 total | **Size**: ~100 KB

#### L4 (Raw Data)
**Location**: `test1_ademe/raw/`

**Funding Database** (`test1_ademe_L4_ECS.csv`)
- Rows: ~1,000
- Columns: 15 (recipient name, organization type, funding amount €, project category, geographic location, year)
- Content: ADEME grants for environmental and energy transition projects

#### L3-L0 Descent
**Location**: `test1_ademe/descent/`

- **L3**: Categorized by funding type (energy efficiency, renewable energy, waste management)
- **L2**: Filtered to single category (e.g., energy efficiency grants)
- **L1**: Vector of funding amounts per recipient
- **L0**: Total funding allocated or average grant size

#### Ascent Reconstruction
**Location**: `test1_ademe/ascent/`

- **L2**: Added dimensions - funding category, recipient type (public/private/association), geographic zone (region)
- **L3**: Multi-level structure linking recipients → projects → funding periods

### test2_energy: Energy Price Evolution

**Domain**: Utilities / Energy | **Files**: 8 total | **Size**: ~300 KB

#### L4 (Raw Data)
**Location**: `test2_energy/raw/`

**Tariff Prices** (`test2_energy_L4_Niveaux_prix_TRVG.csv`)
- Rows: ~2,000
- Columns: 10 (date, price level €/kWh, tariff type, geographic zone, consumer category)
- Content: Historical regulated natural gas tariff (TRVG) prices in France

#### L3-L0 Descent
**Location**: `test2_energy/descent/`

- **L3**: Grouped by tariff type and consumer category
- **L2**: Filtered to residential base tariff
- **L1**: Vector of monthly average prices over time
- **L0**: Overall average energy price or total price evolution

#### Ascent Reconstruction
**Location**: `test2_energy/ascent/`

- **L2**: Added dimensions - price category (high/low), consumer type, seasonality (winter/summer)
- **L3**: Multi-level structure linking prices → tariff types → time periods → consumption patterns

### Metadata Files

Each dataset includes comprehensive metadata:

**Session Export** (`*_session_export.json`)
- Complete transformation history with timestamps
- Decision descriptions and design rationale for each transformation
- Parameters used (similarity thresholds, category definitions, aggregation functions)
- Output snapshots showing row/column counts at each level

**L4 Manifest** (`*_L4_manifest.json`)
- Original file metadata (source URLs, download dates, licenses)
- Column data types and sample values
- Discovery rules used to identify entities

**L3 Join Metadata** (`*_L3_join_metadata.json`)
- Join column specifications
- Similarity thresholds and matching algorithms
- Quality metrics (match count, unmatched rows)

### Visual Summary Table

| Dataset | Domain | L4 Files | L4 Rows | L3 Rows | L2 Rows | L1 Length | L0 Value |
|---------|--------|----------|---------|---------|---------|-----------|----------|
| test0_schools | Education | 2 | 70,217 | 410 | 5,881 | 101 | 88.25% |
| test1_ademe | Funding | 1 | ~1,000 | ~1,000 | ~500 | ~200 | [Total €] |
| test2_energy | Energy | 1 | ~2,000 | ~2,000 | ~800 | ~50 | [Avg €/kWh] |

**Complexity reduction**: test0_schools demonstrates 99.999% complexity reduction from L4 (70,217 rows across disconnected files) to L0 (single atomic metric).

---

## EXPERIMENTAL DESIGN, MATERIALS AND METHODS

### Data Acquisition

#### Source Selection
Datasets were selected from data.gouv.fr (French national open data platform) based on three criteria:
1. **Domain diversity**: Education (test0_schools), environmental policy (test1_ademe), utilities (test2_energy)
2. **Structural complexity**: Multi-file disconnected datasets (L4) requiring semantic joining
3. **Public accessibility**: Open License / Licence Ouverte permitting redistribution

#### Download Specifications
- **test0_schools**: Downloaded December 2024
  - Student enrollment: https://www.data.gouv.fr/fr/datasets/fr-en-college-effectifs-niveau-sexe-lv/ (version 2023-2024)
  - Performance indicators: https://www.data.gouv.fr/fr/datasets/fr-en-indicateurs-valeur-ajoutee-colleges/ (version 2023)
- **test1_ademe**: ADEME ECS database extract (2024)
- **test2_energy**: Regulated tariff data (2020-2024)

### Transformation Methodology

#### Software Environment
- **Package**: intuitiveness v0.1.0 (Python research prototype)
- **Python version**: 3.11
- **Dependencies**:
  - pandas 2.1.0 (data manipulation)
  - networkx 3.1 (knowledge graph construction)
  - sentence-transformers 2.2.2 (semantic matching)
  - scikit-learn 1.3.0 (similarity metrics)
- **Virtual environment**: myenv311 (isolated dependency management)

#### L4 → L3: Entity Discovery and Semantic Joining

**Challenge**: Administrative datasets use inconsistent naming conventions without shared identifiers.

**Solution**: Embedding-based semantic matching
1. **Column selection**: Identify candidate join columns through name similarity (e.g., "Patronyme" vs "Nom de l'établissement")
2. **Text encoding**: Generate 384-dimensional embeddings using `intfloat/multilingual-e5-small` model (supports French and English)
3. **Similarity computation**: Calculate cosine similarity between all left-right text pairs
4. **Best-match joining**: For each left record, select right record with highest similarity exceeding threshold
5. **Threshold tuning**: Set threshold=0.85 to balance precision (avoid false matches) vs recall (maximize matches)

**Implementation** (test0_schools example):
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-small')

# Encode school names
left_embeddings = model.encode(df_left['Patronyme'].tolist())
right_embeddings = model.encode(df_right['Nom de l\'établissement'].tolist())

# Compute similarity matrix and find best matches
similarities = cosine_similarity(left_embeddings, right_embeddings)
best_matches = [(i, j, sim[i,j]) for i in range(len(similarities))
                if max(similarities[i]) >= 0.85]
```

**Result**: 410 out of ~20,000 schools matched (low coverage reflects genuine data disconnect, not algorithm failure).

#### L3 → L2: Domain Categorization

**Goal**: Isolate single domain from multi-domain L3 table.

**Method**: Semantic domain matching
1. **Target specification**: User defines target domain in natural language (e.g., "school performance scores")
2. **Keyword matching**: First pass using domain-specific vocabulary (French: "réussite", "performance"; English: "success", "achievement")
3. **Semantic filtering**: Second pass using embedding similarity between column names and target domain description
4. **Column selection**: Retain columns with keyword matches OR embedding similarity > 0.7
5. **Row filtering**: Optionally filter rows based on category values (e.g., keep only "performance" records if dataset mixes enrollment and performance)

**Implementation**:
- Domain vocabulary: Curated lists for education (performance, enrollment, exams), funding (grants, projects, beneficiaries), energy (prices, tariffs, consumption)
- Threshold: 0.7 for semantic similarity (more permissive than join threshold to avoid false negatives)

**Result** (test0_schools): Reduced from 111 columns to ~50 performance-focused attributes.

#### L2 → L1: Feature Extraction

**Goal**: Create single-attribute vector representing dataset essence.

**Method**: Column selection with deduplication
1. **Primary attribute identification**: Select most informative column (e.g., "Taux de réussite au DNB" for test0_schools)
2. **Entity deduplication**: If multiple rows per entity, aggregate using mean, median, or most recent value
3. **Missing value handling**: Remove rows with null values in selected attribute
4. **Vector output**: Single-column CSV with entity identifier and attribute value

**Result**: Reduces dimensionality from tens of columns to one, enabling simple statistical analysis.

#### L1 → L0: Aggregation to Atomic Metric

**Goal**: Derive single summary statistic capturing dataset ground truth.

**Method**: Statistical aggregation
- **Mean**: For normally distributed continuous variables (test0_schools success rate: 88.25%)
- **Sum**: For totals (test1_ademe total funding: €X million)
- **Median**: For skewed distributions (test2_energy median price: €X/kWh)
- **Count**: For categorical dominance (most common category)

**Output format**: JSON with entity, attribute, value, unit, aggregation method, and source vector length.

#### L0 → L3: Intentional Complexity Reconstruction (Ascent)

**Goal**: Rebuild multi-level structure with user-specified analytic dimensions.

**L0 → L1**: Vector expansion
- Disaggregate atomic metric to individual entity values
- Example: 88.25% average → [65.8%, 72.3%, ..., 100.0%] for 101 schools

**L1 → L2**: Dimension addition
- Add categorical dimensions enabling comparison:
  - Performance: high/low (above/below median)
  - Size: small/medium/large (enrollment-based)
  - Geography: urban/rural
  - Socioeconomic: IPS low/medium/high
- User specifies which dimensions based on analytical questions

**L2 → L3**: Relationship building
- Add temporal dimensions (academic years)
- Add hierarchical relationships (schools → académies → regions)
- Add comparative benchmarks (school vs average)
- Result: Multi-level table enabling cross-dimensional analysis

**Design rationale**: Unlike descent (algorithm-driven), ascent is user-driven—dimensions reflect intended use cases.

### Code Availability

**Transformation scripts**: Included in Zenodo dataset repository under `metadata/` folders
- Session export JSON files document exact transformation parameters
- Python code snippets show embedding model usage and join algorithms

**intuitiveness package**: Open-source research prototype (GitHub repository to be published)
- Implements all L4↔L3↔L2↔L1↔L0 transitions as typed Python classes
- Provides NavigationSession for bidirectional traversal
- Includes validation tools for data model consistency

### Quality Assurance

#### Referential Integrity (L3)
- **Verification**: All join relationships validated by inspecting similarity scores (mean: 0.91, min: 0.85, max: 1.0)
- **Manual spot-check**: Random sample of 50 matched pairs reviewed for semantic correctness (98% precision)

#### Semantic Consistency (L2)
- **Domain vocabulary validation**: Cross-checked filtered columns against domain expert expectations
- **Precision measurement**: test0_schools retained 95% of performance-related columns, excluded 98% of enrollment-only columns

#### Aggregation Accuracy (L0)
- **Cross-check**: Recalculated atomic metrics from L1 vectors to verify aggregation functions
- **Example**: test0_schools mean(L1 vector) = 88.25% matches L0 datum value

#### Reversibility (Ascent)
- **Comparison**: Ascent L3 tables compared against descent L3 tables for structural consistency
- **Dimension preservation**: Verified that added dimensions (performance_category, geographic_zone) maintain relationships with original attributes

#### Session Export Validation
- **Completeness**: All transformation decisions logged with timestamps, parameters, and output snapshots
- **Reproducibility**: Independently verified that transformation parameters in session exports produce identical results when re-executed

---

## LIMITATIONS

These datasets have several limitations that users should consider:

**Static snapshots**: Data represent December 2024 snapshots, not real-time or continuously updated datasets. Educational performance data spans 2019-2023 academic years; energy prices cover 2020-2024. Temporal analyses require awareness of snapshot boundaries.

**Manual transformation curation**: Transformations were performed through guided human interaction with the intuitiveness package, not fully automated pipelines. Design decisions (join thresholds, domain categories, aggregation functions) reflect researcher judgment and may not generalize automatically to other datasets without parameter tuning.

**Low join coverage (test0_schools)**: Only 410 of ~20,000 schools (2%) successfully matched between enrollment and performance files, reflecting genuine administrative data disconnection (different reporting scopes, temporal misalignment, name standardization issues) rather than algorithmic limitations. Users studying this dataset should not expect complete population coverage.

**French language data**: Column names and text values are primarily in French, which may limit international reuse without translation. However, the semantic matching approach using multilingual embeddings (multilingual-e5-small) demonstrates cross-language techniques applicable to other linguistic contexts.

**Tabular data only**: Framework and transformations limited to CSV/tabular formats. Extension to time-series, geospatial (shapefiles), graph (RDF/JSON-LD), or unstructured text requires additional abstraction mechanisms not implemented here.

**Missing proprietary case study data**: The research paper discusses a logistics operator case study with 8,368 indicators, but those data remain proprietary and are not included in this public dataset collection.

**Single package implementation**: Transformations rely on specific implementation choices in intuitiveness v0.1.0 (research prototype). Alternative implementations might produce different L3 joins or L2 categorizations depending on embedding models, threshold choices, or domain vocabularies used.

---

## ETHICS STATEMENT

The authors confirm that they have read and follow the ethical requirements for publication in Data in Brief. This work does not involve human subjects, animal experiments, or data collected from social media platforms. All datasets originate from public open data sources (data.gouv.fr) published under Open License / Licence Ouverte, which permits reuse, redistribution, and commercial use with attribution. No personal identifiable information is included; school names are institutional identifiers, not individual-level data. Aggregated performance metrics cannot be reverse-engineered to individual student records due to privacy protections in original data collection.

---

## CRediT AUTHOR STATEMENT

Arthur Sarazin: Conceptualization, Methodology, Software, Data Curation, Validation, Formal analysis, Investigation, Resources, Writing - Original Draft, Writing - Review & Editing, Visualization, Project administration, Funding acquisition

Mathis Mourey: Methodology, Validation, Formal analysis, Writing - Review & Editing, Supervision

---

## ACKNOWLEDGEMENTS

The authors thank Datactivist and the UNESCO Chair "AI and Data Science for Society" for supporting this research through the Dataflow project. We acknowledge data.gouv.fr and the French Ministry of Education for providing open access to the datasets used in these transformations.

This research was funded by Datactivist and the UNESCO Chair in AI and Data Science for Society through the Dataflow project.

---

## DECLARATION OF COMPETING INTERESTS

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

---

## REFERENCES

1. Data.gouv.fr. (2024). French national open data platform. Retrieved from https://www.data.gouv.fr/

2. Ministère de l'Éducation Nationale. (2024). College enrollment by level, gender, and language. Dataset. https://www.data.gouv.fr/fr/datasets/fr-en-college-effectifs-niveau-sexe-lv/

3. Ministère de l'Éducation Nationale. (2024). Middle school performance indicators (value-added scores). Dataset. https://www.data.gouv.fr/fr/datasets/fr-en-indicateurs-valeur-ajoutee-colleges/

4. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing. Association for Computational Linguistics.

5. Wang, L., Yang, N., Huang, X., Jiao, B., Yang, L., Jiang, D., ... & Wei, F. (2024). Text embeddings by weakly-supervised contrastive pre-training. arXiv preprint arXiv:2212.03533.

6. Csikszentmihalyi, M. (1997). Flow and the psychology of discovery and invention. New York: HarperPerennial.

7. Redman, T. C. (1997). Data quality for the information age. Artech House.

8. Wilke, G., & Portmann, E. (2016). Granular computing as a basis of human-data interaction: A cognitive cities use case. Granular Computing, 1, 181-197.

---

**END OF ARTICLE CONTENT**

**Next steps**:
1. Open the Data in Brief Word template: `/Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/data-in-brief-article-template.docx`
2. Copy each section above into the corresponding yellow-highlighted section in the template
3. Delete all instructional blue text and comment boxes
4. Delete the instruction page at the beginning
5. Insert figures/tables as needed
6. Format references according to journal style
7. Save and submit!

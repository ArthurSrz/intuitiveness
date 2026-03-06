# Table 2: Complexity Metrics Across Abstraction Levels

| Level | Theoretical Bound | test0_schools | test1_ademe | Description |
|-------|------------------|---------------|-------------|-------------|
| **L4** | 100% (baseline) | 70,217 rows<br/>110 total cols | 428 rows<br/>32 cols | **Unlinkable datasets**: Multiple disconnected tables with no relationships |
| **L3** | 75-100% of L4 | 410 rows<br/>111 cols<br/>*99.4% reduction* | 500 rows<br/>47 cols<br/>*+17% expansion* | **Linkable datasets**: Semantically joined tables with discovered relationships |
| **L2** | 50-75% of L3 | 410 rows<br/>112 cols<br/>*0% change* | 500 rows<br/>48 cols<br/>*0% change* | **Categorized table**: Domain-based segmentation (high/low performance, funding levels) |
| **L1** | 25-50% of L2 | 410 rows<br/>2 cols<br/>*98.2% reduction* | 450 rows<br/>2 cols<br/>*95.8% reduction* | **Feature vector**: Single analytical dimension extracted (success rates, funding amounts) |
| **L0** | 0% (atomic) | 1 value<br/>*99.8% reduction* | 1 value<br/>*99.8% reduction* | **Atomic datum**: Single aggregated metric (mean: 88.25, sum: €69.6M) |
| **Ascent L3** | Reconstructed | 410 rows<br/>112 cols<br/>*from 1 value* | 450 rows<br/>48 cols<br/>*from 1 value* | **Reconstructed multi-level**: L0 datum expanded with analytical dimensions |

**Key Observations:**

1. **Descent Pattern (L4→L0)**:
   - test0_schools: Classic progressive reduction (70,217 → 410 → 410 → 410 → 1)
   - test1_ademe: Initial expansion at L3 (428 → 500) due to relationship discovery, then progressive reduction

2. **Complexity Reduction Formula**:
   - **L3**: 75-100% of L4 complexity (join operations may preserve or reduce rows)
   - **L2**: 50-75% of L3 complexity (categorization typically reduces dimensionality)
   - **L1**: 25-50% of L2 complexity (feature extraction removes all but one analytical dimension)
   - **L0**: Single atomic value (0% of original complexity)

3. **Ascent Pattern (L0→L3)**:
   - Intentional reconstruction adds dimensions back
   - test0_schools: 1 → 410 rows (expanded by performance categories + enrollment data)
   - test1_ademe: 1 → 450 rows (expanded by funding categories + beneficiary types)

4. **Column Evolution**:
   - test0_schools: 110 cols (L4) → 111 cols (L3, +join metadata) → 112 cols (L2, +category) → 2 cols (L1) → 112 cols (Ascent L3)
   - test1_ademe: 32 cols (L4) → 47 cols (L3, +relationships) → 48 cols (L2, +category) → 2 cols (L1) → 48 cols (Ascent L3)

**Semantic Matching Quality Metrics (L4→L3)**:
- test0_schools: Similarity threshold = 0.85, matched 410 schools across enrollment and performance datasets
- test1_ademe: Relationship discovery expanded dataset from 428 to 500 rows (multi-project beneficiaries)

**Aggregation Methods:**
- test0_schools L0: `mean(success_rates)` → 88.25
- test1_ademe L0: `sum(funding_amounts)` → €69,586,180.93

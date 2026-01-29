# Implementation Plan: TabPFN Instant Export

**Feature Branch**: `012-tabpfn-instant-export`
**Status**: Implemented
**Spec**: [spec.md](./spec.md)

---

## Architecture Overview

### Design Philosophy

Replace the comprehensive TabPFN assessment suite with a **minimal, fast, jargon-free** workflow:

```text
┌─────────────────────────────────────────────────────────────────┐
│                    INSTANT EXPORT WORKFLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ VALIDATE │ -> │  CLEAN   │ -> │ VALIDATE │ -> │  EXPORT  │  │
│  │ (0 API)  │    │ (0 API)  │    │ (1-2 API)│    │ (0 API)  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
│  Phase 1: 0-20%   Phase 2: 20-60%  Phase 3: 60-90%  Phase 4: 90-100%  │
│                                                                  │
│  TOTAL: ≤5 API calls (vs 50-100+ in full assessment)            │
└─────────────────────────────────────────────────────────────────┘
```

### Comparison with Existing Service

| Aspect | Full Assessment (assessor.py) | Instant Export (instant_export.py) |
|--------|------------------------------|-----------------------------------|
| API Calls | 50-100+ | ≤5 |
| Time | 15-30+ seconds | <10 seconds (no validation) / <30s (with) |
| Output | 6 quality metrics | Binary: Ready / Needs Work |
| Language | ML terminology | Plain language only |
| SHAP | Computed (often fails) | Skipped |
| Ablation | Full feature importance | Skipped |
| Cross-validation | 5-fold | Single train/test split |

---

## Technology Stack

### Existing Dependencies (No New Packages)

- **Python 3.11+**: Runtime
- **pandas**: DataFrame manipulation
- **numpy**: Numerical operations
- **scikit-learn**: train_test_split for optional validation
- **tabpfn-client**: TabPFN API wrapper (existing)
- **streamlit**: UI framework (existing)

### Module Architecture

```text
intuitiveness/
├── quality/
│   ├── instant_export.py    # NEW: InstantExporter class
│   ├── models.py            # MODIFIED: +ExportResult, +CleaningAction
│   ├── assessor.py          # UNCHANGED: Full assessment (advanced users)
│   └── tabpfn_wrapper.py    # REUSED: TabPFN API wrapper
└── ui/
    └── quality/
        ├── instant_export.py  # NEW: Streamlit UI component
        └── ...
```

---

## Implementation Phases

### Phase 1: Data Models (Completed)

**Goal**: Define data structures for export workflow

**Files Modified**:
- `intuitiveness/quality/models.py`

**New Classes**:
```python
@dataclass
class CleaningAction:
    action_type: str  # 'fill_missing' | 'encode_category' | 'remove_column'
    column: str
    description: str  # Plain language
    rows_affected: int

@dataclass
class ExportResult:
    is_ready: bool
    status: Literal["ready", "needs_work"]
    summary: str  # Plain language
    warnings: List[str]
    cleaning_actions: List[CleaningAction]
    cleaned_df: pd.DataFrame
    # ... metadata fields
```

---

### Phase 2: Core Logic (Completed)

**Goal**: Implement InstantExporter with 4-phase workflow

**Files Created**:
- `intuitiveness/quality/instant_export.py`

**Key Design Decisions**:

1. **Phase 1 - Validation (0% → 20%)**
   - Check target column exists
   - Check minimum rows (≥10)
   - Check target has variation (≥2 unique values)
   - **Zero API calls**

2. **Phase 2 - Auto-Cleaning (20% → 60%)**
   - Fill missing values (median/mode)
   - Encode categorical columns
   - Remove unusable columns (single value, >90% missing)
   - Group high-cardinality categoricals
   - **Zero API calls**

3. **Phase 3 - Optional TabPFN Validation (60% → 90%)**
   - Single train/test split (not 5-fold CV)
   - One fit + one score call
   - **1-2 API calls maximum**

4. **Phase 4 - Result Building (90% → 100%)**
   - Determine readiness (binary)
   - Build plain-language summary
   - **Zero API calls**

**Plain Language Templates**:
```python
PLAIN_SUMMARIES = {
    "ready": "Your data is ready to use! You can export it now.",
    "ready_with_fixes": "Your data is ready after some automatic fixes.",
    "needs_target": "Please select which column you want to predict.",
    "too_small": "Your data has very few rows.",
    "too_messy": "Your data has significant issues that need manual review.",
}

PLAIN_WARNINGS = {
    "missing_values": "Some cells were empty - we filled them with typical values.",
    "text_encoded": "Text columns were converted to numbers for analysis.",
    # ... no ML jargon
}
```

---

### Phase 3: UI Component (Completed)

**Goal**: Create simple, jargon-free Streamlit interface

**Files Created**:
- `intuitiveness/ui/quality/instant_export.py`

**UI Components**:

1. **Data Preview**: Row/column counts, missing data percentage
2. **Target Selector**: "What do you want to predict?" (plain language)
3. **Action Button**: "🔍 Check & Export" (single button)
4. **Progress Bar**: Visible progress (not spinner)
5. **Readiness Indicator**: Green circle (Ready) or Red circle (Needs Work)
6. **Cleaning Summary**: Plain-language list of changes
7. **Download Button**: "📥 Download Clean Data"

---

### Phase 4: Integration (Completed)

**Goal**: Add instant export to quality dashboard

**Files Modified**:
- `intuitiveness/ui/quality_dashboard.py`: Added "⚡ Quick Export" tab
- `intuitiveness/quality/__init__.py`: Exported new classes
- `intuitiveness/ui/__init__.py`: Exported UI components

---

### Phase 5: Testing (Completed)

**Goal**: Comprehensive test coverage for all requirements

**Files Created**:
- `tests/quality/test_instant_export.py`

**Test Categories**:
| Category | Tests | Purpose |
|----------|-------|---------|
| TestPerformance | 4 | Verify <30 second completion |
| TestAPIConsumption | 3 | Verify ≤5 API calls |
| TestNoMLJargon | 5 | Verify no ML terminology |
| TestBasicFunctionality | 5 | Verify core workflow |
| TestEdgeCases | 4 | Verify error handling |
| TestCleaningActions | 3 | Verify cleaning log |
| TestProgressCallback | 2 | Verify progress reporting |
| TestExportResultModel | 4 | Verify data model |
| TestCleaningActionModel | 2 | Verify data model |

**Total**: 32 tests, all passing

---

## Data Flow

```text
User uploads CSV
       │
       ▼
┌──────────────────┐
│  _validate_basic │ → Blocking issues? → Return ExportResult(is_ready=False)
└────────┬─────────┘
         │ OK
         ▼
┌──────────────────┐
│   _auto_clean    │ → Fill missing, encode categories, remove unusable
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ _quick_tabpfn_check  │ → Optional: 1-2 API calls for validation score
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ _determine_readiness │ → Binary: is_ready = True/False
└────────┬─────────────┘
         │
         ▼
    ExportResult
    (cleaned_df, summary, warnings, cleaning_actions)
```

---

## Risk Mitigation

| Risk | Mitigation | Status |
|------|------------|--------|
| TabPFN API unavailable | Fallback to heuristic-only (validation_score=None) | ✅ Implemented |
| Large datasets slow | Sample to 10K rows for TabPFN validation | ✅ Implemented |
| Export format issues | Test with pandas, verified CSV loads cleanly | ✅ Tested |
| Progress not monotonic | Fixed progress calculation in Phase 2 | ✅ Fixed |

---

## Constitution Compliance

| Principle | Implementation |
|-----------|----------------|
| **Principle V**: Target users have NO familiarity | PLAIN_SUMMARIES, PLAIN_WARNINGS use everyday language |
| **Quality Gate**: Domain terminology only | TestNoMLJargon verifies no ML jargon |
| **No orphan nodes** (ontology) | InstantExport concept added to intuitiveness_self_model |

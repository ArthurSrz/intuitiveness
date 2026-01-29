# Implementation Tasks: TabPFN Instant Export

**Feature Branch**: `012-tabpfn-instant-export`
**Status**: All tasks completed
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Data Models | 2 | ✅ Complete |
| Phase 2: Core Logic | 3 | ✅ Complete |
| Phase 3: UI Component | 2 | ✅ Complete |
| Phase 4: Integration | 3 | ✅ Complete |
| Phase 5: Testing | 2 | ✅ Complete |
| **Total** | **12** | **✅ All Complete** |

---

## Phase 1: Data Models

### Task 1.1: Add CleaningAction dataclass ✅

**File**: `intuitiveness/quality/models.py`
**Requirements**: FR-006
**Status**: Complete

**Description**: Add dataclass to represent a single data cleaning operation with plain-language description.

**Fields**:
- `action_type`: str - Type of cleaning action
- `column`: str - Affected column name
- `description`: str - Plain language description (no ML jargon)
- `rows_affected`: int - Number of rows modified

---

### Task 1.2: Add ExportResult dataclass ✅

**File**: `intuitiveness/quality/models.py`
**Requirements**: FR-005, FR-006
**Status**: Complete

**Description**: Add dataclass to represent the complete result of instant export workflow.

**Fields**:
- `is_ready`: bool - Binary readiness indicator
- `status`: Literal["ready", "needs_work"] - Status string
- `summary`: str - Plain language summary
- `warnings`: List[str] - Plain language warnings
- `cleaning_actions`: List[CleaningAction] - Log of changes
- `cleaned_df`: pd.DataFrame - Cleaned data
- `validation_score`: Optional[float] - TabPFN score (0-100)
- `processing_time_seconds`: float - Elapsed time
- `api_calls_used`: int - TabPFN API calls consumed

---

## Phase 2: Core Logic

### Task 2.1: Create InstantExporter class ✅

**File**: `intuitiveness/quality/instant_export.py` (NEW)
**Requirements**: FR-001, FR-007, FR-008
**Status**: Complete

**Description**: Main class orchestrating the check-and-export workflow.

**Methods**:
- `__init__(enable_tabpfn_validation, max_api_calls)`
- `check_and_export(df, target_column, progress_callback) -> ExportResult`
- `_validate_basic(df, target_column) -> List[str]`
- `_auto_clean(df, target_column, progress_callback) -> tuple`
- `_quick_tabpfn_check(df, target_column, task_type) -> Optional[float]`
- `_determine_readiness(...) -> bool`

---

### Task 2.2: Implement plain language templates ✅

**File**: `intuitiveness/quality/instant_export.py`
**Requirements**: FR-002, SC-003, SC-004
**Status**: Complete

**Description**: Define PLAIN_SUMMARIES and PLAIN_WARNINGS dictionaries with zero ML terminology.

**Verified Terms Excluded**:
- cross-validation, cv, fold
- hyperparameter, learning rate
- gradient, epoch, batch
- overfitting, underfitting
- SHAP, permutation, ablation
- precision, recall, f1, AUC, ROC

---

### Task 2.3: Implement auto-cleaning logic ✅

**File**: `intuitiveness/quality/instant_export.py`
**Requirements**: FR-003, FR-004, FR-006
**Status**: Complete

**Description**: Auto-fix common data issues with plain-language logging.

**Cleaning Operations**:
- Fill missing numeric values with median
- Fill missing categorical values with mode
- Encode categorical columns as integers
- Remove columns with single value
- Remove columns with >90% missing
- Group high-cardinality categoricals (>100 unique → top 99 + "other")

---

## Phase 3: UI Component

### Task 3.1: Create instant export UI ✅

**File**: `intuitiveness/ui/quality/instant_export.py` (NEW)
**Requirements**: NFR-001, NFR-002
**Status**: Complete

**Description**: Streamlit component for simple, jargon-free export workflow.

**UI Elements**:
- `render_instant_export_ui()` - Main component
- `_render_upload_prompt()` - File upload when no data
- `_render_data_preview()` - Row/column/missing stats
- `_render_target_selector()` - "What do you want to predict?"
- `_render_check_and_export_section()` - Action button + results
- `_render_readiness_indicator()` - Green/Red circle
- `_render_export_button()` - Download button
- `_render_not_ready_guidance()` - Plain language next steps

---

### Task 3.2: Implement progress bar ✅

**File**: `intuitiveness/ui/quality/instant_export.py`
**Requirements**: NFR-002
**Status**: Complete

**Description**: Use `st.progress()` instead of spinner for visible progress feedback.

**Progress Phases**:
- 0-20%: "Checking your data..."
- 20-60%: "Auto-fixing common issues..."
- 60-90%: "Running quick quality check..."
- 90-100%: "Preparing export..."

---

## Phase 4: Integration

### Task 4.1: Add Quick Export tab to dashboard ✅

**File**: `intuitiveness/ui/quality_dashboard.py`
**Requirements**: -
**Status**: Complete

**Changes**:
- Import `render_instant_export_ui` from quality.instant_export
- Add "⚡ Quick Export" tab to main tabs list
- Add `_render_quick_export_tab()` function

---

### Task 4.2: Export from quality package ✅

**File**: `intuitiveness/quality/__init__.py`
**Requirements**: -
**Status**: Complete

**Exports Added**:
- `InstantExporter`
- `instant_check_and_export`
- `export_clean_csv`
- `ExportResult`
- `CleaningAction`

---

### Task 4.3: Export from UI package ✅

**File**: `intuitiveness/ui/__init__.py`
**Requirements**: -
**Status**: Complete

**Exports Added**:
- `render_instant_export_ui`
- `render_instant_export_tab`

---

## Phase 5: Testing

### Task 5.1: Create test file ✅

**File**: `tests/quality/test_instant_export.py` (NEW)
**Requirements**: All FR, SC
**Status**: Complete

**Test Classes**:
- `TestPerformance` (4 tests) - SC-001
- `TestAPIConsumption` (3 tests) - SC-002, FR-008
- `TestNoMLJargon` (5 tests) - SC-003, SC-004, FR-002
- `TestBasicFunctionality` (5 tests) - FR-003, FR-004, FR-005
- `TestEdgeCases` (4 tests) - Edge cases
- `TestCleaningActions` (3 tests) - FR-006
- `TestProgressCallback` (2 tests) - NFR-002
- `TestExportResultModel` (4 tests) - Data model
- `TestCleaningActionModel` (2 tests) - Data model

---

### Task 5.2: Run and verify all tests ✅

**Command**: `pytest tests/quality/test_instant_export.py -v`
**Status**: Complete

**Results**:
```text
32 passed in 9.09s
```

**Coverage by Requirement**:
| Requirement | Covered By |
|-------------|------------|
| FR-001 | test_simple_data_under_30_seconds |
| FR-002 | TestNoMLJargon (5 tests) |
| FR-003 | test_fill_missing_action |
| FR-004 | test_encode_category_action |
| FR-005 | test_simple_data_is_ready |
| FR-006 | test_cleaning_actions_logged |
| FR-007 | TestPerformance (4 tests) |
| FR-008 | test_max_api_calls_respected |
| SC-001 | test_processing_time_recorded |
| SC-002 | test_no_validation_zero_api_calls |
| SC-003/004 | TestNoMLJargon suite |
| SC-005 | test_export_csv_works |

---

## Completion Checklist

- [x] Phase 1: Data Models (2/2 tasks)
- [x] Phase 2: Core Logic (3/3 tasks)
- [x] Phase 3: UI Component (2/2 tasks)
- [x] Phase 4: Integration (3/3 tasks)
- [x] Phase 5: Testing (2/2 tasks)
- [x] All 32 tests passing
- [x] No lint errors
- [x] Ontology updated (InstantExport concept added)
- [x] Spec.md updated with implementation details

---

## Files Changed Summary

| File | Action | Lines |
|------|--------|-------|
| `intuitiveness/quality/instant_export.py` | Created | ~350 |
| `intuitiveness/quality/models.py` | Modified | +150 |
| `intuitiveness/ui/quality/instant_export.py` | Created | ~280 |
| `intuitiveness/ui/quality_dashboard.py` | Modified | +25 |
| `intuitiveness/quality/__init__.py` | Modified | +15 |
| `intuitiveness/ui/__init__.py` | Modified | +10 |
| `tests/quality/test_instant_export.py` | Created | ~500 |
| `specs/012-tabpfn-instant-export/spec.md` | Updated | ~210 |
| `specs/012-tabpfn-instant-export/plan.md` | Created | ~180 |
| `specs/012-tabpfn-instant-export/tasks.md` | Created | ~220 |

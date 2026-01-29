# Feature Specification: TabPFN Instant Export

**Feature Branch**: `012-tabpfn-instant-export`
**Created**: 2026-01-28
**Status**: Implemented
**Input**: Simplify TabPFN integration for non-technical domain experts

---

## What is TabPFN?

**TabPFN** (Tabular Prior-data Fitted Network) is a **foundation model for tabular data** published in [Nature (2024)](https://www.nature.com/articles/s41586-024-07544-w) by Hollmann et al.

### How TabPFN Works

| Traditional ML | TabPFN (In-Context Learning) |
|---------------|------------------------------|
| Trains model parameters on your data | Already pre-trained - uses your data as "context" |
| Each dataset needs fresh training | Single forward pass through pre-trained model |
| Minutes to hours per dataset | **Seconds** per dataset |
| Requires hyperparameter tuning | No tuning needed |

### Key Innovations

1. **Pre-trained on 100 million synthetic datasets** using structural causal models (SCMs)
   - These SCMs simulate real-world causal relationships
   - The model learned general patterns that transfer to real data

2. **In-Context Learning (ICL)**: Your entire dataset is passed as "context" to a transformer
   - Similar to how GPT processes text, TabPFN processes tabular data
   - The model predicts based on patterns it learned during pre-training

3. **Zero-shot capability**: No training on your specific data
   - Your data stays private - only used for inference
   - Faster iteration: change data, get instant new predictions

4. **Ensemble of 8 estimators** averaged for robustness
   - Reduces variance and improves reliability

5. **5,140x faster** than AutoML baselines while matching accuracy on datasets up to 10K rows

### TabPFN Limits

- Optimized for **≤10,000 rows**
- Optimized for **≤500 features**
- Classification: **≤10 classes**

---

## Problem Statement

The existing quality assessment service uses TabPFN for comprehensive ML analysis, but:

| Current Service Problem | Impact |
|------------------------|--------|
| 50-100+ TabPFN API calls per assessment | Slow (15-30+ seconds), expensive |
| Complex ablation study for feature importance | Most users don't need this |
| SHAP computation (often times out) | Unreliable, confusing output |
| 6 quality metrics with ML terminology | Overwhelming for non-technical users |
| Detailed diagnostics | Information overload |

**Target Users**: Domain experts with NO familiarity with ML or data structures (Constitution Principle V)

---

## User Scenarios & Testing

### User Story 1 - Quick Data Export (Priority: P1)

A domain expert uploads a CSV file, clicks one button, and gets a clean dataset ready for analysis - all in under 30 seconds.

**Why this priority**: This is the core value proposition. Everything else is secondary.

**Independent Test**: Upload any CSV → Click "Check & Export" → Receive clean CSV download within 30 seconds.

**Acceptance Scenarios**:

1. **Given** a CSV file with 1,000 rows and some missing values, **When** user clicks "Check & Export", **Then** user receives a cleaned CSV within 30 seconds
2. **Given** a CSV with text columns, **When** export completes, **Then** text columns are converted to numbers automatically
3. **Given** any valid target column, **When** user exports, **Then** the result includes plain-language summary of changes made

---

### User Story 2 - Binary Readiness Indicator (Priority: P1)

User sees a clear "Ready" or "Needs Work" indicator - no complex metrics or ML terminology.

**Why this priority**: Non-technical users need immediate, actionable feedback without cognitive overload.

**Independent Test**: Any dataset shows exactly one of two states: green "READY" or red "NEEDS WORK".

**Acceptance Scenarios**:

1. **Given** clean data with sufficient rows, **When** check completes, **Then** green "READY" indicator is shown
2. **Given** data with critical issues, **When** check completes, **Then** red "NEEDS WORK" indicator is shown with plain-language guidance
3. **Given** any result, **When** user reads the summary, **Then** no ML jargon appears (no "cross-validation", "hyperparameter", "SHAP", etc.)

---

### User Story 3 - Auto-Cleaning with Transparency (Priority: P2)

System automatically fixes common data issues and tells the user what was changed in plain language.

**Why this priority**: Reduces friction for users who don't know how to clean data manually.

**Independent Test**: Upload messy data → See list of plain-language changes → Download cleaned version.

**Acceptance Scenarios**:

1. **Given** data with missing values, **When** export runs, **Then** cleaning log shows "Filled X empty cells in 'column_name' with typical value"
2. **Given** data with text columns, **When** export runs, **Then** cleaning log shows "Converted text in 'column_name' to numbers"
3. **Given** data with unusable columns, **When** export runs, **Then** cleaning log shows "Removed 'column_name' - only one value"

---

### Edge Cases

- **Empty target column**: Show "Please select which column you want to predict"
- **Single-value target**: Show "The column you selected has only one value - nothing to analyze"
- **Very small dataset (<10 rows)**: Show "Your data has very few rows. You may need more data for reliable analysis"
- **All columns removed**: Show "Your data needs attention - too many issues found"
- **TabPFN unavailable**: Fallback to heuristic-only assessment (still works, just no validation score)

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST assess data readiness within 10 seconds (without TabPFN validation) or 30 seconds (with validation)
- **FR-002**: System MUST use plain language only - no ML jargon in any user-facing text
- **FR-003**: System MUST auto-handle missing values using simple imputation (median for numbers, mode for text)
- **FR-004**: System MUST auto-encode categorical columns for export compatibility
- **FR-005**: System MUST provide binary readiness indicator: "Ready" or "Needs Work"
- **FR-006**: System MUST log all cleaning actions with plain-language descriptions
- **FR-007**: System MUST complete full workflow (upload → check → export) in under 30 seconds
- **FR-008**: System MUST use maximum 5 TabPFN API calls (vs current 50-100+)

### Non-Functional Requirements

- **NFR-001**: UI must be accessible to users with no technical background
- **NFR-002**: Progress must be visible (progress bar, not spinner)
- **NFR-003**: Exported CSV must be loadable in Excel, Google Sheets, and pandas without errors

### Key Entities

- **ExportResult**: Contains readiness status, cleaned DataFrame, cleaning actions, warnings, and metadata
- **CleaningAction**: Single cleaning operation with action_type, column, description, and rows_affected
- **InstantExporter**: Main class that orchestrates the check-and-export workflow

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Upload to export completes in **<30 seconds** (measured via test_processing_time_recorded)
- **SC-002**: TabPFN API consumption reduced by **90%** (≤5 calls vs 50-100+, verified via test_max_api_calls_respected)
- **SC-003**: All user-facing text passes jargon-free test (verified via TestNoMLJargon test suite)
- **SC-004**: Zero ML terminology in default UI (verified via test_plain_summaries_no_jargon, test_plain_warnings_no_jargon)
- **SC-005**: Exported CSV loads cleanly in pandas (verified via test_export_csv_works)

---

## Implementation Summary

### Files Created

| File | Purpose |
|------|---------|
| `intuitiveness/quality/instant_export.py` | InstantExporter class with check_and_export() method |
| `intuitiveness/ui/quality/instant_export.py` | Streamlit UI component for quick export |
| `tests/quality/test_instant_export.py` | 32 unit tests covering all requirements |

### Files Modified

| File | Change |
|------|--------|
| `intuitiveness/quality/models.py` | Added ExportResult, CleaningAction dataclasses |
| `intuitiveness/quality/__init__.py` | Exported new classes and functions |
| `intuitiveness/ui/quality_dashboard.py` | Added "⚡ Quick Export" tab |
| `intuitiveness/ui/__init__.py` | Exported UI components |

### Test Results

```text
32 passed in 9.09s
- TestPerformance: 4 passed
- TestAPIConsumption: 3 passed
- TestNoMLJargon: 5 passed
- TestBasicFunctionality: 5 passed
- TestEdgeCases: 4 passed
- TestCleaningActions: 3 passed
- TestProgressCallback: 2 passed
- TestExportResultModel: 4 passed
- TestCleaningActionModel: 2 passed
```

---

## Alignment with Constitution

| Principle | Compliance |
|-----------|------------|
| **Principle V**: Target users have NO familiarity with data structures | ✅ Plain language only, no ML jargon |
| **Design Workflow Step 5**: Validate final abstraction matches domain understanding | ✅ Binary ready/needs_work is domain-friendly |
| **Quality Gate**: User-facing interfaces use domain terminology | ✅ All summaries and warnings use everyday language |

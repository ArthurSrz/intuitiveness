# Troubleshooting Guide

This document records bugs encountered and their solutions for future reference.

---

## OOM Error #1: Level3Dataset NetworkX Graph (2025-12-09)

**Problem**: Out of memory when creating L3 dataset with large dataframes. The Level3Dataset class was storing all rows as NetworkX graph nodes, which consumed excessive memory for datasets with 50k+ rows.

**Solution**: Changed Level3Dataset to store data as a pandas DataFrame instead of a NetworkX graph. Graph representation is only used when needed for visualization.

**File**: `intuitiveness/levels.py`

---

## OOM Error #2: Semantic Join Cartesian Product (2025-12-09)

**Problem**: Out of memory during "Building joined table..." step in the L4→L3 semantic join wizard. The join used `how='outer'` on the `semantic_id` column.

**Root Cause**: With semantic matching, only a subset of rows get assigned a `semantic_id`. Most rows have `semantic_id=None`. An outer join on a nullable column creates a **cartesian product** of all rows with null values:
- ~49,000 rows with `semantic_id=None` in left dataframe
- ~19,000 rows with `semantic_id=None` in right dataframe
- Outer join: 49,000 × 19,000 = **~931 million rows** → OOM

**Solution**:
1. Filter both dataframes to only include rows with valid (non-null) `semantic_id` before joining
2. Change from `how='outer'` to `how='inner'` to prevent any accidental cartesian products

**File**: `intuitiveness/ui/ascent_forms.py` (lines 1334-1347)

**Code Change**:
```python
# BEFORE (causes OOM)
result_df = pd.merge(result_df, df2, on=semantic_id_col, how='outer', ...)

# AFTER (fixed)
result_df_matched = result_df[result_df[semantic_id_col].notna()]
df2_matched = df2[df2[semantic_id_col].notna()]
result_df = pd.merge(result_df_matched, df2_matched, on=semantic_id_col, how='inner', ...)
```

**Lesson**: Always be careful with outer joins on nullable columns. Filter out nulls first or use inner join.

---

## HuggingFace API Call Format (2025-12-09)

**Problem**: Semantic matching returned "No strong semantic matches found" even though the API was being called successfully.

**Root Cause**: The `InferenceClient.sentence_similarity()` method requires positional arguments, not a dictionary.

**Solution**: Changed from dictionary format to positional arguments.

**File**: `intuitiveness/models.py`

**Code Change**:
```python
# BEFORE (wrong format)
result = client.sentence_similarity(
    {"source_sentence": source, "sentences": targets},
    model=MODEL
)

# AFTER (correct format)
result = client.sentence_similarity(
    source,      # positional arg 1
    targets,     # positional arg 2
    model=MODEL  # keyword arg
)
```

---

## Semantic Results Index Mismatch (2025-12-09)

**Problem**: Joined table was empty despite finding 500 semantic matches. Error: "Could not create joined table. The connections may not have produced any matches."

**Root Cause**: Index mismatch between `pair_analyses` and `connections` arrays.
- In Step 2, semantic results are stored with key `f"{prefix}_semantic_{pair_idx}"` where `pair_idx` comes from `enumerate(pair_analyses)`
- If any pairs are skipped, the `connections` array has fewer items and different indices
- In Step 3, the code was using `range(len(connections))` to look up semantic results, but this produced wrong keys

Example:
- `pair_analyses` = [pair0, pair1, pair2], user picks "embeddings" for pair1 only
- Semantic result stored at key `"prefix_semantic_1"` (pair1's index)
- `connections` = [{pair1 data}] (length 1)
- Code looked for `"prefix_semantic_0"` but needed `"prefix_semantic_1"`

**Solution**: Store `pair_idx` in connection dict and use it for semantic lookup.

**Files**: `intuitiveness/ui/ascent_forms.py`

**Code Changes**:
```python
# 1. Store original pair index in connection (line ~1112)
connections.append({
    ...
    'pair_idx': idx  # Store original pair index
})

# 2. Use pair_idx when gathering semantic results (line ~1459)
for conn in connections:
    pair_idx = conn.get('pair_idx', 0)
    semantic_key = f"{step2_key_prefix}_semantic_{pair_idx}"

# 3. Use pair_idx in join function (line ~1311)
pair_idx = conn.get('pair_idx', idx)
semantic_key = f"{key_prefix}_semantic_{pair_idx}"
```

**Lesson**: When filtering arrays creates index mismatches, store original indices to maintain correct lookups.

---

## DataFrame Has No Attribute 'nodes' (2025-12-09)

**Problem**: After confirming L3 dataset, Step 3 (Define Categories) crashes with error:
```
AttributeError: 'DataFrame' object has no attribute 'nodes'
```

**Root Cause**: Cascading effect from OOM Fix #1. When `Level3Dataset` was changed to store data as a DataFrame instead of a NetworkX graph, the `extract_entity_tabs()` and `extract_relationship_tabs()` functions in `entity_tabs.py` still expected a NetworkX graph.

The traceback:
- `streamlit_app.py:721` calls `extract_entity_tabs(graph)` where `graph` is actually a DataFrame
- `entity_tabs.py:98` calls `graph.nodes(data=True)` which fails on DataFrame

**Solution**: Updated `extract_entity_tabs()` and `extract_relationship_tabs()` to handle both NetworkX graphs and pandas DataFrames.

**File**: `intuitiveness/ui/entity_tabs.py`

**Code Changes**:
```python
# extract_entity_tabs() - handle DataFrame input
def extract_entity_tabs(graph_or_df) -> List[EntityTabData]:
    # Handle DataFrame input (from OOM Fix #1 - Level3Dataset stores DataFrame)
    if isinstance(graph_or_df, pd.DataFrame):
        df = graph_or_df
        if df.empty:
            return []

        # Create a single "Data" entity tab with all rows
        entities = []
        for idx, row in df.iterrows():
            entity_record = {"id": str(idx), "name": str(row[df.columns[0]]), "type": "Data"}
            for col in df.columns:
                if col not in entity_record:
                    entity_record[col] = row[col]
            entities.append(entity_record)

        return [EntityTabData(entity_type="Data", entity_count=len(entities), ...)]

    # Original NetworkX graph handling
    graph = graph_or_df
    ...

# extract_relationship_tabs() - handle DataFrame input
def extract_relationship_tabs(graph_or_df) -> List[RelationshipTabData]:
    # DataFrames are flat and have no relationships
    if isinstance(graph_or_df, pd.DataFrame):
        return []

    # Original NetworkX graph handling
    graph = graph_or_df
    ...
```

**Lesson**: When changing data storage format (graph → DataFrame), audit all downstream consumers that may assume the original format.

---

## DataFrame Truthiness Check Error (2025-12-09)

**Problem**: After fixing 'nodes' error, Step 3 (Define Categories) crashes with a different error:
```
ValueError: The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().
```

**Root Cause**: More cascading effects from OOM Fix #1. The code used `if graph` to check if the graph exists, but pandas DataFrames raise a ValueError when used in boolean context because they could be "truthy" in multiple ways.

The traceback:
- `entity_tabs.py:323` has `combined_all = create_combined_all_table(graph) if graph else None`
- When `graph` is a DataFrame, `if graph` raises ValueError

**Solution**:
1. Changed `if graph` to `if graph is not None` for explicit None check
2. Updated `create_combined_all_table()` to handle both NetworkX graphs and DataFrames

**File**: `intuitiveness/ui/entity_tabs.py`

**Code Changes**:
```python
# 1. Fix truthiness check (line 323)
# BEFORE (raises ValueError with DataFrame)
combined_all = create_combined_all_table(graph) if graph else None

# AFTER (explicit None check)
combined_all = create_combined_all_table(graph) if graph is not None else None

# 2. Add DataFrame handling to create_combined_all_table()
def create_combined_all_table(graph_or_df) -> Optional[CombinedTabData]:
    if graph_or_df is None:
        return None

    # Handle DataFrame input
    if isinstance(graph_or_df, pd.DataFrame):
        df = graph_or_df
        if df.empty:
            return None

        columns = list(df.columns)
        data = df.to_dict('records')

        return CombinedTabData(
            tab_type="all_data",
            label="All Data",
            count=len(data),
            columns=columns,
            data=data
        )

    # Original NetworkX graph handling
    graph = graph_or_df
    if graph.number_of_nodes() == 0:
        return None
    ...
```

**Lesson**: Never use `if df` with pandas DataFrames. Always use explicit checks like `df is not None` or `not df.empty`.

---

## Variable Name Mismatch: selected_entity_type (2025-12-09)

**Problem**: Clicking "Categorize Data" in Step 3 crashes with:
```
NameError: name 'selected_entity_type' is not defined
```

**Root Cause**: Refactoring artifact. The code defines `selected_table_name` at lines 770/774 but references `selected_entity_type` at lines 859/862. The variable was renamed but not all references were updated.

**Solution**: Replace `selected_entity_type` with `selected_table_name` at lines 859-863.

**File**: `intuitiveness/streamlit_app.py`

**Code Change**:
```python
# BEFORE (undefined variable)
categorize_by_domains(domains_list, use_semantic, threshold, column=selected_column, entity_type=selected_entity_type)
st.session_state.answers['entity_type'] = selected_entity_type

# AFTER (correct variable name)
categorize_by_domains(domains_list, use_semantic, threshold, column=selected_column, entity_type=selected_table_name)
st.session_state.answers['entity_type'] = selected_table_name
```

**Lesson**: When refactoring variable names, search for all occurrences across the entire function/file.

---

## DataFrame Has No Attribute 'nodes' #2: categorize_by_domains (2025-12-09)

**Problem**: After fixing previous DataFrame issues, clicking "Categorize Data" in Step 3 crashes with:
```
AttributeError: 'DataFrame' object has no attribute 'nodes'
```

**Root Cause**: Another cascading effect from OOM Fix #1. The `categorize_by_domains()` function in `streamlit_app.py` at line 1466 calls `graph.nodes(data=True)` but receives a DataFrame instead of a NetworkX graph.

**Solution**: Updated `categorize_by_domains()` to handle both NetworkX graphs and pandas DataFrames.

**File**: `intuitiveness/streamlit_app.py` (line 1466)

**Code Change**:
```python
# BEFORE (expected graph)
graph = st.session_state.datasets['l3'].get_data()
for node, attrs in graph.nodes(data=True):
    ...

# AFTER (handles both DataFrame and graph)
graph_or_df = st.session_state.datasets['l3'].get_data()

# Handle DataFrame input (from OOM Fix #1)
if isinstance(graph_or_df, pd.DataFrame):
    df = graph_or_df
    for idx, row in df.iterrows():
        value = row[column] if column in df.columns else row[df.columns[0]]
        items.append(str(value) if value is not None else "")
        item_data.append({"id": str(idx), "categorization_value": value, **row.to_dict()})
else:
    # Original NetworkX graph handling
    graph = graph_or_df
    for node, attrs in graph.nodes(data=True):
        ...
```

**Lesson**: When changing data storage format in a core class, audit ALL consumers of that class's data. Use grep/search to find all calls to `.nodes()`, `.edges()`, etc.

---

## Embedding Model Doesn't Support feature_extraction (2025-12-09)

**Problem**: Smart matching (AI) categorization fails with error:
```
Model 'intfloat/multilingual-e5-base' doesn't support task 'feature-extraction'. Supported tasks: 'sentence-similarity'
```

**Root Cause**: The HuggingFace Inference API has different task types. The `intfloat/multilingual-e5-base` model only supports `sentence-similarity` task (comparing two sentences), not `feature-extraction` task (getting raw embedding vectors).

**Solution**: Use a separate model for embeddings that supports `feature-extraction`:
- Keep `intfloat/multilingual-e5-base` for `sentence_similarity()` (pairwise comparison)
- Use `sentence-transformers/all-MiniLM-L6-v2` for `feature_extraction()` (raw embeddings)

**File**: `intuitiveness/models.py`

**Code Change**:
```python
# BEFORE (single model for both tasks)
SIMILARITY_MODEL = "intfloat/multilingual-e5-base"
# Used for both sentence_similarity AND feature_extraction

# AFTER (separate models per task)
SIMILARITY_MODEL = "intfloat/multilingual-e5-base"  # For sentence_similarity
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # For feature_extraction

# In get_embeddings(), use EMBEDDING_MODEL:
batch_embeddings = client.feature_extraction(batch, model=EMBEDDING_MODEL)
```

**Lesson**: HuggingFace Inference API tasks are model-specific. Always check what tasks a model supports before using it. Use specialized models for each task type.

---

## Categorization Uses Wrong Model (MiniLM instead of Multilingual E5) (2025-12-09)

**Problem**: Semantic categorization (L3→L2) used `sentence-transformers/all-MiniLM-L6-v2` instead of the multilingual model `intfloat/multilingual-e5-base`. This caused poor results for French text (e.g., categorizing communes into "ville"/"campagne").

**Root Cause**: The `SemanticMatcher._compute_semantic_scores()` method in `interactive.py` used `get_embeddings()` which calls `feature_extraction` with MiniLM. The multilingual-e5-base model only supports `sentence_similarity`, not `feature_extraction`.

**Solution**: Changed `_compute_semantic_scores()` to use `get_sentence_similarity()` directly instead of getting raw embeddings and computing cosine similarity manually.

**File**: `intuitiveness/interactive.py` (lines 558-585)

**Code Change**:
```python
# BEFORE (used MiniLM via get_embeddings)
from intuitiveness.models import get_embeddings
from numpy import dot
from numpy.linalg import norm

item_embedding = get_embeddings([item])
domain_embeddings = get_embeddings(domains)
# Manual cosine similarity computation...

# AFTER (uses multilingual-e5-base via get_sentence_similarity)
from intuitiveness.models import get_sentence_similarity

# Single API call, returns similarity scores directly
similarity_scores = get_sentence_similarity(item, domains)
scores = {domain: float(similarity_scores[i]) for i, domain in enumerate(domains)}
```

**Benefits**:
- Uses `intfloat/multilingual-e5-base` for better French/multilingual support
- Simpler code (no manual cosine similarity)
- Single API call per item instead of two

**Lesson**: When the API provides a direct comparison function (sentence_similarity), prefer that over getting raw embeddings and computing similarity manually.

---

## OOM Error #3: Many-to-Many Join Explosion (2025-12-09)

**Problem**: L4→L3 semantic join produced 731,142 rows from 50,164 + 20,053 input rows. Expected ~20k rows max.

**Root Cause**: Wrong understanding of the semantic join interface. The original specification described selecting "Dénomination principale" (64 unique values, generic type names like "COLLEGE") and matching it to "Nom de l'établissement" (4,122 unique school names). When semantic matching assigns:
- 32,214 rows with "COLLEGE" in left → matched to multiple "COLLEGE X" in right
- Result: 32,214 × N = explosive cartesian product

**Correct Understanding (Clarification)**:
The L4→L3 semantic join uses **multi-column row vectorization**:
1. User selects **multiple columns** from File 1 (e.g., "Appellation officielle", "Commune")
2. User selects **multiple columns** from File 2 (e.g., "Nom de l'établissement", "Commune")
3. Each **row** is converted to a vector: `vector = (col1_value, col2_value, ...)`
4. Semantic similarity compares row vectors, NOT single column values
5. This creates unique row identities that avoid many-to-many explosion

**Example**:
```
Row Vector File 1: ("COLLEGE JEAN MOULIN", "PARIS")
Row Vector File 2: ("COLLEGE JEAN MOULIN PARIS", "PARIS")
→ High similarity match (unique pair)

NOT:
Single Column File 1: "COLLEGE" (matches 32,214 rows)
Single Column File 2: "COLLEGE X" (matches thousands)
→ Explosion
```

**Files Updated**:
- `specs/006-playwright-mcp-e2e/spec.md` - Added Row Vector entity, updated FR-003, clarified US1/US2 L4→L3 steps
- `specs/006-playwright-mcp-e2e/tasks.md` - Changed "Join Configuration" to "Row Vector Configuration"

**Lesson**: When designing semantic joins, always use multiple columns that together create a unique row identity. Single generic columns cause many-to-many explosion.

---

## DataFrame Has No Attribute 'number_of_nodes': Results Step (2025-12-09)

**Problem**: Step 6 (Results) crashes with error:
```
AttributeError: 'DataFrame' object has no attribute 'number_of_nodes'
```

**Root Cause**: Another cascading effect from OOM Fix #1. The `render_results_step()` function in `streamlit_app.py` at line 1013 calls `G.number_of_nodes()` expecting a NetworkX graph, but receives a DataFrame due to the Level3Dataset storage change.

The traceback:
- `streamlit_app.py:1013` has `st.metric("Connected Items", G.number_of_nodes())`
- `G = st.session_state.datasets['l3'].get_data()` returns DataFrame not graph

**Solution**: Updated the code to handle both NetworkX graphs and DataFrames.

**File**: `intuitiveness/streamlit_app.py` (line 1010-1021)

**Code Change**:
```python
# BEFORE (expected graph)
G = st.session_state.datasets['l3'].get_data()
st.metric("Connected Items", G.number_of_nodes())

# AFTER (handles both DataFrame and graph)
G = st.session_state.datasets['l3'].get_data()
# Handle both NetworkX graphs and DataFrames
if hasattr(G, 'number_of_nodes'):
    st.metric("Connected Items", G.number_of_nodes())
elif hasattr(G, 'shape'):  # DataFrame
    st.metric("Connected Items", len(G))
else:
    st.metric("Connected Items", 0)
```

**Lesson**: After changing core data structures (OOM Fix #1: graph→DataFrame), grep for ALL method calls that assume the old structure (`.nodes()`, `.edges()`, `.number_of_nodes()`, etc.) across the entire codebase.

---

## TypeError: String Indices Must Be Integers - render_data_model_preview (2025-12-09)

**Problem**: Step 6 (Results) crashes in the Structure tab with error:
```
TypeError: string indices must be integers, not 'str'
```

**Root Cause**: The `render_data_model_preview()` function at line 1091 assumes `node.properties` is a list of dictionaries with a `'name'` key:
```python
props = ", ".join([p['name'] for p in node.properties])
```

But sometimes `node.properties` contains a list of strings (just property names) instead of dict objects. When iterating and accessing `p['name']`, Python interprets `p[...]` as string indexing.

**Solution**: Added type checking to handle both dict properties and string properties.

**File**: `intuitiveness/streamlit_app.py` (line 1088-1099)

**Code Change**:
```python
# BEFORE (assumed dict properties)
props = ", ".join([p['name'] for p in node.properties])

# AFTER (handles both dict and string properties)
if node.properties:
    props = ", ".join([
        p['name'] if isinstance(p, dict) else str(p)
        for p in node.properties
    ])
else:
    props = "(none)"
```

**Lesson**: When iterating over data structures that may have been created by different code paths, always check the actual type before assuming dict vs string access patterns.

---

## TypeError: Object of type int64 is not JSON serializable (2025-12-12)

**Problem**: When building the session graph from descent, the application crashes with:
```
TypeError: Object of type int64 is not JSON serializable
```

**Root Cause**: When pandas performs operations on DataFrames, it returns NumPy types (`int64`, `float64`, `bool_`) rather than Python's native `int`, `float`, and `bool`. Python's standard `json.dumps()` doesn't know how to serialize NumPy types.

The traceback:
- `streamlit_app.py:1336` calls `graph.add_level_state(..., data_artifact=some_value)`
- `session_graph.py:94` calls `serialize_value(data_artifact)`
- `serializers.py:106` calls `json.dumps(value)` which fails on NumPy int64

**Solution**: Added a custom `NumpyEncoder` JSON encoder class that converts NumPy types to their Python equivalents.

**File**: `intuitiveness/persistence/serializers.py`

**Code Change**:
```python
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def serialize_value(value: Any) -> str:
    # BEFORE
    json_str = json.dumps(value)

    # AFTER
    json_str = json.dumps(value, cls=NumpyEncoder)
```

Also updated `serialize_graph()` to use `NumpyEncoder` since graph attributes may also contain NumPy types.

**Lesson**: When working with pandas data, always use a custom JSON encoder that handles NumPy types. This is especially important for any serialization that happens after pandas operations (aggregations, groupby, etc.).

---

## Outdated Tabs Description Text (2025-12-12)

**Problem**: The L3 dataset view showed confusing text about "Individual tabs" when only one linked dataset was displayed.

**Root Cause**: UI text was outdated - referred to multiple tabs that no longer existed after simplification.

**Solution**: Simplified the help text to French and removed references to individual tabs.

**File**: `intuitiveness/streamlit_app.py` (line 809-817)

---

## L0 Display Shows np.int64 Notation (2025-12-12)

**Problem**: L0 ground truth displayed as `{'RELIGIEUX': np.int64(1146), 'HOMME_POLITIQUE': np.int64(4), ...}` - not user-friendly.

**Root Cause**: The `output_value` dict was displayed directly with `f-string`, showing Python's `repr()` of NumPy types.

**Solution**: Added `format_l0_value_for_display()` helper function that:
- Formats dicts as bullet lists
- Converts NumPy types to native Python types
- Formats numbers with thousand separators (using spaces per French convention)

**File**: `intuitiveness/streamlit_app.py` (line 172-210)

---

## Ascent Phase Progress Bar Missing (2025-12-12)

**Problem**: The ascent phase (Steps 9-12) had no visual progress bar, while descent (Steps 1-6) had one.

**Root Cause**: Progress bar only used `STEPS` constant which contained descent steps.

**Solution**:
1. Added `ASCENT_STEPS` constant with Steps 9-12 (in French)
2. Added `render_ascent_progress_bar()` function
3. Called it at the start of the ascent phase rendering

**File**: `intuitiveness/streamlit_app.py`

---

## Missing Back Buttons in Ascent Phase (2025-12-12)

**Problem**: Users couldn't navigate backwards during ascent (Steps 10, 11, 12 had no back buttons).

**Root Cause**: Navigation buttons were only implemented for descent, not ascent.

**Solution**: Added back buttons ("⬅️ Retour à l'étape X") at the start of each ascent step:
- Step 10: Back to Step 9
- Step 11: Back to Step 10
- Step 12: Back to Step 11

**File**: `intuitiveness/streamlit_app.py` (lines 2712, 2910, 3026)

---

## Step 11 Shows "No category column found" After Step 10 Categorization (2025-12-12)

**Problem**: After applying categorization in Step 10, Step 11 showed "No category column found in L2 data" and the embedding model didn't seem to trigger.

**Root Cause**: Step 10 creates a column named `'ascent_category'`, but Step 11 searched for category columns using a hardcoded list: `['score_quartile', 'performance_category', 'funding_size', 'value_category']` - which did NOT include `'ascent_category'`.

**Solution**: Added `'ascent_category'` as the FIRST item in the category column search list (in both display and action code).

**File**: `intuitiveness/streamlit_app.py` (lines 2920 and 2994)

**Code Change**:
```python
# BEFORE
for col in ['score_quartile', 'performance_category', 'funding_size', 'value_category']:

# AFTER
for col in ['ascent_category', 'score_quartile', 'performance_category', 'funding_size', 'value_category']:
```

**Lesson**: When creating new columns in one step, ensure all downstream steps know to look for those column names.

---

## NoneType Has No Attribute 'lower' - Data.gouv.fr API (2025-12-12)

**Problem**: Searching on data.gouv.fr crashes with:
```
AttributeError: 'NoneType' object has no attribute 'lower'
```

**Root Cause**: The data.gouv.fr API sometimes returns `null` (None) for the `format` field of resources instead of an empty string. The code used `r.get('format', '').lower()` which:
- Returns the default `''` when the key is MISSING
- Returns `None` when the key EXISTS but has a null value
- Calling `.lower()` on `None` raises AttributeError

**Solution**: Use `(r.get('format') or '').lower()` which handles both missing keys AND null values.

**File**: `intuitiveness/services/datagouv_client.py` (lines 201, 257)

**Code Change**:
```python
# BEFORE (fails when format is null)
r.get('format', '').lower() == 'csv'

# AFTER (handles null values)
(r.get('format') or '').lower() == 'csv'
```

**Lesson**: When dealing with external APIs, always use `(value or '')` pattern instead of `dict.get(key, '')` when the value might be explicitly null/None. The `or` operator handles both missing and null cases.

---

## ModuleNotFoundError: streamlit_pdf_viewer (2025-12-13)

**Problem**: Running the Streamlit app crashes with:
```
ModuleNotFoundError: No module named 'streamlit_pdf_viewer'
File "intuitiveness/ui/tutorial.py", line 14, in <module>
    from streamlit_pdf_viewer import pdf_viewer
```

**Root Cause**: Python environment mismatch. The package `streamlit-pdf-viewer` is installed in the `myenv311` virtual environment, but Streamlit was launched from pyenv's system installation (`/Users/arthursarazin/.pyenv/shims/streamlit`) which uses a different Python without the package.

**Diagnosis**:
```bash
# System path (wrong - doesn't have the package):
which streamlit  # → /Users/arthursarazin/.pyenv/shims/streamlit

# Virtual environment path (correct - has the package):
source myenv311/bin/activate && which streamlit
# → /Users/arthursarazin/Documents/data_redesign_method/myenv311/bin/streamlit
```

**Solution**: Always activate the virtual environment before running Streamlit:

```bash
# Option 1: Activate environment first
source myenv311/bin/activate
streamlit run intuitiveness/streamlit_app.py

# Option 2: Use full path to streamlit
./myenv311/bin/streamlit run intuitiveness/streamlit_app.py

# Option 3: Use python -m streamlit
./myenv311/bin/python -m streamlit run intuitiveness/streamlit_app.py
```

**Lesson**: When packages are installed in a virtual environment, always run commands from that environment. The shell's PATH might resolve to a system-wide installation that doesn't have your project dependencies.

---

## ValueError: DataFrame Truth Value Ambiguous (2025-12-14)

**Problem**: When clicking "Apply All Suggestions" in the Quality Dashboard, got error:
```
ValueError: The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().
```

**Root Cause**: In `quality_dashboard.py` line 610, code used Python `or` operator with DataFrames:
```python
df = st.session_state.get(SESSION_KEY_TRANSFORMED_DF) or st.session_state.get(SESSION_KEY_QUALITY_DF)
```

When a DataFrame exists, Python tries to evaluate its boolean value for the `or` operator, which is ambiguous (is an empty DataFrame False? Is a DataFrame with False values False?).

**Solution**: Use explicit None check instead of `or`:
```python
df = st.session_state.get(SESSION_KEY_TRANSFORMED_DF)
if df is None:
    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
```

**File**: `intuitiveness/ui/quality_dashboard.py` (line 610)

**Lesson**: Never use `or` operator for fallback values when dealing with DataFrames, numpy arrays, or other objects with ambiguous truth values. Always use explicit `is None` checks.

---

## UX Bug: Apply All Redirects Away from Report (2025-12-14)

**Problem**: When user clicks "Apply All Suggestions", the interface redirects back to the upload/assessment screen instead of staying on the report page to show before/after comparison.

**Root Cause**: After applying transformations, the code was calling:
```python
st.session_state.pop(SESSION_KEY_QUALITY_REPORT, None)  # Clears the report
st.rerun()  # Refreshes the page
```

Clearing the report caused the dashboard to go back to "no report" state, showing the upload interface instead of the results.

**Solution**: Keep the report in session state so user stays on the same page and can see:
1. Success message with accuracy improvement
2. Before/after comparison section
3. Export section

Simply removed the `pop(SESSION_KEY_QUALITY_REPORT)` call. User can explicitly click "Re-assess with Changes" or "New Assessment" when they want to start fresh.

**File**: `intuitiveness/ui/quality_dashboard.py` (lines 486-511, 321-342)

**Lesson**: When implementing one-click actions, consider the user journey. Users expect to see the result of their action on the same page, not be redirected elsewhere.

---

## CSV Parsing Error: Semicolon Delimiter Not Detected (2025-12-15)

**Problem**: Uploading a French government CSV file fails with:
```
Error tokenizing data. C error: Expected 1 fields in line 3616, saw 2
```

**Root Cause**: The CSV file uses semicolon (`;`) as delimiter instead of comma (`,`), which is common for French/European data files. The default `pd.read_csv()` assumes comma delimiter.

Example file header:
```
num_ligne;Rentrée scolaire;Code région académique;...
```

**Solution**: Added automatic delimiter detection using Python's `csv.Sniffer()` class:
1. Read first 8KB of file
2. Use `csv.Sniffer().sniff()` to detect delimiter from sample
3. Fall back to comparing semicolon vs comma count if sniffer fails
4. Pass detected delimiter to `pd.read_csv(sep=...)`

**File**: `intuitiveness/ui/quality_dashboard.py` (lines 257-275)

**Code Change**:
```python
# BEFORE (assumed comma delimiter)
df = pd.read_csv(uploaded_file)

# AFTER (auto-detect delimiter)
import csv
sample = uploaded_file.read(8192).decode('utf-8', errors='replace')
uploaded_file.seek(0)  # Reset file position

try:
    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
    sep = dialect.delimiter
except csv.Error:
    # Fallback: check if semicolon is more common than comma
    sep = ';' if sample.count(';') > sample.count(',') else ','

df = pd.read_csv(uploaded_file, sep=sep, encoding='utf-8', on_bad_lines='warn')
```

**Lesson**: European data files often use semicolon delimiter (because comma is used for decimal numbers in French/German locales). Always auto-detect the delimiter instead of assuming comma.

---

## TabPFN API Rate Limit: Switching to Local Inference (2025-12-15)

**Problem**: TabPFN cloud API returns rate limit errors after intensive use:
```
Error: TabPFN API rate limit exceeded. Please try again later.
```

**Root Cause**: The TabPFN cloud API (tabpfn-client) has usage limits. For development and testing, local inference is more reliable.

**Solution**: Updated `TabPFNWrapper` to prefer local inference by default via environment variable.

**Configuration**:
- `TABPFN_PREFER_LOCAL=1` (default): Use local TabPFN first, fall back to cloud API
- `TABPFN_PREFER_LOCAL=0`: Use cloud API first, fall back to local TabPFN

**Machine Requirements for Local TabPFN**:
- Apple Silicon (M1/M2/M3): Works with MPS (Metal Performance Shaders)
- 8GB+ RAM recommended
- PyTorch with MPS support

**Verification**:
```python
import torch
print(f"MPS available: {torch.backends.mps.is_available()}")
# Should print: MPS available: True

from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper
wrapper = TabPFNWrapper(task_type="classification")
print(f"Backend: {wrapper.backend}")
# Should print: Backend: local
```

**Files Modified**: `intuitiveness/quality/tabpfn_wrapper.py`

**Code Changes**:
```python
# Added environment variable support
import os
_PREFER_LOCAL_DEFAULT = os.environ.get("TABPFN_PREFER_LOCAL", "1") == "1"

# Updated TabPFNWrapper.__init__()
def __init__(self, task_type="classification", prefer_local=None, timeout=60.0):
    self.prefer_local = prefer_local if prefer_local is not None else _PREFER_LOCAL_DEFAULT
    # ...

# Updated get_tabpfn_model()
def get_tabpfn_model(task_type="classification", prefer_local=None):
    if prefer_local is None:
        prefer_local = _PREFER_LOCAL_DEFAULT
    return TabPFNWrapper(task_type=task_type, prefer_local=prefer_local)
```

**Lesson**: For development, prefer local inference to avoid API rate limits. Local TabPFN is fast enough for development workflows on modern hardware.

---

## TabPFN Import Error in Jupyter: Corrupted PyTorch (2025-12-15)

**Problem**: Using exported code snippet in Jupyter notebook fails with:
```
ImportError: dlopen(...torch/_C.cpython-311-darwin.so): Library not loaded: @rpath/libtorch_cpu.dylib
```

Full traceback shows hardcoded build paths like `/Users/runner/work/_temp/anaconda/envs/wheel_py311/lib/` that don't exist.

**Root Cause**: Environment mismatch. The Jupyter notebook uses the `anaconda3` environment which has a corrupted/incomplete PyTorch installation, while TabPFN works correctly in the project's `myenv311` virtual environment.

The error occurs because:
1. PyTorch wheels sometimes bake in build-time paths
2. A corrupted conda installation or pip/conda conflict caused missing `libtorch_cpu.dylib`
3. Jupyter kernel uses wrong Python environment

**Solution Options**:

**Option A: Use myenv311 as Jupyter kernel** (Recommended)
```bash
source /Users/arthursarazin/Documents/data_redesign_method/myenv311/bin/activate
pip install ipykernel
python -m ipykernel install --user --name=myenv311 --display-name="Python (myenv311)"
# Then restart Jupyter and select "Python (myenv311)" kernel
```

**Option B: Fix anaconda PyTorch**
```bash
conda activate base
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio
```

**Option C: Use exported code without TabPFN** (updated exporter)
The Export & Go code snippet now includes a try/except fallback:
- Tries TabPFN first
- Falls back to GradientBoosting if TabPFN unavailable
- Shows install instructions

**Files Modified**: `intuitiveness/quality/exporter.py`

**Code Change**:
```python
# Now generates code with fallback:
try:
    from tabpfn import TabPFNClassifier
    model = TabPFNClassifier()
    model.fit(X_train, y_train)
    print("✓ Using TabPFN (same model as quality assessment)")
except ImportError:
    print("⚠ TabPFN not available, using GradientBoosting fallback")
    print("  Install TabPFN: pip install tabpfn")
    from sklearn.ensemble import GradientBoostingClassifier
    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
```

**Lesson**: When generating code for external use (Export & Go), always include fallbacks for optional dependencies. Users may have different environments with missing packages.

---

## TabPFN Classifier: Too Many Classes (2025-12-15)

**Problem**: TabPFN Classifier fails with:
```
ValueError: Number of classes 28 exceeds the maximal number of classes supported by TabPFN.
```

**Root Cause**: TabPFN Classifier only supports up to 10 classes. The target column has more unique values.

**Common Scenario**: A continuous variable like "Taux de réussite G" (success rate %) was detected as classification because:
- `detect_task_type()` uses the rule: if unique_values < 5% of total rows → classification
- 28 unique values in 600 rows = 4.6% → classified as classification
- But percentages should typically use **regression**, not classification

**Solutions**:

**Option A: Use Regression (if target is continuous)**
```python
# If your target is a percentage/rate/continuous value, use regression:
from tabpfn import TabPFNRegressor
model = TabPFNRegressor()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

from sklearn.metrics import r2_score, mean_squared_error
print(f"R² Score: {r2_score(y_test, y_pred):.3f}")
print(f"RMSE: {mean_squared_error(y_test, y_pred, squared=False):.3f}")
```

**Option B: Use sklearn for many-class classification**
```python
# If you genuinely have 28+ categories:
from sklearn.ensemble import GradientBoostingClassifier
model = GradientBoostingClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(f"Accuracy: {model.score(X_test, y_test):.2%}")
```

**Option C: Bin into fewer categories first**
```python
# Convert continuous to 5 categories
df['target_binned'] = pd.qcut(df['Taux de réussite G'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
```

**Files Modified**: `intuitiveness/quality/exporter.py` - Complete rewrite with `smart_model_fit()` function.

**Final Robust Solution**: The exporter now generates a `smart_model_fit()` function that:
1. Auto-detects task type at runtime (not just at export time)
2. Checks if >20 unique numeric values → switches to regression
3. Checks TabPFN's 10-class limit before attempting fit
4. Catches ALL exceptions (ImportError, ValueError, RuntimeError, etc.)
5. Falls back to sklearn GradientBoosting which has no limits
6. Provides clear emoji-based feedback about what's happening

**Lesson**: When generating code for external use, don't trust pre-computed values. Re-analyze the data at runtime and handle ALL possible failure modes gracefully.

---

## Misleading "Classes" Warning for Regression Data (2025-12-15)

**Problem**: When loading continuous data (like success rates), the UI shows:
```
⚠️ Target has 29 classes (TabPFN optimal: ≤10). Consider grouping rare classes.
```

This warning is misleading because continuous data should use **regression**, not classification, and regression has no class limit.

**Root Cause**: `estimate_api_consumption()` in `tabpfn_wrapper.py` didn't know the task type. It counted unique values as "classes" and warned regardless of whether the data was classification or regression.

**Solution**:
1. Added `task_type` parameter to `estimate_api_consumption()`
2. Updated `quality_dashboard.py` to detect task type BEFORE calling the estimate function
3. Only show the "classes" warning when `task_type == "classification"`
4. Updated the UI to show task-type-aware info:
   - Regression: "29 unique values (continuous → regression)"
   - Classification: "5 classes (classification)"

**Files Modified**:
- `intuitiveness/quality/tabpfn_wrapper.py` - Added task_type parameter, made class warning conditional
- `intuitiveness/ui/quality_dashboard.py` - Detect task type early, pass to estimate function

**Lesson**: Warnings should be context-aware. A "classes" warning is meaningless and confusing for regression tasks.

---

## Grafo MCP: Attribute Creation Returns "Resource Not Found" (2026-01-09)

**Problem**: When building an ontology in Grafo MCP, attempting to add attributes to concepts fails with:
```
Error: Resource not found
```

Despite the concepts existing and being visible via `grafo_list_concepts()`.

**Root Cause**: Bug in the Grafo MCP server (`grafo-mcp-server/src/index.ts`). The MCP server uses wrong API endpoints:

```typescript
// BUGGY CODE in index.ts (line ~1000-1018)
// grafo_create_attribute handler uses:
const endpoint = parent_type === "concept"
  ? `/concepts/${parent_id}/attributes`  // WRONG - not document-scoped
  : `/relationships/${parent_id}/attributes`;
```

The Grafo REST API requires **document-scoped paths** for all concept operations:
- **Wrong**: `/concepts/{id}/attributes` → Returns 404
- **Correct**: `/documents/{doc_id}/concepts/{id}/attributes` → Works

Additionally, the API field name for attributes is `label`, not `name`.

**Solution**: Use direct curl API calls with the correct endpoint:

```bash
# Working command pattern:
DOC_ID="your-document-id"
CONCEPT_ID="node-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
TOKEN="your-grafo-api-token"

curl -s -X POST "https://app.gra.fo/api/v1/documents/${DOC_ID}/concepts/${CONCEPT_ID}/attributes" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"label": "attribute_name", "description": "attribute description"}'
```

**Key Points**:
1. **Endpoint**: Use document-scoped path `/documents/{doc_id}/concepts/{concept_id}/attributes`
2. **Field name**: Use `label` not `name` for the attribute name
3. **Token**: Get from `~/.claude/mcp.json` under `grafo.env.GRAFO_API_TOKEN`

**MCP Server Fix Needed** (for future reference):
In `/Users/arthursarazin/Documents/ontoKit/grafo-mcp-server/src/index.ts`, the `grafo_create_attribute` handler should be updated to:

```typescript
// FIXED CODE
const document_id = args.document_id;  // Need to add this param
const endpoint = parent_type === "concept"
  ? `/documents/${document_id}/concepts/${parent_id}/attributes`
  : `/documents/${document_id}/relationships/${parent_id}/attributes`;
```

**Constitution Compliance**: After using the direct API fix:
- **"No orphan entity nodes"**: ✅ All 24 concepts connected via 29 relationships
- **"No relationships without attribute"**: ✅ All relationships have label and description
- **"All entities should have at least one property"**: ✅ All 24 concepts have 1-4 attributes each

**File Affected**: Grafo MCP Server at `/Users/arthursarazin/Documents/ontoKit/grafo-mcp-server/src/index.ts`

**Lesson**: When MCP tools fail, investigate the underlying API directly with curl to identify endpoint mismatches.

---

## TabPFN Permission Denied on Streamlit Cloud (2026-01-29)

**Problem**: TabPFN validation fails on Streamlit Cloud with:
```
ERROR:intuitiveness.quality.instant_export:TabPFN validation failed: [Errno 13] Permission denied: '/home/adminuser/venv/lib/python3.13/site-packages/tabpfn_client/.tabpfn'
```

**Root Cause**: Python's import system and module-level constant initialization order:

1. `tabpfn_client/constants.py` defines: `CACHE_DIR = Path(__file__).parent.resolve() / ".tabpfn"`
2. Other modules import and compute derived constants at **import time**:
   ```python
   # service_wrapper.py line 30
   from tabpfn_client.constants import CACHE_DIR
   CACHED_TOKEN_FILE = CACHE_DIR / "config"  # Computed at import!
   ```
3. If we patch `constants.CACHE_DIR` **after** these imports, the derived constant `CACHED_TOKEN_FILE` still points to the old (read-only) path
4. Streamlit Cloud's filesystem is read-only in the package directory, causing permission errors

**Key Insight**: Module-level constants in Python are computed **once** at import time. If module B imports `CACHE_DIR` from module A and computes `CONSTANT = CACHE_DIR / "file"`, patching A's CACHE_DIR later won't update B's CONSTANT.

**Solution**: Patch `constants.CACHE_DIR` **BEFORE** importing any other tabpfn_client modules:

```python
# CRITICAL FIX: Patch constants FIRST
import tempfile
from pathlib import Path
import tabpfn_client.constants

cache_dir = Path(tempfile.gettempdir()) / "tabpfn_cache"
cache_dir.mkdir(parents=True, exist_ok=True)
tabpfn_client.constants.CACHE_DIR = cache_dir

# NOW import everything else (they'll use the patched path)
from tabpfn_client import TabPFNClassifier, TabPFNRegressor

# Patch any remaining references in already-imported modules
_patch_all_tabpfn_cache_dirs()  # Patches CACHED_TOKEN_FILE, etc.
```

**Implementation Details**:
The `_patch_all_tabpfn_cache_dirs()` function must also patch derived constants:

```python
def _patch_all_tabpfn_cache_dirs():
    # ... patch CACHE_DIR in all modules ...

    # CRITICAL: Also patch module-level constants computed from CACHE_DIR
    import tabpfn_client.service_wrapper
    if hasattr(tabpfn_client.service_wrapper, 'CACHED_TOKEN_FILE'):
        tabpfn_client.service_wrapper.CACHED_TOKEN_FILE = cache_dir / "config"
```

**Files Modified**:
- `intuitiveness/quality/tabpfn_wrapper.py`: Import order fix (lines 133-158)
- `intuitiveness/quality/tabpfn_wrapper.py`: Enhanced patching function (lines 32-91)

**Verification on Streamlit Cloud**:
```
INFO:intuitiveness.quality.tabpfn_wrapper:TabPFN cache redirected to /tmp/tabpfn_cache
INFO:intuitiveness.quality.tabpfn_wrapper:Patched CACHED_TOKEN_FILE to /tmp/tabpfn_cache/config
INFO:intuitiveness.quality.tabpfn_wrapper:Patched TabPFN CACHE_DIR in modules [constants, client, service_wrapper, config] to /tmp/tabpfn_cache
INFO:intuitiveness.quality.tabpfn_wrapper:TabPFN authenticated via ServiceClient.authorize() (no file cache)
```
✅ No more permission errors!

**Lesson**: When monkey-patching third-party libraries, understand the import chain and initialization order. Patch the **source of truth** (constants.py) BEFORE any downstream modules import from it. Also patch any derived constants that were already computed.

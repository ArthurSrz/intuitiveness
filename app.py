"""
Data Redesign Method - Streamlit App Entry Point

Run with:
    streamlit run app.py

This is the main entry point for the interactive data redesign application.
"""

import streamlit as st
import pandas as pd
import networkx as nx
import json
import sys
import os
import re
import requests

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# INTUITIVENESS PACKAGE IMPORTS
# ============================================================================

from intuitiveness import (
    ComplexityLevel,
    Level4Dataset,
    Level3Dataset,
    Level2Dataset,
    Level1Dataset,
    Level0Dataset,
    Redesigner,
    NavigationSession,
    NavigationState,
    NavigationError
)

# ============================================================================
# AGENT & NEO4J INTEGRATION
# ============================================================================

try:
    from intuitiveness.neo4j_client import Neo4jClient, Neo4jResult
    from intuitiveness.agent import SmolLM2Agent, AgentResult, AgentStep, simple_chat
    NEO4J_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Neo4j Agent not available: {e}")
    NEO4J_AGENT_AVAILABLE = False

# ============================================================================
# LLM INTEGRATION (Ollama + OpenAI)
# ============================================================================

# Ollama settings
# Options: qwen2.5-coder:7b (8GB RAM), qwen2.5-coder:14b (16GB RAM), deepseek-coder-v2:16b (32GB RAM)
OLLAMA_MODEL = "qwen2.5-coder:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# OpenAI settings
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]


def call_openai(prompt: str, model: str, api_key: str) -> str:
    """Call OpenAI API with the specified model."""
    import sys
    print(f"\n{'='*80}", flush=True)
    print(f"[OPENAI] Calling model: {model}", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"[OPENAI] === PROMPT START ===", flush=True)
    print(prompt, flush=True)
    print(f"[OPENAI] === PROMPT END === ({len(prompt)} chars)", flush=True)
    print(f"{'='*80}", flush=True)
    sys.stdout.flush()

    try:
        print(f"[OPENAI] Sending request to OpenAI API...", flush=True)
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        print(f"[OPENAI] === RESPONSE START ===", flush=True)
        print(result, flush=True)
        print(f"[OPENAI] === RESPONSE END === ({len(result)} chars)", flush=True)
        print(f"{'='*80}", flush=True)
        return result
    except requests.exceptions.HTTPError as e:
        print(f"[OPENAI] ERROR: {e}")
        if e.response.status_code == 401:
            return "ERROR: Invalid OpenAI API key"
        return f"ERROR: {str(e)}"
    except Exception as e:
        print(f"[OPENAI] ERROR: {str(e)}")
        return f"ERROR: {str(e)}"


def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """Call Ollama API with the specified model."""
    import sys
    print(f"\n{'='*80}", flush=True)
    print(f"[OLLAMA] Calling model: {model}", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"[OLLAMA] === PROMPT START ===", flush=True)
    print(prompt, flush=True)
    print(f"[OLLAMA] === PROMPT END === ({len(prompt)} chars)", flush=True)
    print(f"{'='*80}", flush=True)
    sys.stdout.flush()
    try:
        print(f"[OLLAMA] Sending request to {OLLAMA_URL}...", flush=True)
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2000
                }
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json().get("response", "")
        print(f"[OLLAMA] === RESPONSE START ===", flush=True)
        print(result, flush=True)
        print(f"[OLLAMA] === RESPONSE END === ({len(result)} chars)", flush=True)
        print(f"{'='*80}", flush=True)
        return result
    except requests.exceptions.ConnectionError:
        print(f"[OLLAMA] ERROR: Cannot connect to Ollama!")
        return "ERROR: Cannot connect to Ollama. Make sure it's running (ollama serve)"
    except Exception as e:
        print(f"[OLLAMA] ERROR: {str(e)}")
        return f"ERROR: {str(e)}"


def call_llm(prompt: str) -> str:
    """Call the configured LLM (Ollama or OpenAI based on session state)."""
    provider = st.session_state.get('llm_provider', 'ollama')

    if provider == 'openai':
        api_key = st.session_state.get('openai_api_key', '')
        model = st.session_state.get('openai_model', 'gpt-4o-mini')
        if not api_key:
            return "ERROR: OpenAI API key not configured. Set it in the sidebar."
        return call_openai(prompt, model, api_key)
    else:
        model = st.session_state.get('ollama_model', OLLAMA_MODEL)
        return call_ollama(prompt, model)


def analyze_data_for_entities(dataframes: dict, custom_instructions: str = None) -> str:
    """Use LLM to analyze data and suggest entities for the knowledge graph."""
    print(f"\n{'#'*80}")
    print(f"# STEP 2.1: ENTITY ANALYSIS - Suggesting entities from data")
    print(f"{'#'*80}")
    print(f"[ENTITY ANALYSIS] Analyzing {len(dataframes)} dataframes")
    if custom_instructions:
        print(f"[ENTITY ANALYSIS] Custom instructions: {custom_instructions[:100]}...")

    # Build a summary of the data
    data_summary = []
    for filename, df in dataframes.items():
        print(f"[ENTITY ANALYSIS] Processing: {filename} ({len(df)} rows, {len(df.columns)} cols)")
        cols = list(df.columns)[:10]  # Limit columns
        sample_values = {}
        for col in cols[:5]:
            unique_vals = df[col].dropna().unique()[:3]
            sample_values[col] = [str(v)[:50] for v in unique_vals]

        data_summary.append(f"""
File: {filename}
Columns: {cols}
Sample values: {sample_values}
Rows: {len(df)}
""")

    # Build the context section with user instructions
    context_section = ""
    if custom_instructions and custom_instructions.strip():
        context_section = f"""
USER CONTEXT AND REQUIREMENTS:
{custom_instructions.strip()}

MANDATORY : follow the requirements when designing the data model.

"""

    prompt = f"""You are a Neo4j data modeling expert. Analyze this CSV data and suggest a graph data model that integrates all DATA models below.
{context_section}

DATA:
{chr(10).join(data_summary)}

Based on the columns and sample values, identify:
1. ENTITIES: What are the main node types? (use PascalCase)
2. PROPERTIES: For each entity, which columns should be properties?
3. RELATIONSHIPS: How do entities connect? (use SCREAMING_SNAKE_CASE)

Return your analysis in this format:
ENTITIES: Entity1, Entity2, Entity3
PROPERTIES:
- Entity1: prop1, prop2
- Entity2: prop1, prop2
RELATIONSHIPS:
- Entity1 -[RELATIONSHIP_TYPE]-> Entity2

Analysis:"""

    return call_llm(prompt)


def generate_cypher_from_model(data_model: str, dataframes: dict) -> str:
    """Generate Cypher queries directly from data model and dataframes."""
    print(f"\n{'#'*80}")
    print(f"# CYPHER GENERATION - Creating Neo4j import queries")
    print(f"{'#'*80}")

    # Build CSV structure info
    csv_info = []
    for filename, df in dataframes.items():
        cols = list(df.columns)
        sample_rows = df.head(5).to_dict('records')
        csv_info.append(f"""
File: {filename}
Columns: {cols}
Sample data (first 5 rows): {sample_rows}
Total rows: {len(df)}
""")

    prompt = f"""You are a Neo4j Cypher expert. Generate Cypher queries to import data into Neo4j based on this data model.

DATA MODEL:
{data_model}

CSV DATA:
{chr(10).join(csv_info)}

Generate Cypher queries that:
1. Create constraints for each entity's key property (use IF NOT EXISTS)
2. Create nodes using MERGE with the sample data pattern shown
3. Create relationships between nodes based on the model

IMPORTANT:
- Do NOT use LOAD CSV (files are not accessible to Neo4j)
- Generate MERGE statements directly using the column names as property keys
- Use Neo4j 5.x syntax: CREATE CONSTRAINT IF NOT EXISTS FOR (n:Label) REQUIRE n.property IS UNIQUE
- Do NOT wrap output in markdown code blocks
- Return ONLY raw Cypher queries separated by semicolons
- Use UNWIND for batch inserts when possible
- Add comments with // to explain each section

Example pattern for batch insert:
UNWIND $rows AS row
MERGE (n:Label {{id: row.id}})
SET n.prop1 = row.prop1, n.prop2 = row.prop2

Cypher:"""

    return call_llm(prompt)


def sanitize_property_name(name: str) -> str:
    """Sanitize column name to be a valid Neo4j property name."""
    # Replace spaces and special chars with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'col_' + sanitized
    return sanitized or 'unknown'


def parse_data_model(data_model: str) -> dict:
    """Parse the LLM's data model response to extract entities, properties, and relationships."""
    import re as regex

    result = {
        'entities': [],
        'properties': {},
        'relationships': []
    }

    lines = data_model.strip().split('\n')
    current_section = None

    # Multiple regex patterns to handle LLM variations
    relationship_patterns = [
        r'(\w+)\s*-\[(\w+)\]->\s*(\w+)',           # Entity1 -[TYPE]-> Entity2
        r'(\w+)\s*-+\[(\w+)\]-+>\s*(\w+)',         # Entity1 --[TYPE]--> Entity2
        r'(\w+)\s*\[(\w+)\]\s*-+>\s*(\w+)',        # Entity1 [TYPE] --> Entity2
        r'(\w+)\s*-\s*(\w+)\s*->\s*(\w+)',         # Entity1 - TYPE -> Entity2
        r'(\w+)\s*\((\w+)\)\s*-*>\s*(\w+)',        # Entity1 (TYPE) -> Entity2
    ]

    # Section detection patterns (more flexible - handle #, ##, ### markdown headers)
    entity_section_patterns = ['ENTITIES:', 'ENTITÉS:', 'NODES:', 'NODE:', '# ENTITIES', '## ENTITIES', '### ENTITIES', '## ENTITÉS', '### ENTITÉS', '**ENTITIES', '**ENTITÉS']
    property_section_patterns = ['PROPERTIES:', 'PROPRIÉTÉS:', 'ATTRIBUTS:', '# PROPERTIES', '## PROPERTIES', '### PROPERTIES', '**PROPERTIES']
    relationship_section_patterns = ['RELATIONSHIPS:', 'RELATIONSHIP:', 'RELATIONS:', '# RELATIONSHIPS', '## RELATIONSHIPS', '### RELATIONSHIPS', '**RELATIONSHIPS']

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line_upper = line.upper().replace('**', '').strip()
        # Also create a version with leading # stripped for more flexible matching
        line_normalized = line_upper.lstrip('#').strip()

        # Detect sections with multiple patterns (check both original and normalized)
        is_entity_section = any(line_upper.startswith(p.upper()) or line_normalized.startswith(p.upper().lstrip('#').strip()) for p in entity_section_patterns)
        is_property_section = any(line_upper.startswith(p.upper()) or line_normalized.startswith(p.upper().lstrip('#').strip()) for p in property_section_patterns)
        is_relationship_section = any(line_upper.startswith(p.upper()) or line_normalized.startswith(p.upper().lstrip('#').strip()) for p in relationship_section_patterns)

        if is_entity_section:
            current_section = 'entities'
            print(f"[PARSE MODEL] Detected ENTITIES section: '{line}'")
            # Extract entities from same line if present
            if ':' in line:
                entities_str = line.split(':', 1)[1].strip()
                new_entities = [e.strip().strip('*').strip() for e in entities_str.split(',') if e.strip()]
                result['entities'].extend(new_entities)
        elif is_property_section:
            current_section = 'properties'
        elif is_relationship_section:
            current_section = 'relationships'
        elif current_section == 'entities':
            # Parse entity from bullet point: - Entity or * Entity or 1. Entity
            entity_line = regex.sub(r'^[-*•]\s*|\d+\.\s*', '', line).strip()
            # Remove markdown bold
            entity_line = entity_line.replace('**', '').strip()
            if entity_line and not entity_line.startswith('#'):
                # Extract just the entity name (before any colon or description)
                entity_name = entity_line.split(':')[0].split('(')[0].strip()
                if entity_name and regex.match(r'^[A-Za-z]\w*$', entity_name):
                    result['entities'].append(entity_name)
        elif current_section == 'properties':
            # Parse: - Entity1: prop1, prop2 (with or without leading -)
            prop_line = regex.sub(r'^[-*•]\s*|\d+\.\s*', '', line).strip()
            parts = prop_line.split(':', 1)
            if len(parts) == 2:
                entity = parts[0].strip().replace('**', '')
                props = [p.strip().replace('**', '') for p in parts[1].split(',') if p.strip()]
                if entity and props:
                    result['properties'][entity] = props
        elif current_section == 'relationships':
            # Parse relationship with multiple patterns (with or without leading -)
            rel_line = regex.sub(r'^[-*•]\s*|\d+\.\s*', '', line).strip()
            # Remove markdown bold markers **
            rel_line = rel_line.replace('**', '')

            # Try each pattern
            matched = False
            for pattern in relationship_patterns:
                match = regex.search(pattern, rel_line)
                if match:
                    rel = {
                        'from': match.group(1),
                        'type': match.group(2).upper().replace(' ', '_'),
                        'to': match.group(3)
                    }
                    result['relationships'].append(rel)
                    print(f"[PARSE MODEL] Found relationship: {rel['from']} -[{rel['type']}]-> {rel['to']}")
                    matched = True
                    break

            if not matched and rel_line and not rel_line.startswith('#'):
                print(f"[PARSE MODEL] WARNING: Could not parse relationship line: '{rel_line}'")

    print(f"[PARSE MODEL] Entities: {result['entities']}")
    print(f"[PARSE MODEL] Properties: {result['properties']}")
    print(f"[PARSE MODEL] Relationships: {result['relationships']}")

    return result


def map_csv_to_entity(filename: str, entities: list) -> str:
    """Try to map a CSV filename to an entity from the data model."""
    # Clean filename
    clean_name = filename.replace('.csv', '').replace(' ', '').replace('-', '').replace('_', '').lower()

    # Try to find matching entity
    for entity in entities:
        entity_clean = entity.replace(' ', '').replace('-', '').replace('_', '').lower()
        if entity_clean in clean_name or clean_name in entity_clean:
            return entity

    # If no match, create label from filename
    label = filename.replace('.csv', '').replace(' ', '_').replace('-', '_')
    label = ''.join(word.capitalize() for word in label.split('_'))
    return re.sub(r'[^a-zA-Z0-9]', '', label)


def compute_row_embedding(row: pd.Series, model) -> list:
    """Compute embedding for a row by concatenating its string properties."""
    # Create a text representation of the row
    text_parts = []
    for col, val in row.items():
        if pd.notna(val):
            text_parts.append(f"{col}: {str(val)[:100]}")

    text = " | ".join(text_parts[:10])  # Limit to first 10 columns
    if not text:
        text = "empty"

    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def find_semantic_relationships(dataframes: dict, csv_to_entity: dict, model_relationships: list = None, limit: int = 100, similarity_threshold: float = 0.5):
    """
    Use organizing principles (columns) to find semantic relationships between entities.

    L4 → L3 transition based on the Intuitiveness framework:
    1. Columns are organizing principles that give structure to data
    2. Find semantically similar columns across CSVs (column-to-column matching)
    3. Link rows that share similar values in those related columns (value overlap)
    4. Use LLM-inferred relationship types from model_relationships
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    print(f"\n[L4→L3] Loading intfloat/multilingual-e5-small model...")
    model = SentenceTransformer('intfloat/multilingual-e5-small')

    # Build lookup for relationship types from LLM model
    rel_type_lookup = {}
    if model_relationships:
        for rel in model_relationships:
            key = (rel['from'], rel['to'])
            rel_type_lookup[key] = rel['type']
            rel_type_lookup[(rel['to'], rel['from'])] = rel['type']
        print(f"[L4→L3] Loaded {len(rel_type_lookup)} relationship type mappings from LLM model")

    # Helper function to analyze column profile
    def get_column_profile(df, col):
        """Analyze column: type, cardinality, sample values."""
        series = df[col].dropna()
        if len(series) == 0:
            return {'dtype': 'empty', 'cardinality': 0, 'unique_ratio': 0, 'values': set()}

        # Detect data type
        if pd.api.types.is_numeric_dtype(series):
            dtype = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(series):
            dtype = 'datetime'
        else:
            # Check if string column contains mostly numbers
            str_series = series.astype(str)
            numeric_count = str_series.str.match(r'^-?\d+\.?\d*$').sum()
            if numeric_count / len(series) > 0.8:
                dtype = 'numeric_string'
            else:
                dtype = 'string'

        unique_vals = set(series.astype(str).str.lower().str.strip().head(500))
        cardinality = len(unique_vals)
        unique_ratio = cardinality / len(series) if len(series) > 0 else 0

        return {
            'dtype': dtype,
            'cardinality': cardinality,
            'unique_ratio': unique_ratio,
            'values': unique_vals,
            'count': len(series)
        }

    def compute_column_similarity(profile1, profile2, name_sim):
        """Compute overall column similarity based on name, type, and distribution."""
        # Type compatibility score
        type_compat = {
            ('numeric', 'numeric'): 1.0,
            ('numeric', 'numeric_string'): 0.9,
            ('numeric_string', 'numeric'): 0.9,
            ('numeric_string', 'numeric_string'): 1.0,
            ('string', 'string'): 1.0,
            ('datetime', 'datetime'): 1.0,
        }
        type_score = type_compat.get((profile1['dtype'], profile2['dtype']), 0.3)

        # Value overlap score (Jaccard similarity)
        if profile1['values'] and profile2['values']:
            intersection = len(profile1['values'] & profile2['values'])
            union = len(profile1['values'] | profile2['values'])
            value_overlap = intersection / union if union > 0 else 0
        else:
            value_overlap = 0

        # Cardinality similarity (similar uniqueness pattern)
        if profile1['unique_ratio'] > 0 and profile2['unique_ratio'] > 0:
            ratio_sim = min(profile1['unique_ratio'], profile2['unique_ratio']) / max(profile1['unique_ratio'], profile2['unique_ratio'])
        else:
            ratio_sim = 0

        # Combined score: weighted average
        # - High value overlap is the strongest signal (columns share actual values)
        # - Type compatibility is important
        # - Name similarity helps disambiguate
        # - Cardinality pattern is a weak signal
        if value_overlap > 0.1:
            # Strong value overlap - these columns are definitely related
            combined = 0.5 * value_overlap + 0.2 * type_score + 0.2 * name_sim + 0.1 * ratio_sim
        else:
            # No value overlap - rely more on type and name
            combined = 0.4 * type_score + 0.4 * name_sim + 0.2 * ratio_sim

        return combined, type_score, value_overlap, ratio_sim

    # Step 1: Analyze all columns (organizing principles)
    print(f"\n[L4→L3] Step 1: Analyzing organizing principles (columns)...")
    csv_columns = {}  # {filename: {col_name: {'embedding': ..., 'profile': ...}}}

    for filename, df in dataframes.items():
        col_data = {}
        print(f"\n[L4→L3] Analyzing {filename}:")
        for col in df.columns:
            embedding = model.encode(str(col), convert_to_numpy=True)
            profile = get_column_profile(df, col)
            col_data[col] = {'embedding': embedding, 'profile': profile}
            print(f"[L4→L3]   '{col}': {profile['dtype']}, {profile['cardinality']} unique values, {profile['unique_ratio']:.2f} unique ratio")
        csv_columns[filename] = col_data

    # Step 2: Find related column pairs (by name + type + distribution) - PARALLEL
    print(f"\n[L4→L3] Step 2: Finding related columns across CSVs (name + type + distribution)...")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import os

    COLUMN_MATCH_THRESHOLD = 0.8

    def compare_column_pair(args):
        """Compare a single column pair - for parallel execution."""
        csv1, col1, data1, csv2, col2, data2 = args
        name_sim = cosine_similarity([data1['embedding']], [data2['embedding']])[0][0]
        combined, type_score, value_overlap, ratio_sim = compute_column_similarity(
            data1['profile'], data2['profile'], name_sim
        )
        if combined > COLUMN_MATCH_THRESHOLD:
            return (csv1, col1, csv2, col2, float(combined), name_sim, type_score, value_overlap, ratio_sim)
        return None

    # Build list of all column pairs to compare
    comparison_tasks = []
    csv_list = list(dataframes.keys())
    for i, csv1 in enumerate(csv_list):
        cols1 = csv_columns[csv1]
        for csv2 in csv_list[i+1:]:
            cols2 = csv_columns[csv2]
            for col1, data1 in cols1.items():
                for col2, data2 in cols2.items():
                    comparison_tasks.append((csv1, col1, data1, csv2, col2, data2))

    print(f"[L4→L3] Comparing {len(comparison_tasks)} column pairs in parallel...")

    similar_column_pairs = []
    n_workers = min(os.cpu_count() or 4, 8)  # Use up to 8 workers

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(compare_column_pair, task): task for task in comparison_tasks}
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            if done_count % 50 == 0:
                print(f"[L4→L3]   ... {done_count}/{len(comparison_tasks)} comparisons ({100*done_count//len(comparison_tasks)}%)", end='\r')
            result = future.result()
            if result:
                csv1, col1, csv2, col2, combined, name_sim, type_score, value_overlap, ratio_sim = result
                similar_column_pairs.append((csv1, col1, csv2, col2, combined))
                print(f"\n[L4→L3]   ✓ '{col1}' ({csv1}) <-> '{col2}' ({csv2}): combined={combined:.3f}")
                print(f"[L4→L3]     name={name_sim:.2f}, type={type_score:.2f}, value_overlap={value_overlap:.2f}, cardinality={ratio_sim:.2f}")

    print(f"\n[L4→L3] Found {len(similar_column_pairs)} related column pairs")

    # Step 3: Find rows with matching/similar values in related columns - OPTIMIZED
    print(f"\n[L4→L3] Step 3: Finding value overlaps in related columns...")
    relationships = []  # [(from_entity, from_row_id, to_entity, to_row_id, rel_type, similarity)]

    total_pairs = len(similar_column_pairs)
    exact_matches = 0
    semantic_matches = 0

    for pair_idx, (csv1, col1, csv2, col2, col_sim) in enumerate(similar_column_pairs):
        df1 = dataframes[csv1].head(limit)
        df2 = dataframes[csv2].head(limit)
        entity1 = csv_to_entity[csv1]
        entity2 = csv_to_entity[csv2]

        # Get relationship type from LLM model
        rel_type = rel_type_lookup.get((entity1, entity2), "RELATED_TO")

        print(f"\n[L4→L3] Processing column pair {pair_idx+1}/{total_pairs}: '{col1}' <-> '{col2}'")
        print(f"[L4→L3]   {entity1} ({len(df1)} rows) vs {entity2} ({len(df2)} rows) | rel_type: {rel_type}")

        # Extract values with their row indices
        vals1 = [(idx, str(row.get(col1)).lower().strip()) for idx, row in df1.iterrows() if pd.notna(row.get(col1))]
        vals2 = [(idx, str(row.get(col2)).lower().strip()) for idx, row in df2.iterrows() if pd.notna(row.get(col2))]

        print(f"[L4→L3]   {len(vals1)} non-null values in col1, {len(vals2)} in col2")

        pair_exact = 0
        pair_semantic = 0

        # Step 3a: Find exact matches first (fast)
        print(f"[L4→L3]   Finding exact matches...")
        val2_lookup = {}  # value -> list of row indices
        for idx2, v2 in vals2:
            if v2 not in val2_lookup:
                val2_lookup[v2] = []
            val2_lookup[v2].append(idx2)

        exact_matched_pairs = set()
        for idx1, v1 in vals1:
            if v1 in val2_lookup:
                for idx2 in val2_lookup[v1]:
                    relationship_score = col_sim * 1.0
                    relationships.append((entity1, idx1, entity2, idx2, rel_type, relationship_score))
                    exact_matched_pairs.add((idx1, idx2))
                    pair_exact += 1
                    exact_matches += 1

        print(f"[L4→L3]   Found {pair_exact} exact matches")

        # Step 3b: Batch encode unique values for semantic matching
        print(f"[L4→L3]   Computing semantic similarities (batch encoding)...")

        # Get unique values to encode
        unique_vals1 = list(set(v for _, v in vals1))
        unique_vals2 = list(set(v for _, v in vals2))

        if unique_vals1 and unique_vals2:
            # Batch encode all unique values at once (much faster!)
            print(f"[L4→L3]   Encoding {len(unique_vals1)} + {len(unique_vals2)} unique values...")
            emb1_batch = model.encode([v[:100] for v in unique_vals1], convert_to_numpy=True, show_progress_bar=False)
            emb2_batch = model.encode([v[:100] for v in unique_vals2], convert_to_numpy=True, show_progress_bar=False)

            # Build embedding lookup
            emb1_lookup = {v: emb1_batch[i] for i, v in enumerate(unique_vals1)}
            emb2_lookup = {v: emb2_batch[i] for i, v in enumerate(unique_vals2)}

            # Compute all pairwise similarities at once using matrix multiplication
            print(f"[L4→L3]   Computing similarity matrix...")
            sim_matrix = cosine_similarity(emb1_batch, emb2_batch)

            # Find semantic matches above threshold
            val1_to_idx = {v: i for i, v in enumerate(unique_vals1)}
            val2_to_idx = {v: i for i, v in enumerate(unique_vals2)}

            for idx1, v1 in vals1:
                i1 = val1_to_idx[v1]
                for idx2, v2 in vals2:
                    # Skip if already exact match
                    if (idx1, idx2) in exact_matched_pairs:
                        continue
                    if v1 == v2:  # Also skip same values (already counted)
                        continue

                    i2 = val2_to_idx[v2]
                    val_sim = sim_matrix[i1, i2]

                    if val_sim >= similarity_threshold:
                        relationship_score = col_sim * val_sim
                        relationships.append((entity1, idx1, entity2, idx2, rel_type, float(relationship_score)))
                        pair_semantic += 1
                        semantic_matches += 1

        print(f"[L4→L3]   ✓ Column pair done: {pair_exact} exact + {pair_semantic} semantic = {pair_exact + pair_semantic} relationships")

    print(f"\n[L4→L3] Step 3 complete: {exact_matches} exact matches + {semantic_matches} semantic matches")

    # Deduplicate relationships (keep highest score for each pair)
    unique_rels = {}
    for rel in relationships:
        key = (rel[0], rel[1], rel[2], rel[3])
        if key not in unique_rels or rel[5] > unique_rels[key][5]:
            unique_rels[key] = rel

    relationships = list(unique_rels.values())

    print(f"[L4→L3] Found {len(relationships)} relationships via organizing principles")

    return relationships


def generate_direct_insert_queries(dataframes: dict, data_model: str,
                                   column_to_entity_mapping: dict,
                                   limit: int = 100) -> str:
    """Generate direct Cypher INSERT queries from dataframes using COLUMN-to-Entity mapping.

    Implements the L4 → L3 transition from the Data Redesign Method:
    - COLUMNS are mapped to entities (not entire CSVs)
    - Each row can produce MULTIPLE nodes (one per entity with columns in that row)
    - Nodes from the same row are automatically related
    - Relationship types come from the LLM data model

    Args:
        dataframes: Dict of {filename: DataFrame}
        data_model: LLM-generated data model string
        column_to_entity_mapping: Dict of {"csv::column": entity_name}
        limit: Max rows per CSV to process
    """
    print(f"\n{'#'*80}")
    print(f"# DIRECT INSERT - L4 → L3 Transition (COLUMN-based Graph Construction)")
    print(f"{'#'*80}")

    # Parse the data model to get entities, properties, and relationships
    model = parse_data_model(data_model)

    queries = []

    model_entities = model['entities']
    model_relationships = model['relationships']

    print(f"[L4→L3] Model entities: {model_entities}")
    print(f"[L4→L3] Model relationships: {model_relationships}")

    # CRITICAL: Validate that we have entities from the LLM model
    if not model_entities:
        raise ValueError("LLM data model has no entities! Cannot proceed with graph construction.")

    # ========================================================================
    # COLUMN-TO-ENTITY MAPPING: Group columns by entity, preserving source CSV
    # ========================================================================
    print(f"\n[L4→L3] Processing COLUMN-to-Entity mapping:")
    print(f"[L4→L3] Total mappings: {len(column_to_entity_mapping)}")

    # Structure: {entity: {csv: [columns]}}
    entity_csv_columns = {e: {} for e in model_entities}

    for col_key, entity in column_to_entity_mapping.items():
        if entity == "-- Ignore --":
            continue
        if "::" not in col_key:
            print(f"[L4→L3] WARNING: Invalid column key format: {col_key}")
            continue

        csv_name, col_name = col_key.split("::", 1)
        if entity not in entity_csv_columns:
            entity_csv_columns[entity] = {}
        if csv_name not in entity_csv_columns[entity]:
            entity_csv_columns[entity][csv_name] = []
        entity_csv_columns[entity][csv_name].append(col_name)

    # Print summary
    for entity, csv_cols in entity_csv_columns.items():
        if csv_cols:
            for csv_name, cols in csv_cols.items():
                print(f"[L4→L3] ✓ {entity} from {csv_name}: {cols}")

    # ========================================================================
    # CREATE NODES: For each entity, for each source CSV, create nodes
    # ========================================================================
    created_entities = []

    for entity in model_entities:
        csv_cols = entity_csv_columns.get(entity, {})
        if not csv_cols:
            print(f"[L4→L3] ⚠ Entity '{entity}' has no columns assigned - skipping")
            continue

        created_entities.append(entity)

        # Constraint on row_id
        queries.append(f"// Constraint for {entity}")
        queries.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{entity}) REQUIRE n.row_id IS UNIQUE")

        # For each CSV that has columns for this entity
        for csv_name, columns in csv_cols.items():
            if csv_name not in dataframes:
                print(f"[L4→L3] WARNING: CSV '{csv_name}' not found in dataframes")
                continue

            df = dataframes[csv_name]
            queries.append(f"\n// Insert {entity} nodes from {csv_name} (columns: {columns})")

            for idx, row in df.head(limit).iterrows():
                # row_id includes csv name to avoid collisions
                row_id = f"{csv_name.replace('.csv', '')}_{idx}"
                props = [f"row_id: '{row_id}'", f"source_csv: '{csv_name}'"]

                for col in columns:
                    if col not in df.columns:
                        continue
                    val = row[col]
                    if pd.isna(val):
                        continue

                    sanitized_col = sanitize_property_name(col)

                    if isinstance(val, str):
                        val = val.replace('\\', '\\\\').replace("'", "\\'")
                        props.append(f"{sanitized_col}: '{val}'")
                    elif isinstance(val, (int, float)):
                        props.append(f"{sanitized_col}: {val}")
                    else:
                        val_str = str(val).replace('\\', '\\\\').replace("'", "\\'")
                        props.append(f"{sanitized_col}: '{val_str}'")

                if len(props) > 2:  # Has more than just row_id and source_csv
                    props_str = ', '.join(props[:15])
                    queries.append(f"MERGE (n:{entity} {{{props_str}}})")

    # ========================================================================
    # CREATE RELATIONSHIPS: Use LLM model relationships + row_id matching
    # ========================================================================
    # Nodes from the same CSV row share row_id prefix, so they're naturally related.
    # We use the LLM relationship types to determine which entity pairs should be connected.

    print(f"[L4→L3] Created entities: {created_entities}")

    if len(created_entities) >= 2:
        queries.append(f"\n// Creating relationships based on LLM data model")

        # Build lookup for relationship types: (from_entity, to_entity) -> rel_type
        rel_type_lookup = {}
        for rel in model_relationships:
            key = (rel['from'], rel['to'])
            rel_type_lookup[key] = rel['type']
            # Also add reverse (some relationships might be bidirectional)
            reverse_key = (rel['to'], rel['from'])
            if reverse_key not in rel_type_lookup:
                rel_type_lookup[reverse_key] = rel['type']

        print(f"[L4→L3] Relationship types from model: {rel_type_lookup}")

        # For entities from the SAME CSV: connect via row_id
        # Check which entities share a source CSV
        entities_per_csv = {}
        for entity, csv_cols in entity_csv_columns.items():
            if entity not in created_entities:
                continue
            for csv_name in csv_cols.keys():
                if csv_name not in entities_per_csv:
                    entities_per_csv[csv_name] = []
                entities_per_csv[csv_name].append(entity)

        print(f"[L4→L3] Entities per CSV: {entities_per_csv}")

        # Create relationships between entities from the same CSV (same row = related)
        for csv_name, entities in entities_per_csv.items():
            if len(entities) < 2:
                continue

            queries.append(f"\n// Relationships between entities from {csv_name} (same row = related)")

            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Look up relationship type from LLM model
                    rel_type = rel_type_lookup.get((entity1, entity2)) or \
                               rel_type_lookup.get((entity2, entity1)) or \
                               "RELATED_TO"

                    queries.append(f"""
MATCH (a:{entity1}), (b:{entity2})
WHERE a.row_id = b.row_id
MERGE (a)-[r:{rel_type}]->(b)""")
                    print(f"[L4→L3] ✓ {entity1} -[{rel_type}]-> {entity2} (via row_id in {csv_name})")

        # For entities from DIFFERENT CSVs: use embedding similarity
        csv_names = list(entities_per_csv.keys())
        if len(csv_names) >= 2:
            print(f"\n[L4→L3] Finding cross-CSV relationships via embeddings...")

            # Build a mapping of entity -> dataframe for embedding computation
            entity_dataframes = {}
            for entity in created_entities:
                csv_cols = entity_csv_columns.get(entity, {})
                for csv_name, columns in csv_cols.items():
                    if csv_name in dataframes:
                        # Create a filtered dataframe with only this entity's columns
                        df = dataframes[csv_name][columns].copy()
                        df['_source_csv'] = csv_name
                        df['_row_idx'] = range(len(df))
                        entity_dataframes[entity] = df
                        break  # Use first CSV for now

            # TODO: Implement cross-CSV embedding similarity if needed
            # For now, we only connect entities from the same CSV via row_id

        print(f"[L4→L3] Relationship creation complete")
    else:
        print(f"[L4→L3] Only {len(created_entities)} entity type - no cross-entity relationships to create")

    return ';\n'.join(queries)


def execute_cypher_queries(cypher_queries: str):
    """Execute Cypher queries in Neo4j using direct connection."""
    print(f"\n{'#'*80}")
    print(f"# EXECUTING CYPHER QUERIES")
    print(f"{'#'*80}")

    # Clean markdown code blocks from LLM response
    import re
    cleaned = cypher_queries
    cleaned = re.sub(r'```cypher\s*', '', cleaned)
    cleaned = re.sub(r'```sql\s*', '', cleaned)
    cleaned = re.sub(r'```\s*', '', cleaned)

    # Split queries by semicolon and clean up
    def clean_query(q):
        """Remove leading comment lines but keep actual Cypher."""
        lines = q.strip().split('\n')
        # Remove pure comment lines from beginning
        while lines and lines[0].strip().startswith('//'):
            lines.pop(0)
        return '\n'.join(lines).strip()

    queries = [clean_query(q) for q in cleaned.split(';') if clean_query(q)]

    client = get_neo4j_client()
    if not client or not client.is_connected:
        st.error("❌ Not connected to Neo4j. Please connect first using the chat panel.")
        st.info("Click '🔌 Connecter Neo4j' in the chat section below.")
        return

    results = []
    success_count = 0
    error_count = 0

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, query in enumerate(queries):
        if query.strip():
            progress = (i + 1) / len(queries)
            progress_bar.progress(progress)
            status_text.text(f"Executing query {i+1}/{len(queries)}...")

            print(f"[CYPHER] Executing query {i+1}/{len(queries)}...")
            print(f"[CYPHER] {query[:100]}...")

            # Use write_cypher for write operations, run_cypher for reads
            if any(kw in query.upper() for kw in ['CREATE', 'MERGE', 'DELETE', 'SET', 'REMOVE']):
                result = client.write_cypher(query)
            else:
                result = client.run_cypher(query)

            if result.success:
                success_count += 1
                results.append({"query": query[:50] + "...", "status": "✅", "result": str(result.data)[:50]})
            else:
                error_count += 1
                print(f"[CYPHER] ERROR: {result.error}")
                results.append({"query": query[:50] + "...", "status": "❌", "error": str(result.error)[:50]})

    progress_bar.empty()
    status_text.empty()

    # Summary
    if error_count == 0:
        st.success(f"✅ All {success_count} queries executed successfully!")
    else:
        st.warning(f"⚠️ {success_count} succeeded, {error_count} failed")

    st.session_state['cypher_results'] = results
    if results:
        with st.expander("📊 Execution Results"):
            st.dataframe(results)

    # Visualize the graph from Neo4j
    if success_count > 0:
        visualize_neo4j_graph(client)


def visualize_neo4j_graph(client):
    """Query Neo4j and visualize the knowledge graph."""
    import matplotlib.pyplot as plt
    import random

    st.divider()
    st.subheader("🕸️ Knowledge Graph from Neo4j")

    # Query graph structure - get node counts by label
    node_query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    LIMIT 20
    """

    # Query relationship counts - aggregate by pattern
    rel_query = """
    MATCH (a)-[r]->(b)
    RETURN labels(a)[0] as from_label, type(r) as rel_type, labels(b)[0] as to_label, count(r) as count
    ORDER BY count DESC
    LIMIT 50
    """

    # Sample query using Neo4j internal IDs and node properties (name, id, or fallback)
    sample_query = """
    MATCH (a)-[r]->(b)
    RETURN labels(a)[0] as from_label,
           id(a) as from_id,
           coalesce(a.name, a.id, toString(id(a))) as from_name,
           type(r) as rel_type,
           labels(b)[0] as to_label,
           id(b) as to_id,
           coalesce(b.name, b.id, toString(id(b))) as to_name
    LIMIT 100
    """

    # Get stats
    node_result = client.run_cypher(node_query)
    rel_result = client.run_cypher(rel_query)
    sample_result = client.run_cypher(sample_query)

    if not node_result.success:
        st.error(f"Failed to query nodes: {node_result.error}")
        return

    # Display stats in expandable sections (stacked vertically)
    with st.expander("📦 **Nodes**", expanded=False):
        if node_result.data:
            for item in node_result.data[:8]:
                label = item['label'] if item['label'] else 'Unknown'
                st.write(f"**:{label}** - {item['count']} nodes")
        else:
            st.info("No nodes found")

    with st.expander("🔗 **Relationships**", expanded=False):
        if rel_result.success and rel_result.data:
            for item in rel_result.data[:10]:
                from_label = item['from_label'] if item['from_label'] else '?'
                to_label = item['to_label'] if item['to_label'] else '?'
                st.write(f"(:{from_label})-[:{item['rel_type']}]->(:{to_label}): **{item['count']}**")
        else:
            st.info("No relationships found")

    # Build NetworkX graph for visualization
    if sample_result.success and sample_result.data:
        G = nx.DiGraph()

        # Dynamic color palette - generate colors for discovered labels
        base_colors = [
            "#3498DB", "#2ECC71", "#E74C3C", "#9B59B6", "#F39C12",
            "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#27AE60",
            "#2980B9", "#8E44AD", "#F1C40F", "#D35400", "#C0392B"
        ]

        # Collect all unique labels
        unique_labels = set()
        for row in sample_result.data:
            if row.get('from_label'):
                unique_labels.add(row['from_label'])
            if row.get('to_label'):
                unique_labels.add(row['to_label'])

        # Create dynamic palette
        palette = {}
        for i, label in enumerate(sorted(unique_labels)):
            palette[label] = base_colors[i % len(base_colors)]

        node_colors = {}
        node_display_names = {}

        for row in sample_result.data:
            from_label = row.get('from_label', 'Unknown')
            to_label = row.get('to_label', 'Unknown')
            from_id = row.get('from_id', 0)
            to_id = row.get('to_id', 0)
            from_name = row.get('from_name', str(from_id))
            to_name = row.get('to_name', str(to_id))

            # Create unique node identifiers
            from_node = f"{from_label}_{from_id}"
            to_node = f"{to_label}_{to_id}"

            G.add_node(from_node, label=from_label, name=from_name)
            G.add_node(to_node, label=to_label, name=to_name)
            G.add_edge(from_node, to_node, relation=row['rel_type'])

            node_colors[from_node] = palette.get(from_label, "#95A5A6")
            node_colors[to_node] = palette.get(to_label, "#95A5A6")

            # Store display names (shortened)
            node_display_names[from_node] = (from_name[:12] + '..') if len(str(from_name)) > 12 else str(from_name)
            node_display_names[to_node] = (to_name[:12] + '..') if len(str(to_name)) > 12 else str(to_name)

        if G.number_of_nodes() > 0:
            fig, ax = plt.subplots(figsize=(16, 12))

            # Layout with more spacing (k parameter controls distance)
            pos = nx.spring_layout(G, k=3, iterations=100, seed=42)

            # Draw nodes
            colors = [node_colors.get(n, "#95A5A6") for n in G.nodes()]
            nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=400, alpha=0.9, ax=ax)

            # Draw edges with curved connections
            nx.draw_networkx_edges(G, pos, edge_color="#7F8C8D", arrows=True,
                                   arrowsize=12, alpha=0.5, ax=ax,
                                   connectionstyle="arc3,rad=0.1",
                                   width=0.8)

            # Labels - use display names
            nx.draw_networkx_labels(G, pos, node_display_names, font_size=6, ax=ax)

            # Edge labels (relationship types) - only show unique ones to reduce clutter
            edge_labels = {}
            seen_rel_types = set()
            for (u, v, data) in G.edges(data=True):
                rel_type = data.get('relation', '')
                # Only label first occurrence of each relationship type
                if rel_type not in seen_rel_types:
                    edge_labels[(u, v)] = rel_type
                    seen_rel_types.add(rel_type)

            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=5, font_color="#E74C3C", ax=ax)

            ax.set_title(f"Knowledge Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} relationships",
                         fontsize=12, fontweight='bold')
            ax.axis('off')
            plt.tight_layout()

            # Display graph full width and centered
            st.pyplot(fig, use_container_width=True)
            plt.close()

            # Legend - show actual labels found
            legend_items = [f"<b>{k}</b>=<span style='color:{v}'>{v}</span>"
                           for k, v in palette.items() if any(k in str(G.nodes[n].get('label', '')) for n in G.nodes())]
            if legend_items:
                st.markdown(
                    "<div style='text-align: center; font-size: 12px;'>" +
                    "Node colors: " + ", ".join(legend_items[:10]) +  # Limit legend items
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No relationships to visualize. Nodes were created but not connected.")
    else:
        st.info("Graph visualization: No connected data found. Check if relationships were created.")


def suggest_relationships(entities: list, dataframes: dict) -> str:
    """Use LLM to suggest relationships between entities."""

    # Get column names for context
    all_columns = set()
    for df in dataframes.values():
        all_columns.update(df.columns)

    prompt = f"""Given these entities for a Neo4j graph: {entities}
And these data columns: {list(all_columns)[:20]}

Suggest relationships between entities.
Return ONLY in format: EntityA-RELATIONSHIP_TYPE->EntityB
One per line.

Relationships:"""

    return call_llm(prompt)


def generate_data_model_with_ollama(entities: list, core_entity: str, dataframes: dict) -> dict:
    """
    Use Ollama to generate a complete Neo4j data model.
    Returns a dict in the format expected by mcp__neo4j-data-modeling tools.
    """
    print(f"\n{'#'*80}")
    print(f"# STEP 2.2: DATA MODEL GENERATION - Creating Neo4j schema")
    print(f"{'#'*80}")
    print(f"[DATA MODEL] Entities: {entities}")
    print(f"[DATA MODEL] Core entity: {core_entity}")

    # Get column names for context
    all_columns = set()
    sample_data = {}
    for filename, df in dataframes.items():
        print(f"[DATA MODEL] Extracting columns from: {filename}")
        all_columns.update(df.columns)
        for col in list(df.columns)[:5]:
            unique_vals = df[col].dropna().unique()[:3]
            sample_data[col] = [str(v)[:30] for v in unique_vals]

    prompt = f"""Create a Neo4j graph data model from this data.

ENTITIES: {entities}
CORE ENTITY: {core_entity}
DATA COLUMNS: {list(all_columns)[:15]}
SAMPLE VALUES: {sample_data}

Return ONLY a valid JSON object with this EXACT structure:
{{
  "nodes": [
    {{"label": "EntityName", "key_property": {{"name": "id", "type": "STRING"}}, "properties": [{{"name": "name", "type": "STRING"}}]}}
  ],
  "relationships": [
    {{"type": "RELATIONSHIP_TYPE", "start_node_label": "EntityA", "end_node_label": "EntityB"}}
  ]
}}

Rules:
- Labels must be PascalCase
- Relationship types must be SCREAMING_SNAKE_CASE
- Each node MUST have a key_property with name and type
- The core entity ({core_entity}) should connect to other entities
- Use meaningful relationship types based on the data

JSON:"""

    print(f"[DATA MODEL] Sending prompt to Ollama...")
    response = call_ollama(prompt)

    # Try to extract JSON from response
    try:
        # Find JSON in response
        import re
        print(f"[DATA MODEL] Parsing LLM response...")
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            parsed = json.loads(json_match.group())
            print(f"[DATA MODEL] SUCCESS: Parsed JSON with {len(parsed.get('nodes', []))} nodes, {len(parsed.get('relationships', []))} relationships")
            return parsed
    except Exception as e:
        print(f"[DATA MODEL] WARNING: Could not parse LLM response: {e}")
        st.warning(f"Could not parse LLM response: {e}")

    # Fallback: create basic model from entities
    print(f"[DATA MODEL] Using fallback basic model...")
    return create_basic_data_model(entities, core_entity)


def create_basic_data_model(entities: list, core_entity: str) -> dict:
    """Create a basic data model structure from entities."""
    print(f"[BASIC MODEL] Creating basic model from {len(entities)} entities")
    nodes = []
    relationships = []

    for entity in entities:
        node = {
            "label": entity,
            "key_property": {"name": f"{entity.lower()}Id", "type": "STRING"},
            "properties": [
                {"name": "name", "type": "STRING"},
                {"name": "createdAt", "type": "STRING"}
            ]
        }
        nodes.append(node)

        # Create relationship from non-core to core
        if entity != core_entity:
            rel = {
                "type": f"BELONGS_TO_{core_entity.upper()}",
                "start_node_label": entity,
                "end_node_label": core_entity
            }
            relationships.append(rel)

    return {"nodes": nodes, "relationships": relationships}

from intuitiveness import (
    Level4Dataset, Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset,
    DataModelGenerator, Neo4jDataModel, SemanticMatcher, QuestionType
)


# ============================================================================
# NEO4J AGENT HELPERS
# ============================================================================

def get_neo4j_client():
    """Get or create Neo4j client singleton."""
    if not NEO4J_AGENT_AVAILABLE:
        return None

    if 'neo4j_client' not in st.session_state:
        # Credentials resolved from st.secrets / env (MEMGRAPH_* or NEO4J_*),
        # never hardcoded — see get_graph_db_credentials() in neo4j_client.py.
        st.session_state.neo4j_client = Neo4jClient()
    return st.session_state.neo4j_client


def get_agent():
    """Get or create SmolLM2 agent singleton."""
    if not NEO4J_AGENT_AVAILABLE:
        return None

    if 'smol_agent' not in st.session_state:
        client = get_neo4j_client()
        st.session_state.smol_agent = SmolLM2Agent(
            model=OLLAMA_MODEL,
            neo4j_client=client,
            verbose=True,
            max_iterations=10
        )
    return st.session_state.smol_agent


def connect_neo4j():
    """Connect to Neo4j database."""
    client = get_neo4j_client()
    if client:
        return client.connect()
    return False


def render_chat_panel():
    """Render the SmolLM2 Chat panel with Neo4j integration."""
    if not NEO4J_AGENT_AVAILABLE:
        st.warning("Agent Neo4j non disponible. Installez le package `neo4j` avec: pip install neo4j")
        return

    st.subheader("💬 Chat avec SmolLM2")
    st.caption("Discutez avec l'agent pour explorer et modifier votre base Neo4j")

    # Connection status and button
    col1, col2 = st.columns([3, 1])

    with col1:
        if st.session_state.get('neo4j_connected'):
            st.success("✅ Connecté à Neo4j")
        else:
            st.info("⚠️ Non connecté à Neo4j")

    with col2:
        if st.button("🔌 Connecter Neo4j"):
            with st.spinner("Connexion à Neo4j..."):
                try:
                    if connect_neo4j():
                        st.session_state['neo4j_connected'] = True
                        st.success("Connecté!")
                        st.rerun()
                    else:
                        st.error("Échec de connexion")
                except Exception as e:
                    st.error(f"Erreur: {e}")

    st.divider()

    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg['role']):
                st.write(msg['content'])

                # Show tool calls if any
                if msg.get('tool_calls'):
                    with st.expander("🔧 Outils utilisés"):
                        for tool in msg['tool_calls']:
                            st.code(f"{tool['name']}: {tool.get('result', 'N/A')[:200]}")

    # Chat input
    if prompt := st.chat_input("Posez une question sur vos données...", key="chat_input"):
        print(f"\n{'='*80}")
        print(f"[CHAT] User input received: {prompt}")
        print(f"{'='*80}")

        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })

        # Get response
        with st.spinner("🤖 Réflexion en cours..."):
            try:
                client = get_neo4j_client()
                print(f"[CHAT] Neo4j client: {client}")
                print(f"[CHAT] Neo4j connected: {st.session_state.get('neo4j_connected')}")
                print(f"[CHAT] Client is_connected: {client.is_connected if client else 'N/A'}")

                # Check if connected
                if st.session_state.get('neo4j_connected') and client and client.is_connected:
                    print(f"[CHAT] Using full agent with Neo4j")
                    # Use full agent for complex tasks
                    agent = get_agent()
                    result = agent.run(prompt, context={"data_model": st.session_state.get('mcp_model')})

                    response = result.answer
                    tool_calls = [
                        {"name": step.tool_name, "result": step.observation}
                        for step in result.steps if step.tool_name
                    ]
                    print(f"[CHAT] Agent response: {response[:200]}...")
                else:
                    print(f"[CHAT] Using simple_chat (no Neo4j)")
                    # Use simple chat without Neo4j
                    response = simple_chat(prompt, neo4j_client=None, model=OLLAMA_MODEL, verbose=True)
                    tool_calls = []
                    print(f"[CHAT] Simple chat response: {response[:200]}...")

                # Add assistant response
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "tool_calls": tool_calls
                })
                print(f"[CHAT] Response added to history")

            except Exception as e:
                import traceback
                print(f"[CHAT] ERROR: {str(e)}")
                print(f"[CHAT] Traceback:\n{traceback.format_exc()}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Erreur: {str(e)}"
                })

        print(f"[CHAT] Calling st.rerun()")
        st.rerun()

    # Quick actions
    st.divider()
    st.markdown("**Actions rapides:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Voir le schéma", width="stretch", disabled=not st.session_state.get('neo4j_connected')):
            st.session_state.chat_history.append({"role": "user", "content": "Montre-moi le schéma de la base de données"})
            st.rerun()

    with col2:
        if st.button("📈 Compter les noeuds", width="stretch", disabled=not st.session_state.get('neo4j_connected')):
            st.session_state.chat_history.append({"role": "user", "content": "Combien de noeuds et relations y a-t-il ?"})
            st.rerun()

    with col3:
        if st.button("🗑️ Effacer le chat", width="stretch"):
            st.session_state.chat_history = []
            st.rerun()


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state for the redesign workflow."""
    defaults = {
        'current_step': 0,
        'answers': {},
        'datasets': {},
        'data_model': None,
        'raw_data': None,
        'workflow_mode': 'descent',  # 'descent' or 'ascent'
        # Navigation session (User Story 5)
        'nav_session': None,
        'nav_mode': False,  # Toggle between guided workflow and free navigation
        'nav_history_visible': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_workflow():
    """Reset the workflow to start over, including clearing Neo4j database completely."""
    # Clear Neo4j database if connected
    try:
        client = get_neo4j_client()
        if client and client._connected:
            # 1. Delete all nodes and relationships
            client.write_cypher("MATCH (n) DETACH DELETE n")
            print("[RESET] Deleted all nodes and relationships")

            # 2. Drop all constraints
            constraints = client.run_cypher("SHOW CONSTRAINTS")
            if constraints.success and constraints.data:
                for c in constraints.data:
                    name = c.get('name')
                    if name:
                        client.write_cypher(f"DROP CONSTRAINT {name} IF EXISTS")
                        print(f"[RESET] Dropped constraint: {name}")

            # 3. Drop all indexes (except system lookup indexes)
            indexes = client.run_cypher("SHOW INDEXES")
            if indexes.success and indexes.data:
                for idx in indexes.data:
                    name = idx.get('name')
                    idx_type = idx.get('type', '')
                    if name and 'LOOKUP' not in idx_type.upper():
                        try:
                            client.write_cypher(f"DROP INDEX {name} IF EXISTS")
                            print(f"[RESET] Dropped index: {name}")
                        except:
                            pass

            # 4. Clear property keys using APOC (if available)
            try:
                client.write_cypher("CALL apoc.schema.assert({}, {})")
                print("[RESET] Cleared schema with APOC")
            except:
                pass

            # 5. Clear query caches
            try:
                client.run_cypher("CALL db.clearQueryCaches()")
                print("[RESET] Cleared query caches")
            except:
                pass

            print("[RESET] Neo4j database fully reset")
    except Exception as e:
        print(f"[RESET] Could not clear Neo4j database: {e}")

    # Reset session state
    st.session_state.current_step = 0
    st.session_state.answers = {}
    st.session_state.datasets = {}
    st.session_state.data_model = None
    st.session_state.raw_data = None
    st.session_state.neo4j_connected = False


# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

DESCENT_STEPS = [
    {"id": "upload", "title": "Upload Data", "level": "L4", "emoji": "📁",
     "question": "Upload your raw data files to begin"},
    {"id": "entities", "title": "Define Entities", "level": "L4→L3", "emoji": "🏗️",
     "question": "What are the main entities you want in your knowledge graph?"},
    {"id": "domains", "title": "Isolate Domains", "level": "L3→L2", "emoji": "📂",
     "question": "Query the graph to isolate domain-specific subsets"},
    {"id": "features", "title": "Extract Features", "level": "L2→L1", "emoji": "📊",
     "question": "Extract a column to create vectors for analysis"},
    {"id": "metric", "title": "Compute Metric", "level": "L1→L0", "emoji": "🎯",
     "question": "What aggregation metric do you want to compute?"},
    {"id": "results", "title": "Results", "level": "L0", "emoji": "✅",
     "question": "Review your atomic metrics and data model"}
]


# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================

def create_demo_data():
    """Create sample demo data for testing."""
    import numpy as np
    np.random.seed(42)

    prefixes = ['CA', 'VOL', 'NB', 'TX', 'MT', 'ETP']
    segments = ['B2B', 'B2C', 'PRO', 'PART', 'ENT']
    locations = ['FR', 'INT', 'EU', 'DOM', 'EXP']
    products = ['EXPRESS', 'STD', 'ECO', 'PREM']

    data = []
    for i in range(150):
        prefix = np.random.choice(prefixes)
        name = f"{prefix}_{np.random.choice(segments)}_{np.random.choice(locations)}_{np.random.choice(products)}"
        data.append({
            'indicator_name': name,
            'description': f'Business indicator {i+1}',
            'source_system': f'System_{np.random.randint(1, 6)}',
            'created_date': f'2024-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}'
        })

    return {'demo_indicators.csv': pd.DataFrame(data)}


def build_knowledge_graph(raw_data, data_model):
    """Build L3 knowledge graph from raw data using the data model."""
    print(f"\n{'='*60}")
    print(f"[GRAPH BUILD] Building knowledge graph...")
    print(f"[GRAPH BUILD] Data sources: {list(raw_data.keys())}")
    print(f"{'='*60}")
    G = nx.Graph()
    core_label = data_model.nodes[0].label if data_model.nodes else "Entity"
    print(f"[GRAPH BUILD] Core label: {core_label}")

    for filename, df in raw_data.items():
        # Add source node
        source_id = f"source_{filename}"
        G.add_node(source_id, type="Source", name=filename)
        print(f"[GRAPH BUILD] Processing {filename} with {len(df)} rows, {len(df.columns)} columns")
        print(f"[GRAPH BUILD] Columns: {list(df.columns)}")

        # Find the best name column (prioritize columns with 'name', 'title', 'label', 'indicator')
        name_col = None
        priority_keywords = ['indicator', 'name', 'title', 'label', 'description', 'id']

        for keyword in priority_keywords:
            for col in df.columns:
                if keyword in col.lower() and df[col].dtype == 'object':
                    # Check that values are not too long (avoid concatenated data)
                    avg_len = df[col].dropna().astype(str).str.len().mean()
                    if avg_len < 200:  # Reasonable name length
                        name_col = col
                        print(f"[GRAPH BUILD] Selected name column: '{col}' (keyword: {keyword}, avg_len: {avg_len:.0f})")
                        break
            if name_col:
                break

        # Fallback: find any string column with reasonable length values
        if not name_col:
            for col in df.columns:
                if df[col].dtype == 'object':
                    avg_len = df[col].dropna().astype(str).str.len().mean()
                    if avg_len < 200:
                        name_col = col
                        print(f"[GRAPH BUILD] Fallback name column: '{col}' (avg_len: {avg_len:.0f})")
                        break

        if not name_col and len(df.columns) > 0:
            name_col = df.columns[0]
            print(f"[GRAPH BUILD] Using first column as name: '{name_col}'")

        if name_col:
            for idx, row in df.iterrows():
                entity_name = str(row.get(name_col, f'Entity_{idx}'))
                if entity_name == 'nan' or pd.isna(entity_name):
                    continue

                entity_id = f"{filename}_{idx}"
                node_attrs = {
                    "type": core_label,
                    "name": entity_name,
                    "source_file": filename
                }

                # Add other columns as properties
                for col in df.columns:
                    if col != name_col:
                        node_attrs[col.lower().replace(" ", "_")] = str(row.get(col, ""))

                G.add_node(entity_id, **node_attrs)
                G.add_edge(entity_id, source_id, relation="FOUND_IN")

    print(f"[GRAPH BUILD] DONE: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def categorize_by_domains(graph, domains, use_semantic=True, threshold=0.3):
    """Categorize graph nodes by domains using keyword + semantic matching."""
    print(f"\n{'='*60}")
    print(f"[CATEGORIZE] Categorizing by domains: {domains}")
    print(f"[CATEGORIZE] Semantic matching: {use_semantic}, threshold: {threshold}")
    print(f"{'='*60}")
    items = []
    item_data = []

    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") not in ["Source"]:
            name = attrs.get("name", str(node))
            items.append(name)
            item_data.append({"id": node, "name": name, **attrs})

    print(f"[CATEGORIZE] Found {len(items)} items to categorize")
    matcher = SemanticMatcher(use_embeddings=use_semantic)
    print(f"[CATEGORIZE] Running semantic matcher...")
    categorized = matcher.categorize_by_domains(items, domains, threshold)

    results = {}
    for domain, matches in categorized.items():
        matched_names = {item for item, score in matches}
        domain_data = [d for d in item_data if d.get("name") in matched_names]
        results[domain] = pd.DataFrame(domain_data) if domain_data else pd.DataFrame()
        print(f"[CATEGORIZE] {domain}: {len(domain_data)} items matched")

    print(f"[CATEGORIZE] DONE: categorized into {len(results)} domains")
    return results


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_sidebar():
    """Render the sidebar with navigation and info."""
    with st.sidebar:
        # Load and display logo
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "descent_ascent_logo.webp")
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
        else:
            st.title("🔄 Data Redesign")
        st.caption("Interactive Q&A Workflow")

        st.divider()

        # LLM Configuration
        st.markdown("### 🤖 LLM Settings")

        llm_provider = st.radio(
            "Provider:",
            options=["ollama", "openai"],
            index=0 if st.session_state.get('llm_provider', 'ollama') == 'ollama' else 1,
            horizontal=True,
            key="llm_provider_radio"
        )
        st.session_state['llm_provider'] = llm_provider

        if llm_provider == "openai":
            api_key = st.text_input(
                "OpenAI API Key:",
                type="password",
                value=st.session_state.get('openai_api_key', ''),
                key="openai_key_input"
            )
            st.session_state['openai_api_key'] = api_key

            model = st.selectbox(
                "Model:",
                options=OPENAI_MODELS,
                index=OPENAI_MODELS.index(st.session_state.get('openai_model', 'gpt-4o-mini')) if st.session_state.get('openai_model', 'gpt-4o-mini') in OPENAI_MODELS else 1,
                key="openai_model_select"
            )
            st.session_state['openai_model'] = model

            if api_key:
                st.success("✅ API Key set")
            else:
                st.warning("⚠️ Enter API key")
        else:
            ollama_model = st.text_input(
                "Ollama Model:",
                value=st.session_state.get('ollama_model', OLLAMA_MODEL),
                key="ollama_model_input"
            )
            st.session_state['ollama_model'] = ollama_model
            st.caption("e.g., qwen2.5-coder:7b, codellama:13b")

        st.divider()

        # Current step indicator
        current = DESCENT_STEPS[st.session_state.current_step]
        st.info(f"**{current['emoji']} {current['level']}**\n\n{current['title']}")

        st.divider()

        # Progress
        st.markdown("### Progress")
        progress = st.session_state.current_step / (len(DESCENT_STEPS) - 1)
        st.progress(progress)

        # Step list
        for i, step in enumerate(DESCENT_STEPS):
            if i < st.session_state.current_step:
                st.markdown(f"✅ ~~{step['level']}: {step['title']}~~")
            elif i == st.session_state.current_step:
                st.markdown(f"🔵 **{step['level']}: {step['title']}**")
            else:
                st.markdown(f"⚪ {step['level']}: {step['title']}")

        st.divider()

        # Reset button
        if st.button("🔄 Start Over", width="stretch"):
            reset_workflow()
            st.rerun()

        # Mode toggle (Guided Workflow vs Free Navigation)
        st.markdown("### 🧭 Mode")
        nav_mode = st.toggle(
            "Free Navigation",
            value=st.session_state.get('nav_mode', False),
            help="Switch between guided workflow and free navigation explorer"
        )
        if nav_mode != st.session_state.get('nav_mode', False):
            st.session_state['nav_mode'] = nav_mode
            st.rerun()

        if nav_mode:
            st.caption("🧭 Explore data freely")
        else:
            st.caption("📋 Step-by-step workflow")

        st.divider()

        # Help
        with st.expander("ℹ️ About"):
            st.markdown("""
            This app implements the **Data Redesign Method** from the Intuitiveness framework.

            **Descent** (L4→L0): Reduce complexity through guided questions
            **Ascent** (L0→L3): Rebuild with intentional structure

            **Modes**:
            - 📋 **Guided Workflow**: Step-by-step Q&A to transform your data
            - 🧭 **Free Navigation**: Explore the abstraction hierarchy freely

            [📄 Read the paper](https://example.com)
            """)


def render_step_header():
    """Render the current step header."""
    step = DESCENT_STEPS[st.session_state.current_step]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"{step['emoji']} {step['title']}")
    with col2:
        st.metric("Level", step['level'])

    st.markdown(f"**{step['question']}**")
    st.divider()


def render_navigation():
    """Render navigation buttons."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.session_state.current_step > 0:
            if st.button("← Previous", width="stretch"):
                st.session_state.current_step -= 1
                st.rerun()

    with col3:
        if st.session_state.current_step < len(DESCENT_STEPS) - 1:
            if st.button("Next →", type="primary", width="stretch"):
                st.session_state.current_step += 1
                st.rerun()


# ============================================================================
# STEP RENDERERS
# ============================================================================

def render_upload_step():
    """Step 0: Upload raw data."""
    st.info("📁 Upload one or more CSV files, or use demo data to explore the method.")

    tab1, tab2 = st.tabs(["📤 Upload Files", "🎮 Use Demo Data"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Choose CSV files",
            type=['csv'],
            accept_multiple_files=True
        )

        if uploaded_files:
            print(f"\n{'='*60}")
            print(f"[FILE UPLOAD] Processing {len(uploaded_files)} files...")
            print(f"{'='*60}")
            raw_data = {}
            for file in uploaded_files:
                print(f"[FILE UPLOAD] Loading: {file.name}")
                try:
                    # Try multiple encodings and parsing options
                    best_df = None
                    best_cols = 0
                    best_encoding = None
                    best_delimiter = None

                    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                    delimiters = [';', ',', '\t', '|']  # Try semicolon first (common in EU data)

                    for encoding in encodings:
                        for delimiter in delimiters:
                            try:
                                file.seek(0)  # Reset file pointer
                                df = pd.read_csv(
                                    file,
                                    encoding=encoding,
                                    delimiter=delimiter,
                                    on_bad_lines='skip',
                                    engine='python'
                                )
                                # Pick the parsing that gives the MOST columns (best structure)
                                if len(df) > 0 and len(df.columns) > best_cols:
                                    best_df = df
                                    best_cols = len(df.columns)
                                    best_encoding = encoding
                                    best_delimiter = delimiter
                                    print(f"[FILE UPLOAD] Found better parse: {len(df.columns)} cols with encoding={encoding}, delimiter='{delimiter}'")
                            except Exception:
                                continue

                    if best_df is None or best_df.empty:
                        raise ValueError("Could not parse file with any known format")

                    df = best_df
                    print(f"[FILE UPLOAD] BEST PARSE: encoding={best_encoding}, delimiter='{best_delimiter}', {len(df.columns)} columns")
                    print(f"[FILE UPLOAD] Columns: {list(df.columns)[:5]}...")

                    # Save file to disk for Neo4j LOAD CSV
                    upload_dir = os.path.join(os.path.dirname(__file__), "csv_uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    saved_path = os.path.join(upload_dir, file.name)
                    df.to_csv(saved_path, index=False)
                    print(f"[FILE UPLOAD] Saved to: {saved_path}")

                    raw_data[file.name] = df

                    # Track file paths for Neo4j
                    if 'csv_paths' not in st.session_state:
                        st.session_state['csv_paths'] = {}
                    st.session_state['csv_paths'][file.name] = saved_path

                    print(f"[FILE UPLOAD] Loaded {file.name}: {df.shape[0]} rows × {df.shape[1]} columns")
                    st.success(f"✅ {file.name}: {df.shape[0]} rows × {df.shape[1]} columns")
                except Exception as e:
                    print(f"[FILE UPLOAD] ERROR loading {file.name}: {e}")
                    st.error(f"❌ Error loading {file.name}: {e}")

            if raw_data:
                st.session_state.raw_data = raw_data
                st.session_state.datasets['l4'] = Level4Dataset(raw_data)

                with st.expander("👁️ Preview Data"):
                    for name, df in raw_data.items():
                        st.subheader(name)
                        st.dataframe(df.head(10), width="stretch")

    with tab2:
        st.markdown("Load sample logistics indicator data to test the workflow.")
        if st.button("🎮 Load Demo Data", type="primary"):
            demo_data = create_demo_data()

            # Save demo files to disk for Neo4j LOAD CSV
            upload_dir = os.path.join(os.path.dirname(__file__), "csv_uploads")
            os.makedirs(upload_dir, exist_ok=True)
            st.session_state['csv_paths'] = {}
            for filename, df in demo_data.items():
                saved_path = os.path.join(upload_dir, filename)
                df.to_csv(saved_path, index=False)
                st.session_state['csv_paths'][filename] = saved_path
                print(f"[DEMO DATA] Saved to: {saved_path}")

            st.session_state.raw_data = demo_data
            st.session_state.datasets['l4'] = Level4Dataset(demo_data)
            st.success("Demo data loaded!")
            st.rerun()

    # Show loaded data summary
    if st.session_state.raw_data:
        st.divider()
        st.subheader("📊 Loaded Data Summary")
        summary = []
        for name, df in st.session_state.raw_data.items():
            summary.append({"File": name, "Rows": df.shape[0], "Columns": df.shape[1]})
        st.dataframe(pd.DataFrame(summary), width="stretch")


def render_entities_step():
    """Step 1: L4 → L3 Transition - Transform CSVs into Knowledge Graph."""
    if not st.session_state.raw_data:
        st.warning("⚠️ Please upload data first.")
        return

    # ========================================================================
    # SECTION 1: AI-Powered Entity Discovery
    # ========================================================================
    st.subheader("🤖 AI-Powered Entity Discovery")

    # Custom instructions input
    custom_instructions = st.text_area(
        "💡 **Context & Instructions** (optional)",
        value=st.session_state.get('entity_instructions', ''),
        height=100,
        placeholder="Ex: Je cherche à analyser les prix immobiliers par commune. Focus sur les relations géographiques et temporelles...",
        help="Décrivez ce que vous cherchez dans les données. Ces instructions seront ajoutées au prompt envoyé au LLM.",
        key="entity_instructions_input"
    )
    if custom_instructions != st.session_state.get('entity_instructions', ''):
        st.session_state['entity_instructions'] = custom_instructions

    col1, col2 = st.columns([2, 1])
    with col1:
        provider = st.session_state.get('llm_provider', 'ollama')
        if provider == 'openai':
            model_name = st.session_state.get('openai_model', 'gpt-4o-mini')
            st.caption(f"🔑 OpenAI: `{model_name}`")
        else:
            model_name = st.session_state.get('ollama_model', OLLAMA_MODEL)
            st.caption(f"🦙 Ollama: `{model_name}`")
    with col2:
        if st.button("🔍 Analyze Data with AI", type="primary"):
            print(f"\n[BUTTON] 'Analyze Data with AI' clicked")
            with st.spinner("🤖 Analyzing your data..."):
                user_instructions = st.session_state.get('entity_instructions', '')
                suggestion = analyze_data_for_entities(st.session_state.raw_data, user_instructions)
                if suggestion.startswith("ERROR"):
                    print(f"[BUTTON] Entity analysis FAILED")
                    st.error(suggestion)
                else:
                    st.session_state['llm_suggestion'] = suggestion
                    print(f"[BUTTON] Entity analysis SUCCESS: {suggestion[:100]}...")
                    st.success("AI analysis complete!")

    # ========================================================================
    # SECTION 2: Editable Data Model
    # ========================================================================
    if 'llm_suggestion' in st.session_state:
        st.divider()
        st.subheader("📝 Data Model (Editable)")

        col_editor, col_schema = st.columns([1, 1])

        with col_editor:
            edited_model = st.text_area(
                "Review and edit the suggested data model:",
                value=st.session_state.get('edited_model', st.session_state['llm_suggestion']),
                height=350,
                key="model_editor"
            )

            if edited_model != st.session_state.get('edited_model'):
                st.session_state['edited_model'] = edited_model

        with col_schema:
            st.markdown("**📊 Schema Visualization**")

            # Parse the current model to visualize
            current_model_text = st.session_state.get('edited_model', st.session_state.get('llm_suggestion', ''))
            schema = parse_data_model(current_model_text)

            if schema['entities']:
                import matplotlib.pyplot as plt
                import networkx as nx

                # Build schema graph
                G = nx.DiGraph()

                # Add entity nodes with properties as labels
                for entity in schema['entities']:
                    props = schema['properties'].get(entity, [])
                    props_label = "\n".join(props[:4]) if props else ""
                    G.add_node(entity, props=props_label)

                # Add relationship edges
                for rel in schema['relationships']:
                    if isinstance(rel, dict) and 'from' in rel and 'to' in rel:
                        G.add_edge(rel['from'], rel['to'], label=rel.get('type', 'RELATED_TO'))
                    elif len(rel) >= 3:
                        G.add_edge(rel[0], rel[2], label=rel[1])

                # Create visualization
                fig, ax = plt.subplots(figsize=(7, 5))
                ax.set_facecolor('#0e1117')
                fig.patch.set_facecolor('#0e1117')

                # Layout - use shell layout for better visibility with few nodes
                if len(G.nodes()) > 0:
                    if len(G.nodes()) <= 4:
                        pos = nx.shell_layout(G)
                    else:
                        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

                    # Scale positions to leave margin
                    for node in pos:
                        pos[node] = pos[node] * 0.7

                    # Draw edges FIRST (so they appear behind nodes)
                    if G.number_of_edges() > 0:
                        nx.draw_networkx_edges(G, pos, ax=ax,
                                              edge_color='#64B5F6',
                                              arrows=True,
                                              arrowsize=25,
                                              arrowstyle='-|>',
                                              connectionstyle='arc3,rad=0.15',
                                              width=2.5,
                                              min_source_margin=30,
                                              min_target_margin=30)

                        # Draw edge labels (relationship types)
                        edge_labels = nx.get_edge_attributes(G, 'label')
                        nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax,
                                                    font_size=9,
                                                    font_color='#90CAF9',
                                                    bbox=dict(boxstyle='round,pad=0.3',
                                                             facecolor='#1e1e1e',
                                                             edgecolor='#64B5F6',
                                                             alpha=0.9))

                    # Draw nodes
                    nx.draw_networkx_nodes(G, pos, ax=ax,
                                          node_color='#4CAF50',
                                          node_size=3000,
                                          alpha=0.95)

                    # Draw node labels (entity names)
                    nx.draw_networkx_labels(G, pos, ax=ax,
                                           font_size=11,
                                           font_weight='bold',
                                           font_color='white')

                ax.axis('off')
                ax.set_xlim(-1.2, 1.2)
                ax.set_ylim(-1.2, 1.2)
                plt.tight_layout(pad=0.5)
                st.pyplot(fig)
                plt.close()

                # Debug: show relationship count
                st.caption(f"Nodes: {len(schema['entities'])} | Relationships: {len(schema['relationships'])}")

                # Show properties and relationships below the graph
                with st.expander("📋 Properties & Relationships", expanded=True):
                    st.markdown("**Nodes:**")
                    for entity in schema['entities']:
                        props = schema['properties'].get(entity, [])
                        if props:
                            st.code(f"(:{entity} {{{', '.join(props)}}})", language=None)
                        else:
                            st.code(f"(:{entity})", language=None)

                    if schema['relationships']:
                        st.markdown("**Relationships:**")
                        for rel in schema['relationships']:
                            if isinstance(rel, dict) and 'from' in rel and 'to' in rel:
                                st.code(f"(:{rel['from']})-[:{rel.get('type', 'RELATED_TO')}]->(:{rel['to']})", language=None)
                            elif len(rel) >= 3:
                                st.code(f"(:{rel[0]})-[:{rel[1]}]->(:{rel[2]})", language=None)
                    else:
                        st.caption("*No relationships defined yet*")
            else:
                st.warning("No entities parsed from the model")

        # ========================================================================
        # SECTION 2.5: Map COLUMNS to Entities (REQUIRED)
        # ========================================================================
        st.divider()
        st.subheader("🗺️ Map Columns to Entities")
        st.caption("**Required**: Assign each column to an entity from the data model. Columns assigned to the same entity will form nodes of that type.")

        # Parse entities from current data model
        current_model = st.session_state.get('edited_model', st.session_state.get('llm_suggestion', ''))
        parsed = parse_data_model(current_model)
        model_entities = parsed['entities']
        model_properties = parsed.get('properties', {})  # LLM suggested properties per entity

        if not model_entities:
            st.error("❌ No entities found in data model! Please check the format above.")
        else:
            st.info(f"**Entities from LLM model:** {', '.join(model_entities)}")

            # Initialize column mapping in session state
            if 'column_to_entity_mapping' not in st.session_state:
                st.session_state['column_to_entity_mapping'] = {}

            # Collect all columns from all CSVs with their source
            all_columns = []  # List of (csv_name, column_name)
            for filename, df in st.session_state.raw_data.items():
                for col in df.columns:
                    all_columns.append((filename, col))

            # Options: entities + "Ignore"
            entity_options = ["-- Ignore --"] + model_entities

            # Auto-suggest based on LLM properties
            def suggest_entity_for_column(col_name):
                col_lower = col_name.lower().replace('_', '').replace('-', '')
                for entity, props in model_properties.items():
                    for prop in props:
                        prop_lower = prop.lower().replace('_', '').replace('-', '')
                        if prop_lower in col_lower or col_lower in prop_lower:
                            return entity
                return "-- Ignore --"

            # Group columns by CSV for display
            st.markdown("---")
            for filename, df in st.session_state.raw_data.items():
                with st.expander(f"📄 **{filename}** ({len(df.columns)} columns)", expanded=True):
                    cols_per_row = 2
                    columns_list = list(df.columns)

                    for i in range(0, len(columns_list), cols_per_row):
                        row_cols = st.columns(cols_per_row)
                        for j, st_col in enumerate(row_cols):
                            if i + j < len(columns_list):
                                col_name = columns_list[i + j]
                                col_key = f"{filename}::{col_name}"

                                with st_col:
                                    # Get current selection or auto-suggest
                                    current = st.session_state['column_to_entity_mapping'].get(
                                        col_key,
                                        suggest_entity_for_column(col_name)
                                    )
                                    if current not in entity_options:
                                        current = "-- Ignore --"

                                    selected = st.selectbox(
                                        f"`{col_name}`",
                                        options=entity_options,
                                        index=entity_options.index(current),
                                        key=f"col_map_{col_key}",
                                    )
                                    st.session_state['column_to_entity_mapping'][col_key] = selected

            # Show summary: which columns are assigned to each entity
            st.markdown("---")
            st.markdown("**Mapping Summary:**")
            entity_columns = {e: [] for e in model_entities}
            ignored_columns = []

            for col_key, entity in st.session_state['column_to_entity_mapping'].items():
                if entity == "-- Ignore --":
                    ignored_columns.append(col_key)
                else:
                    entity_columns[entity].append(col_key)

            for entity in model_entities:
                cols = entity_columns[entity]
                if cols:
                    col_names = [c.split('::')[1] for c in cols]
                    st.success(f"✅ **{entity}**: {', '.join(col_names)}")
                else:
                    st.warning(f"⚠️ **{entity}**: No columns assigned!")

            if ignored_columns:
                st.caption(f"Ignored: {len(ignored_columns)} columns")

        # ========================================================================
        # SECTION 3: Connect to Neo4j
        # ========================================================================
        st.divider()
        st.subheader("🔌 Connect to Neo4j")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.get('neo4j_connected'):
                st.success("✅ Connected to Neo4j")
            else:
                st.info("⚠️ Not connected to Neo4j")
        with col2:
            if st.button("🔌 Connect to Neo4j"):
                with st.spinner("Connecting..."):
                    if connect_neo4j():
                        st.session_state['neo4j_connected'] = True
                        st.success("Connected!")
                        st.rerun()
                    else:
                        st.error("Connection failed")

        # ========================================================================
        # SECTION 4: Add Data to Neo4j
        # ========================================================================
        st.divider()
        st.subheader("📤 Add Data to Neo4j")

        # Check prerequisites
        execute_disabled = not st.session_state.get('neo4j_connected')
        col_mapping = st.session_state.get('column_to_entity_mapping', {})
        # Check that at least one entity has columns assigned
        entities_with_columns = set(e for e in col_mapping.values() if e != "-- Ignore --")
        mapping_missing = len(entities_with_columns) == 0

        col1, col2 = st.columns([2, 1])
        with col1:
            limit = st.number_input("Row limit per entity:", min_value=10, max_value=1000, value=100, step=10)
        with col2:
            execute_clicked = st.button("⚡ Generate & Execute", type="primary", disabled=execute_disabled or mapping_missing)

        if execute_disabled:
            st.caption("⚠️ Connect to Neo4j first to enable execution")
        if mapping_missing:
            st.caption("⚠️ Assign columns to at least one entity above first")

        # Execution happens BELOW the columns (not inside col2)
        if execute_clicked:
            with st.spinner("Generating and executing Cypher queries..."):
                # Generate Cypher using COLUMN-to-Entity mapping
                cypher_result = generate_direct_insert_queries(
                    st.session_state.raw_data,
                    st.session_state.get('edited_model', ''),
                    column_to_entity_mapping=st.session_state['column_to_entity_mapping'],
                    limit=limit
                )
                st.session_state['generated_cypher'] = cypher_result
                # Execute queries - this also calls visualize_neo4j_graph()
                execute_cypher_queries(cypher_result)

        # Show generated Cypher preview (collapsed by default)
        if 'generated_cypher' in st.session_state:
            with st.expander("📜 View Generated Cypher Queries"):
                st.code(st.session_state['generated_cypher'][:3000] + "\n...", language="cypher")
                st.download_button(
                    "📥 Download Cypher",
                    data=st.session_state['generated_cypher'],
                    file_name="neo4j_import.cypher",
                    mime="text/plain"
                )


def render_domains_step():
    """Step 2: L3→L2 - Domain Isolation.

    Query the Neo4j knowledge graph (L3) and isolate domain-specific subsets (L2).
    Based on the scientific paper: "We queried the graph to isolate indicators
    related to the 'revenues', 'volumes', and 'ETP'."
    """
    # Check if Neo4j is connected
    if not st.session_state.get('neo4j_connected'):
        st.warning("⚠️ Please connect to Neo4j and complete the L4→L3 step first.")
        return

    st.markdown("""
    **L3 → L2: Domain Isolation**

    Query the knowledge graph to extract domain-specific tables. The system uses:
    1. 🔤 **Keyword matching** - Direct string matching on node properties
    2. 🧠 **Semantic similarity** - Embedding-based matching (multilingual-e5-small)
    """)

    # ========================================================================
    # KNOWLEDGE GRAPH PREVIEW (L3)
    # ========================================================================
    client = get_neo4j_client()
    if not client:
        st.error("Could not connect to Neo4j")
        return

    # Get entity types (labels) from the graph
    labels_query = "CALL db.labels() YIELD label RETURN label"
    labels_result = client.run_cypher(labels_query)

    if not labels_result.success or not labels_result.data:
        st.warning("No entities found in Neo4j. Please run L4→L3 first.")
        return

    available_labels = [r['label'] for r in labels_result.data]

    # Show L3 Knowledge Graph data - LINKED DATA VIEW
    st.subheader("🕸️ L3 Knowledge Graph - Linked Data")

    # Get relationship types
    rel_types_query = """
    MATCH ()-[r]->()
    RETURN DISTINCT type(r) as rel_type,
           head(labels(startNode(r))) as from_label,
           head(labels(endNode(r))) as to_label,
           count(*) as count
    """
    rel_types_result = client.run_cypher(rel_types_query)

    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        node_count_query = "MATCH (n) RETURN count(n) as cnt"
        node_count = client.run_cypher(node_count_query)
        total_nodes = node_count.data[0]['cnt'] if node_count.success and node_count.data else 0
        st.metric("Total Nodes", total_nodes)
    with col2:
        rel_count_query = "MATCH ()-[r]->() RETURN count(r) as cnt"
        rel_count = client.run_cypher(rel_count_query)
        total_rels = rel_count.data[0]['cnt'] if rel_count.success and rel_count.data else 0
        st.metric("Total Relationships", total_rels)
    with col3:
        st.metric("Entity Types", len(available_labels))

    # Show linked data tables - one per relationship type
    if rel_types_result.success and rel_types_result.data:
        st.markdown("**📊 Linked Data Tables (Cross-Entity Joins):**")

        # Create tabs for each relationship
        rel_tabs = st.tabs([f"🔗 {r['from_label']} → {r['to_label']}" for r in rel_types_result.data])

        for tab, rel_info in zip(rel_tabs, rel_types_result.data):
            with tab:
                from_label = rel_info['from_label']
                to_label = rel_info['to_label']
                rel_type = rel_info['rel_type']

                st.caption(f"**{from_label}** -[:{rel_type}]-> **{to_label}** ({rel_info['count']} links)")

                # Query linked data - join the two entity types
                linked_query = f"""
                MATCH (a:{from_label})-[r:{rel_type}]->(b:{to_label})
                RETURN properties(a) as from_props,
                       type(r) as relationship,
                       properties(b) as to_props
                LIMIT 100
                """
                linked_result = client.run_cypher(linked_query)

                if linked_result.success and linked_result.data:
                    # Flatten into a single table with prefixed columns
                    rows = []
                    for record in linked_result.data:
                        row = {}
                        # Add from_entity properties with prefix
                        for k, v in record['from_props'].items():
                            if k != 'row_id':  # Skip internal IDs
                                row[f"{from_label}.{k}"] = v
                        # Add relationship
                        row['🔗 Relationship'] = record['relationship']
                        # Add to_entity properties with prefix
                        for k, v in record['to_props'].items():
                            if k != 'row_id':  # Skip internal IDs
                                row[f"{to_label}.{k}"] = v
                        rows.append(row)

                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, height=300)
                else:
                    st.info("No linked data found")
    else:
        st.warning("No relationships found in the graph. The data is not yet linked.")

        # Fallback: show individual entity tables
        st.markdown("**Individual Entity Tables (not yet linked):**")
        entity_tabs = st.tabs([f"📦 {label}" for label in available_labels])

        for tab, label in zip(entity_tabs, available_labels):
            with tab:
                data_query = f"MATCH (n:{label}) RETURN properties(n) as props LIMIT 50"
                data_result = client.run_cypher(data_query)
                if data_result.success and data_result.data:
                    rows = [r['props'] for r in data_result.data]
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, height=200)

    st.divider()

    # ========================================================================
    # STEP 1: Select entity type to categorize
    # ========================================================================
    st.info(f"**Entities in graph:** {', '.join(available_labels)}")

    # ========================================================================
    # STEP 2: Select entity type to categorize
    # ========================================================================
    st.subheader("1️⃣ Select Entity to Categorize")
    selected_entity = st.selectbox(
        "Which entity type do you want to categorize into domains?",
        options=available_labels,
        help="Select the main entity type to extract and categorize"
    )

    # ========================================================================
    # STEP 3: Define domains
    # ========================================================================
    st.subheader("2️⃣ Define Domains")
    default = st.session_state.answers.get('domains', "Revenue, Volume, ETP")
    domains_input = st.text_input(
        "Enter domains (comma-separated):",
        value=default,
        placeholder="e.g., Revenue, Volume, ETP, Finance, Operations"
    )

    col1, col2 = st.columns(2)
    with col1:
        use_semantic = st.checkbox("Use semantic matching", value=True)
    with col2:
        threshold = st.slider("Similarity threshold", 0.1, 0.9, 0.4, 0.05)

    domains_list = [d.strip() for d in domains_input.split(",") if d.strip()]

    # ========================================================================
    # STEP 4: Categorize
    # ========================================================================
    categorize_clicked = st.button("📂 Categorize into Domains", type="primary", disabled=not domains_list)

    if categorize_clicked:
        with st.spinner(f"Querying Neo4j and categorizing {selected_entity} nodes..."):
            # Query all nodes of selected entity type
            node_query = f"""
            MATCH (n:{selected_entity})
            RETURN n, properties(n) as props
            LIMIT 1000
            """
            node_result = client.run_cypher(node_query)

            if not node_result.success or not node_result.data:
                st.error(f"No {selected_entity} nodes found in Neo4j")
                return

            # Extract node data
            nodes_data = []
            for row in node_result.data:
                props = row.get('props', {})
                # Create text representation for semantic matching
                text_repr = " ".join(str(v) for v in props.values() if v)
                nodes_data.append({
                    'text': text_repr,
                    **props
                })

            st.write(f"Found **{len(nodes_data)}** {selected_entity} nodes")

            # Categorize using semantic matching
            domain_dfs = categorize_nodes_by_domains(
                nodes_data, domains_list, use_semantic, threshold
            )

            # Store as L2 datasets
            l2_datasets = {}
            for domain, df in domain_dfs.items():
                l2_datasets[domain] = Level2Dataset(df, name=f"{domain}_{selected_entity}")

            st.session_state.datasets['l2'] = l2_datasets
            st.session_state.answers['domains'] = domains_input
            st.session_state.answers['l3_entity'] = selected_entity

        st.success("✅ Domain isolation complete!")

    # ========================================================================
    # Show results
    # ========================================================================
    if 'l2' in st.session_state.datasets:
        st.divider()
        st.subheader("📋 Domain Tables (L2)")

        tabs = st.tabs([f"{d} ({len(st.session_state.datasets['l2'][d].get_data())})"
                        for d in st.session_state.datasets['l2'].keys()])

        for tab, (domain, l2_ds) in zip(tabs, st.session_state.datasets['l2'].items()):
            with tab:
                df = l2_ds.get_data()
                if not df.empty:
                    st.dataframe(df.head(20), use_container_width=True)
                else:
                    st.info("No items matched this domain")


def categorize_nodes_by_domains(nodes_data: list, domains: list, use_semantic: bool = True, threshold: float = 0.4) -> dict:
    """Categorize nodes into domains using keyword + semantic matching.

    Args:
        nodes_data: List of dicts with node properties and 'text' key
        domains: List of domain names
        use_semantic: Whether to use embedding-based matching
        threshold: Similarity threshold for semantic matching

    Returns:
        Dict of {domain: DataFrame}
    """
    print(f"\n{'='*60}")
    print(f"[L3→L2] Categorizing {len(nodes_data)} nodes into domains: {domains}")
    print(f"[L3→L2] Semantic matching: {use_semantic}, threshold: {threshold}")
    print(f"{'='*60}")

    results = {domain: [] for domain in domains}

    if use_semantic:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        print(f"[L3→L2] Loading embedding model...")
        model = SentenceTransformer('intfloat/multilingual-e5-small')

        # Encode domains
        domain_embeddings = model.encode(domains, convert_to_numpy=True)

        # Encode node texts
        node_texts = [n.get('text', '') for n in nodes_data]
        node_embeddings = model.encode(node_texts, convert_to_numpy=True)

        # Compute similarities
        similarities = cosine_similarity(node_embeddings, domain_embeddings)

        for i, node in enumerate(nodes_data):
            # Find best matching domain
            best_domain_idx = np.argmax(similarities[i])
            best_score = similarities[i][best_domain_idx]

            if best_score >= threshold:
                domain = domains[best_domain_idx]
                node_copy = {k: v for k, v in node.items() if k != 'text'}
                node_copy['_domain_score'] = float(best_score)
                results[domain].append(node_copy)
                print(f"[L3→L2] Node matched '{domain}' (score: {best_score:.3f})")
    else:
        # Simple keyword matching
        for node in nodes_data:
            text = node.get('text', '').lower()
            for domain in domains:
                if domain.lower() in text:
                    node_copy = {k: v for k, v in node.items() if k != 'text'}
                    results[domain].append(node_copy)
                    break

    # Convert to DataFrames
    result_dfs = {}
    for domain, nodes in results.items():
        result_dfs[domain] = pd.DataFrame(nodes) if nodes else pd.DataFrame()
        print(f"[L3→L2] {domain}: {len(nodes)} nodes")

    print(f"[L3→L2] DONE: categorized into {len(result_dfs)} domains")
    return result_dfs


def render_features_step():
    """Step 3: L2→L1 - Reduce table to vector.

    From the theory (Section 2.2):
    Level 1 = "data made of a single entity and several attributes
               OR a single attribute and several entities"

    Two extraction modes:
    - Column extraction: 1 attribute × N entities (vertical slice)
    - Row extraction: 1 entity × N attributes (horizontal slice)
    """
    if 'l2' not in st.session_state.datasets:
        st.warning("⚠️ Please complete the L3→L2 step first (Isolate Domains).")
        return

    st.markdown("""
    **L2 → L1: Reduce Table to Vector**

    *From the theory:* Level 1 = "data made of **a single entity and several attributes**
    OR **a single attribute and several entities**"

    Choose how to slice your table:
    - **Column** → 1 attribute across all entities (e.g., all names)
    - **Row** → 1 entity with all its attributes (e.g., one specific record)
    """)

    # ========================================================================
    # STEP 1: Show current L2 data & select domain
    # ========================================================================
    st.subheader("1️⃣ Select Domain Table (L2)")

    domains = list(st.session_state.datasets['l2'].keys())
    selected_domain = st.selectbox("Domain:", options=domains)

    df = st.session_state.datasets['l2'][selected_domain].get_data()

    if df.empty:
        st.warning(f"No data in {selected_domain} table.")
        return

    st.caption(f"**{selected_domain}**: {len(df)} rows × {len(df.columns)} columns")
    with st.expander("Preview table", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    # ========================================================================
    # STEP 2: Choose extraction mode
    # ========================================================================
    st.subheader("2️⃣ Choose Extraction Mode")

    extraction_mode = st.radio(
        "How do you want to slice the table?",
        options=["column", "row"],
        format_func=lambda x: {
            "column": "📊 Column (1 attribute × N entities)",
            "row": "📋 Row (1 entity × N attributes)"
        }[x],
        horizontal=True
    )

    # Filter out internal columns
    display_columns = [c for c in df.columns if not c.startswith('_')]

    # ========================================================================
    # STEP 3: Select what to extract
    # ========================================================================
    st.subheader("3️⃣ Select What to Extract")

    if extraction_mode == "column":
        # Column extraction: select one attribute
        default_idx = 0
        for preferred in ['name', 'nom', 'label', 'title', 'id']:
            if preferred in display_columns:
                default_idx = display_columns.index(preferred)
                break

        selected_col = st.selectbox(
            "Select attribute (column):",
            options=display_columns,
            index=default_idx
        )

        st.markdown(f"**Preview:** `{selected_col}` values")
        preview = df[selected_col].head(5).tolist()
        st.write(preview)

    else:
        # Row extraction: select one entity
        # Try to find an identifier column
        id_col = None
        for col in ['name', 'nom', 'id', 'label', 'row_id']:
            if col in df.columns:
                id_col = col
                break
        id_col = id_col or df.columns[0]

        row_options = df[id_col].astype(str).tolist()
        selected_row_label = st.selectbox(
            f"Select entity (by `{id_col}`):",
            options=row_options
        )
        selected_row_idx = row_options.index(selected_row_label)

        st.markdown(f"**Preview:** Row for `{selected_row_label}`")
        row_data = df.iloc[selected_row_idx][display_columns]
        st.write(row_data.to_dict())

    # ========================================================================
    # STEP 4: Extract
    # ========================================================================
    extract_clicked = st.button("📊 Extract to L1", type="primary")

    if extract_clicked:
        if extraction_mode == "column":
            # Extract column as series
            series = df[selected_col].dropna()
            l1_data = Level1Dataset(series, name=f"{selected_domain}_{selected_col}")
            extraction_desc = f"Column `{selected_col}` from {selected_domain}"
        else:
            # Extract row as series (attributes become the index)
            row_series = df.iloc[selected_row_idx][display_columns]
            l1_data = Level1Dataset(row_series, name=f"{selected_domain}_{selected_row_label}")
            extraction_desc = f"Row `{selected_row_label}` from {selected_domain}"

        st.session_state.datasets['l1'] = {selected_domain: l1_data}
        st.session_state.answers['feature'] = extraction_desc
        st.session_state.answers['extraction_mode'] = extraction_mode
        st.success(f"✅ Extracted: {extraction_desc}")

    # ========================================================================
    # Show extracted vector
    # ========================================================================
    if 'l1' in st.session_state.datasets:
        st.divider()
        st.subheader("📈 Extracted Vector (L1)")

        mode = st.session_state.answers.get('extraction_mode', 'column')
        desc = st.session_state.answers.get('feature', '')
        st.caption(f"**{desc}**")

        for domain, l1_ds in st.session_state.datasets['l1'].items():
            series = l1_ds.get_data()

            col1, col2 = st.columns([2, 1])

            with col1:
                if mode == "column":
                    st.markdown("**Values (entities):**")
                    st.write(series.head(20).tolist())
                    if len(series) > 20:
                        st.caption(f"... and {len(series) - 20} more")
                else:
                    st.markdown("**Values (attributes):**")
                    st.write(series.to_dict())

            with col2:
                st.markdown("**Stats:**")
                st.metric("Length", len(series))
                st.metric("Unique", series.nunique())
                if series.dtype in ['int64', 'float64']:
                    st.metric("Sum", f"{series.sum():.2f}")


def detect_vector_type(series: pd.Series) -> str:
    """Detect whether a pandas Series contains numbers, categories, or text.

    Returns:
        'numeric' - for int/float data
        'categorical' - for data with few unique values (< 20% of total or < 50 unique)
        'text' - for string data with many unique values
    """
    if series.dtype in ['int64', 'float64', 'int32', 'float32']:
        return 'numeric'

    # For object/string types, check cardinality
    n_unique = series.nunique()
    n_total = len(series)

    # If few unique values relative to total, treat as categorical
    if n_unique < 50 or (n_total > 0 and n_unique / n_total < 0.2):
        return 'categorical'

    return 'text'


def render_metric_step():
    """Step 4: L1→L0 - Reduce vector to single datum.

    From the theory (Section 2.1):
    Level 0 = "data made of a single entity, a single attribute and a single value"
    The datum is a triplet (entity, attribute, value).

    The aggregation method depends on the data type:
    - Numeric: sum, mean, min, max, count
    - Categorical: mode, count, unique count
    - Text: count, unique count, total length
    """
    if 'l1' not in st.session_state.datasets:
        st.warning("⚠️ Please complete the previous step first.")
        return

    st.markdown("""
    **L1→L0**: Reduce your vector to a **single datum** (entity-attribute-value triplet).

    The available aggregations depend on the **data type** of your L1 vector.
    """)

    # Analyze each L1 dataset and show type-specific options
    l1_configs = {}

    for domain, l1_ds in st.session_state.datasets['l1'].items():
        series = l1_ds.get_data()
        data_type = detect_vector_type(series)

        st.markdown(f"#### 📊 {domain}")

        # Show data preview and detected type
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption(f"Vector preview (first 5 values):")
            st.write(series.head().tolist())
        with col2:
            type_icons = {'numeric': '🔢', 'categorical': '🏷️', 'text': '📝'}
            type_labels = {'numeric': 'Numeric', 'categorical': 'Categorical', 'text': 'Text'}
            st.info(f"{type_icons[data_type]} Detected: **{type_labels[data_type]}**")

        # Show distribution visualization for numeric data
        if data_type == 'numeric':
            import matplotlib.pyplot as plt

            with st.expander("📈 Distribution", expanded=True):
                fig, axes = plt.subplots(1, 2, figsize=(10, 3))
                fig.patch.set_facecolor('#0e1117')

                # Histogram
                axes[0].set_facecolor('#0e1117')
                numeric_data = series.dropna()
                axes[0].hist(numeric_data, bins=20, color='#4CAF50', edgecolor='#2E7D32', alpha=0.8)
                axes[0].set_title('Histogram', color='white', fontsize=10)
                axes[0].tick_params(colors='white')
                for spine in axes[0].spines.values():
                    spine.set_color('#333')

                # Box plot
                axes[1].set_facecolor('#0e1117')
                bp = axes[1].boxplot(numeric_data, vert=True, patch_artist=True)
                bp['boxes'][0].set_facecolor('#64B5F6')
                bp['medians'][0].set_color('#FF5722')
                for element in ['whiskers', 'caps']:
                    for line in bp[element]:
                        line.set_color('white')
                axes[1].set_title('Box Plot', color='white', fontsize=10)
                axes[1].tick_params(colors='white')
                for spine in axes[1].spines.values():
                    spine.set_color('#333')

                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

                # Show stats
                stats_col1, stats_col2, stats_col3, stats_col4, stats_col5 = st.columns(5)
                with stats_col1:
                    st.metric("Min", f"{numeric_data.min():.2f}")
                with stats_col2:
                    st.metric("Max", f"{numeric_data.max():.2f}")
                with stats_col3:
                    st.metric("Mean", f"{numeric_data.mean():.2f}")
                with stats_col4:
                    st.metric("Median", f"{numeric_data.median():.2f}")
                with stats_col5:
                    st.metric("Std Dev", f"{numeric_data.std():.2f}")

        # Type-specific aggregation options
        if data_type == 'numeric':
            options = ["sum", "mean", "min", "max", "count", "distribution"]
            format_func = lambda x: {
                "sum": "➕ Sum (total)",
                "mean": "📊 Mean (average)",
                "min": "⬇️ Minimum",
                "max": "⬆️ Maximum",
                "count": "🔢 Count (non-null)",
                "distribution": "📦 Distribution (boîte à moustache)"
            }[x]
        elif data_type == 'categorical':
            options = ["mode", "count", "nunique", "distribution"]
            format_func = lambda x: {
                "mode": "🏆 Mode (most frequent value)",
                "count": "🔢 Count (total entries)",
                "nunique": "🎯 Unique count (distinct values)",
                "distribution": "📊 Distribution (value → count)"
            }[x]
        else:  # text
            options = ["count", "nunique", "total_length", "avg_length"]
            format_func = lambda x: {
                "count": "🔢 Count (total entries)",
                "nunique": "🎯 Unique count (distinct values)",
                "total_length": "📏 Total length (all characters)",
                "avg_length": "📐 Average length (chars per entry)"
            }[x]

        aggregation = st.selectbox(
            f"Aggregation for {domain}:",
            options=options,
            format_func=format_func,
            key=f"agg_{domain}"
        )

        l1_configs[domain] = {
            'series': series,
            'data_type': data_type,
            'aggregation': aggregation
        }

        st.divider()

    if st.button("🎯 Compute L0 Metrics", type="primary"):
        l0_datasets = {}

        for domain, config in l1_configs.items():
            series = config['series']
            data_type = config['data_type']
            aggregation = config['aggregation']

            # Compute based on type and aggregation
            if data_type == 'numeric':
                if aggregation == "sum":
                    value = float(series.sum())
                elif aggregation == "mean":
                    value = round(float(series.mean()), 2)
                elif aggregation == "min":
                    value = float(series.min())
                elif aggregation == "max":
                    value = float(series.max())
                elif aggregation == "distribution":
                    # Store the numeric data for box plot visualization
                    value = {'type': 'numeric_distribution', 'data': series.dropna().tolist()}
                else:  # count
                    value = int(series.count())

            elif data_type == 'categorical':
                if aggregation == "mode":
                    value = series.mode().iloc[0] if len(series.mode()) > 0 else None
                elif aggregation == "count":
                    value = int(len(series))
                elif aggregation == "nunique":
                    value = int(series.nunique())
                else:  # distribution
                    value = series.value_counts().to_dict()

            else:  # text
                if aggregation == "count":
                    value = int(len(series))
                elif aggregation == "nunique":
                    value = int(series.nunique())
                elif aggregation == "total_length":
                    value = int(series.astype(str).str.len().sum())
                else:  # avg_length
                    value = round(float(series.astype(str).str.len().mean()), 1)

            l0_datasets[domain] = Level0Dataset(value, description=f"{aggregation} of {domain}")

        st.session_state.datasets['l0'] = l0_datasets
        st.session_state.answers['l0_configs'] = {k: {'type': v['data_type'], 'aggregation': v['aggregation']} for k, v in l1_configs.items()}
        st.success("✅ L0 datums computed!")

    # Show metrics
    if 'l0' in st.session_state.datasets:
        st.divider()
        st.subheader("🎯 Atomic Metrics (L0)")
        st.caption("Each metric is a **datum** = (entity, attribute, value) triplet")

        for domain, l0_ds in st.session_state.datasets['l0'].items():
            value = l0_ds.get_data()

            if isinstance(value, dict):
                if value.get('type') == 'numeric_distribution':
                    # Numeric distribution - show box plot (boîte à moustache)
                    st.markdown(f"**{domain}** (distribution numérique)")
                    data = value.get('data', [])
                    if data:
                        fig, ax = plt.subplots(figsize=(8, 4))
                        bp = ax.boxplot(data, vert=False, patch_artist=True)
                        bp['boxes'][0].set_facecolor('#4CAF50')
                        bp['boxes'][0].set_alpha(0.7)
                        ax.set_xlabel(domain)
                        ax.set_title(f"Distribution de {domain}")
                        ax.grid(True, alpha=0.3)

                        # Add stats annotation
                        data_series = pd.Series(data)
                        stats_text = f"Min: {data_series.min():.2f} | Q1: {data_series.quantile(0.25):.2f} | Médiane: {data_series.median():.2f} | Q3: {data_series.quantile(0.75):.2f} | Max: {data_series.max():.2f}"
                        ax.set_xlabel(stats_text, fontsize=9)

                        st.pyplot(fig)
                        plt.close(fig)
                    else:
                        st.warning("Pas de données numériques disponibles")
                else:
                    # Categorical distribution case - show as bar chart
                    st.markdown(f"**{domain}** (distribution)")
                    chart_data = pd.DataFrame({
                        'Category': list(value.keys()),
                        'Count': list(value.values())
                    })
                    st.bar_chart(chart_data.set_index('Category'))
            else:
                # Single value - show as metric
                col1, col2, col3 = st.columns(3)
                with col2:
                    st.metric(domain, value)


def render_neo4j_export():
    """Render Neo4j export/write options."""
    st.markdown("### 🗄️ Neo4j Integration")

    if 'l3' not in st.session_state.datasets or not st.session_state.data_model:
        st.warning("No graph data available. Complete the workflow first.")
        return

    from intuitiveness.neo4j_writer import (
        Neo4jMCPWriter,
        generate_full_ingest_script,
        graph_to_neo4j_records
    )

    graph = st.session_state.datasets['l3'].get_data()
    data_model = st.session_state.data_model.to_json()

    # Summary
    records = graph_to_neo4j_records(graph, data_model)
    total_nodes = sum(len(r) for r in records['nodes'].values())
    total_rels = len(records['relationships'])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nodes to Write", total_nodes)
    with col2:
        st.metric("Relationships", total_rels)
    with col3:
        st.metric("Node Types", len(records['nodes']))

    st.divider()

    # MCP Model visualization
    if 'mcp_model' in st.session_state:
        st.markdown("#### Data Model Visualization")
        st.markdown("""
        Ask Claude to generate a Mermaid diagram:
        ```
        Generate Mermaid visualization for the data model using mcp__neo4j-data-modeling__get_mermaid_config_str
        ```
        """)

        with st.expander("View MCP Model JSON"):
            st.json(st.session_state['mcp_model'])

    st.divider()

    # Option 1: Download Cypher script
    st.markdown("#### Option 1: Download Cypher Script")
    st.caption("Run this script in Neo4j Browser or via bolt connection")

    if st.button("📝 Generate Cypher Script"):
        script = generate_full_ingest_script(graph, data_model)
        st.session_state['cypher_script'] = script

    if 'cypher_script' in st.session_state:
        st.download_button(
            "📥 Download Cypher Script",
            data=st.session_state['cypher_script'],
            file_name="neo4j_ingest.cypher",
            mime="text/plain",
            width="stretch"
        )
        with st.expander("Preview Script"):
            st.code(st.session_state['cypher_script'][:2000] + "\n...", language="cypher")

    st.divider()

    # Option 2: Direct write via MCP
    st.markdown("#### Option 2: Write via Neo4j MCP")
    st.caption("Use Claude Code with Neo4j MCP tools to write directly")

    writer = Neo4jMCPWriter()
    queries = writer.prepare_ingest(graph, data_model)
    summary = writer.get_summary()

    st.success(f"""
    **Ready for MCP Write:**
    - {summary.get('constraints', 0)} constraints
    - {summary.get('total_nodes', 0)} nodes in {summary.get('node_batches', 0)} batches
    - {summary.get('total_relationships', 0)} relationships
    """)

    st.markdown("""
    **Ask Claude to write to Neo4j:**
    ```
    Write the data model to neo4j-intuitiveness database using the MCP tools:
    1. First validate with mcp__neo4j-data-modeling__validate_data_model
    2. Create constraints with mcp__neo4j-intuitiveness__write_neo4j_cypher
    3. Write nodes and relationships
    ```
    """)

    # Store queries for potential MCP execution
    st.session_state['neo4j_queries'] = queries

    # Show sample write command
    with st.expander("Sample MCP Commands"):
        if queries:
            constraint_query = next((q['query'] for q in queries if q['type'] == 'constraint'), None)
            if constraint_query:
                st.code(f"Constraint Query:\n{constraint_query}", language="cypher")

            node_query = next((q for q in queries if q['type'] == 'nodes'), None)
            if node_query:
                st.code(f"Node Ingest Query:\n{node_query['query']}", language="cypher")


def render_results_step():
    """Step 5: Show final L0 results.

    L0 = datum (entity-attribute-value triplet)
    Results vary based on data type:
    - Numeric: single number (sum, mean, etc.)
    - Categorical: string (mode) or dict (distribution)
    - Text: single number (count, length, etc.)
    """
    st.success("🎉 **Descent Complete!** Your data has been transformed from chaos to clarity.")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📁 Sources (L4)", len(st.session_state.raw_data) if st.session_state.raw_data else 0)

    with col2:
        if 'l3' in st.session_state.datasets:
            G = st.session_state.datasets['l3'].get_data()
            st.metric("🕸️ Graph (L3)", f"{G.number_of_nodes()} nodes")

    with col3:
        if 'l2' in st.session_state.datasets:
            total = sum(len(l2.get_data()) for l2 in st.session_state.datasets['l2'].values())
            st.metric("📋 Categorized (L2)", total)

    with col4:
        if 'l0' in st.session_state.datasets:
            n_datums = len(st.session_state.datasets['l0'])
            st.metric("🎯 Datums (L0)", n_datums)

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Metrics", "📦 Data Model", "🔗 Workflow", "📥 Export", "🗄️ Neo4j"])

    with tab1:
        if 'l0' in st.session_state.datasets:
            st.markdown("### 🎯 Atomic Datums (L0)")
            st.caption("Each datum is a triplet: (entity, attribute, value)")

            # Get L0 configs if available
            l0_configs = st.session_state.answers.get('l0_configs', {})

            # Separate by type for appropriate display
            numeric_datums = {}
            categorical_datums = {}
            distribution_datums = {}

            for domain, l0_ds in st.session_state.datasets['l0'].items():
                value = l0_ds.get_data()
                config = l0_configs.get(domain, {})
                data_type = config.get('type', 'unknown')
                aggregation = config.get('aggregation', 'unknown')

                if isinstance(value, dict):
                    distribution_datums[domain] = {'value': value, 'aggregation': aggregation}
                elif isinstance(value, (int, float)):
                    numeric_datums[domain] = {'value': value, 'aggregation': aggregation, 'type': data_type}
                else:
                    categorical_datums[domain] = {'value': value, 'aggregation': aggregation}

            # Display numeric datums as metrics + chart
            if numeric_datums:
                st.markdown("#### 🔢 Numeric Datums")
                cols = st.columns(len(numeric_datums))
                for col, (domain, info) in zip(cols, numeric_datums.items()):
                    with col:
                        st.metric(
                            label=domain,
                            value=info['value'] if isinstance(info['value'], int) else f"{info['value']:.2f}",
                            help=f"Aggregation: {info['aggregation']}"
                        )

                # Bar chart for numeric values
                if len(numeric_datums) > 1:
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots(figsize=(8, 4))
                    domains = list(numeric_datums.keys())
                    values = [info['value'] for info in numeric_datums.values()]
                    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6'][:len(domains)]
                    bars = ax.bar(domains, values, color=colors)
                    ax.set_ylabel('Value')
                    ax.set_title('Numeric Datums by Domain')

                    for bar, val in zip(bars, values):
                        label = str(int(val)) if isinstance(val, int) else f"{val:.2f}"
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                                label, ha='center', fontweight='bold')
                    st.pyplot(fig)

            # Display categorical datums (mode values)
            if categorical_datums:
                st.markdown("#### 🏷️ Categorical Datums")
                for domain, info in categorical_datums.items():
                    st.info(f"**{domain}** ({info['aggregation']}): `{info['value']}`")

            # Display distribution datums as charts
            if distribution_datums:
                st.markdown("#### 📊 Distribution Datums")
                for domain, info in distribution_datums.items():
                    st.markdown(f"**{domain}** (value distribution)")
                    dist = info['value']
                    chart_data = pd.DataFrame({
                        'Category': list(dist.keys()),
                        'Count': list(dist.values())
                    })
                    st.bar_chart(chart_data.set_index('Category'))

        else:
            st.info("Complete the L1→L0 step to see your atomic metrics.")

    with tab2:
        if st.session_state.data_model:
            st.markdown("### Neo4j Data Model Schema")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Nodes:**")
                for node in st.session_state.data_model.nodes:
                    st.code(f"(:{node.label} {{{node.key_property}: STRING}})")

            with col2:
                st.markdown("**Relationships:**")
                for rel in st.session_state.data_model.relationships:
                    st.code(f"(:{rel.start_node_label})-[:{rel.type}]->(:{rel.end_node_label})")

    with tab3:
        st.markdown("### Your Q&A Workflow")
        for key, value in st.session_state.answers.items():
            st.markdown(f"- **{key.title()}**: `{value}`")

    with tab4:
        st.markdown("### Export All Complexity Levels")
        st.caption("Download your data at each stage of the descent")

        # L4: Raw Data
        st.markdown("#### 📁 L4 - Raw Data (Unlinkable Tables)")
        if st.session_state.raw_data:
            l4_cols = st.columns(len(st.session_state.raw_data))
            for col, (filename, df) in zip(l4_cols, st.session_state.raw_data.items()):
                with col:
                    st.download_button(
                        f"📥 {filename}",
                        data=df.to_csv(index=False),
                        file_name=filename,
                        mime="text/csv",
                        key=f"l4_{filename}"
                    )
        else:
            st.info("No L4 data available")

        st.divider()

        # L3: Knowledge Graph
        st.markdown("#### 🕸️ L3 - Knowledge Graph")
        if 'l3' in st.session_state.datasets:
            col1, col2 = st.columns(2)
            with col1:
                # Export as node/edge JSON
                G = st.session_state.datasets['l3'].get_data()
                graph_json = {
                    'nodes': [{'id': n, **G.nodes[n]} for n in G.nodes()],
                    'edges': [{'source': u, 'target': v, **G.edges[u, v]} for u, v in G.edges()]
                }
                st.download_button(
                    "📥 Graph (JSON)",
                    data=json.dumps(graph_json, indent=2, default=str),
                    file_name="l3_knowledge_graph.json",
                    mime="application/json",
                    key="l3_json"
                )
            with col2:
                if st.session_state.data_model:
                    model_json = st.session_state.data_model.to_json()
                    st.download_button(
                        "📥 Data Model (JSON)",
                        data=json.dumps(model_json, indent=2),
                        file_name="l3_data_model.json",
                        mime="application/json",
                        key="l3_model"
                    )
        else:
            st.info("No L3 data available")

        st.divider()

        # L2: Domain Tables
        st.markdown("#### 📋 L2 - Domain Tables")
        if 'l2' in st.session_state.datasets:
            l2_cols = st.columns(min(len(st.session_state.datasets['l2']), 4))
            for i, (domain, l2_ds) in enumerate(st.session_state.datasets['l2'].items()):
                with l2_cols[i % len(l2_cols)]:
                    df = l2_ds.get_data()
                    st.download_button(
                        f"📥 {domain} ({len(df)} rows)",
                        data=df.to_csv(index=False),
                        file_name=f"l2_{domain}.csv",
                        mime="text/csv",
                        key=f"l2_{domain}"
                    )
        else:
            st.info("No L2 data available")

        st.divider()

        # L1: Feature Vectors
        st.markdown("#### 📊 L1 - Feature Vectors")
        if 'l1' in st.session_state.datasets:
            l1_cols = st.columns(min(len(st.session_state.datasets['l1']), 4))
            for i, (domain, l1_ds) in enumerate(st.session_state.datasets['l1'].items()):
                with l1_cols[i % len(l1_cols)]:
                    series = l1_ds.get_data()
                    df = series.to_frame(name='value')
                    st.download_button(
                        f"📥 {domain} ({len(series)} values)",
                        data=df.to_csv(index=False),
                        file_name=f"l1_{domain}.csv",
                        mime="text/csv",
                        key=f"l1_{domain}"
                    )
        else:
            st.info("No L1 data available")

        st.divider()

        # L0: Atomic Datums
        st.markdown("#### 🎯 L0 - Atomic Datums")
        if 'l0' in st.session_state.datasets:
            l0_export = {}
            for domain, l0_ds in st.session_state.datasets['l0'].items():
                value = l0_ds.get_data()
                config = st.session_state.answers.get('l0_configs', {}).get(domain, {})
                l0_export[domain] = {
                    'value': value,
                    'type': config.get('type', 'unknown'),
                    'aggregation': config.get('aggregation', 'unknown'),
                    'description': l0_ds.description
                }
            st.download_button(
                "📥 All Datums (JSON)",
                data=json.dumps(l0_export, indent=2, default=str),
                file_name="l0_datums.json",
                mime="application/json",
                key="l0_json"
            )
        else:
            st.info("No L0 data available")

        st.divider()

        # Workflow Config
        st.markdown("#### ⚙️ Workflow Configuration")
        if st.session_state.answers:
            st.download_button(
                "📥 Full Workflow Config (JSON)",
                data=json.dumps(st.session_state.answers, indent=2, default=str),
                file_name="workflow_config.json",
                mime="application/json",
                key="workflow_config"
            )

    with tab5:
        render_neo4j_export()


# ============================================================================
# NAVIGATION EXPLORER (User Story 5)
# ============================================================================

def render_navigation_explorer():
    """
    Render the free navigation explorer mode.

    This implements User Story 5: Navigate Dataset Hierarchy Step-by-Step
    - Entry point is always L4
    - Users can move UP or DOWN one level at a time (vertical only, no horizontal)
    - Cannot return to L4 once left (L4 is entry-only)
    - Each level transition uses the same features as the guided workflow
    - Can exit and resume at any point
    """
    st.markdown("### 🧭 Free Navigation Mode")
    st.markdown("""
    Navigate through abstraction levels freely. Each transition uses the same
    LLM-powered features as the guided workflow.

    **Rules**: Move ⬇️ down or ⬆️ up one level at a time. Cannot return to L4.
    """)

    # Check if we have raw data to create a navigation session
    if not st.session_state.get('raw_data'):
        st.warning("⚠️ Upload data first to enable navigation. Go to the guided workflow and upload your CSV files.")
        if st.button("← Back to Guided Workflow"):
            st.session_state['nav_mode'] = False
            st.rerun()
        return

    # Initialize or get navigation session
    nav_session = st.session_state.get('nav_session')

    if nav_session is None:
        st.info("🚀 Start a new navigation session from your L4 data (raw sources)")

        if st.button("Start Navigation Session", type="primary"):
            try:
                # Create L4 dataset from raw data
                l4_dataset = Level4Dataset(st.session_state['raw_data'])
                nav_session = NavigationSession(l4_dataset)
                st.session_state['nav_session'] = nav_session
                st.success("✅ Navigation session started at L4")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start navigation: {str(e)}")
        return

    # Display current position
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        level = nav_session.current_level
        level_names = {
            ComplexityLevel.LEVEL_0: ("L0: Datum", "🎯", "Single atomic value"),
            ComplexityLevel.LEVEL_1: ("L1: Vector", "📊", "One-dimensional data"),
            ComplexityLevel.LEVEL_2: ("L2: Table", "📋", "Two-dimensional data"),
            ComplexityLevel.LEVEL_3: ("L3: Linkable", "🔗", "Multi-level with relationships"),
            ComplexityLevel.LEVEL_4: ("L4: Unlinkable", "📁", "Raw unconnected sources")
        }
        name, emoji, desc = level_names.get(level, ("Unknown", "❓", ""))
        st.metric(
            label=f"{emoji} Current Level",
            value=name,
            delta=desc
        )

    with col2:
        st.metric(
            label="🔢 Steps Taken",
            value=len(nav_session.get_history())
        )

    with col3:
        state_display = {
            NavigationState.ENTRY: ("Entry", "🚪"),
            NavigationState.EXPLORING: ("Exploring", "🔍"),
            NavigationState.EXITED: ("Exited", "🚪")
        }
        state_name, state_emoji = state_display.get(nav_session.state, ("Unknown", "❓"))
        st.metric(
            label=f"{state_emoji} State",
            value=state_name
        )

    st.divider()

    # Available moves (vertical only - no horizontal)
    moves = nav_session.get_available_moves()

    # Show navigation options in a 2-column layout
    st.markdown("#### 🧭 Navigation Options")

    nav_cols = st.columns(2)

    with nav_cols[0]:
        st.markdown("##### ⬇️ Descend (Reduce Complexity)")
        if nav_session.can_descend():
            for move in moves.get("descend", []):
                if isinstance(move, dict):
                    st.info(f"**{move.get('target', '?')}** - {move.get('description', '')}")
                else:
                    st.caption(f"• {move}")
        else:
            st.success("You've reached L0 (Datum) - the ground truth level.")

    with nav_cols[1]:
        st.markdown("##### ⬆️ Ascend (Increase Complexity)")
        if nav_session.can_ascend():
            for move in moves.get("ascend", []):
                if isinstance(move, dict):
                    st.info(f"**{move.get('target', '?')}** - {move.get('description', '')}")
                else:
                    st.caption(f"• {move}")
        elif level == ComplexityLevel.LEVEL_3:
            st.warning("L4 is entry-only. Cannot return to L4.")
        elif level == ComplexityLevel.LEVEL_4:
            st.caption("Already at entry point (L4).")
        else:
            st.caption("Ascent not available at this level.")

    st.divider()

    # =========================================================================
    # STEP CONTENT: Render the appropriate step features based on current level
    # =========================================================================
    st.markdown("### 📋 Current Step Features")

    current_step = nav_session.get_current_step_id()

    if level == ComplexityLevel.LEVEL_4:
        # At L4 (entry point) - show entities step for descending to L3
        st.markdown("**L4 → L3 Transition: Define Entities and Build Knowledge Graph**")
        render_entities_step()

        # Navigation control: Descend to L3 after generating Cypher/data model
        st.divider()
        st.markdown("#### 🧭 Navigate to Next Level")
        # Check if Cypher has been generated (indicates graph is ready)
        if st.session_state.get('generated_cypher') or st.session_state.get('neo4j_queries'):
            st.success("Knowledge graph defined! You can now descend to L3.")
            if st.button("⬇️ Descend to L3 (Linkable)", key="nav_descend_to_l3", type="primary"):
                try:
                    # Create a simple graph from the data model for navigation
                    data_model = st.session_state.get('data_model')
                    nav_session.descend(builder_func=lambda x: data_model)
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))
        else:
            st.info("Generate the Cypher script above (using 'Generate Complete Cypher') to enable descent to L3.")

    elif level == ComplexityLevel.LEVEL_3:
        # At L3 - show domains step for descending to L2
        st.markdown("**L3 → L2 Transition: Query Graph for Domain-Specific Tables**")
        render_domains_step()

        # Navigation control: Always allow descent from L3
        st.divider()
        st.markdown("#### 🧭 Navigate to Next Level")
        st.success("You can descend to L2 to work with domain-specific tables.")
        if st.button("⬇️ Descend to L2 (Table)", key="nav_descend_to_l2", type="primary"):
            try:
                # Use raw_data as the table source for now
                nav_session.descend(query_func=lambda x: st.session_state.get('raw_data', {}))
                st.rerun()
            except NavigationError as e:
                st.error(str(e))

    elif level == ComplexityLevel.LEVEL_2:
        # At L2 - show features step for descending to L1
        st.markdown("**L2 → L1 Transition: Extract Features from Tables**")
        render_features_step()

        # Navigation control: Allow descent and ascent from L2
        st.divider()
        st.markdown("#### 🧭 Navigate to Next Level")

        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            st.info("Descend to extract feature vectors")
            if st.button("⬇️ Descend to L1 (Vector)", key="nav_descend_to_l1", type="primary"):
                try:
                    nav_session.descend(column="feature")
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

        with col_nav2:
            st.info("Ascend back to knowledge graph by adding analytic dimensions")

        # L2→L3 Ascent UI with dimension selection
        st.markdown("---")
        st.markdown("#### ⬆️ Ascent Options (L2 → L3)")
        st.info("Add analytic dimensions to enable hierarchical grouping and linkage.")

        try:
            from intuitiveness.ascent import DimensionRegistry, find_duplicates
            dim_registry = DimensionRegistry.get_instance()

            # Get available dimensions for L2→L3
            available_dims = dim_registry.list_for_transition(
                ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3
            )

            if available_dims:
                st.markdown("##### Select Analytic Dimensions")

                # Show dimension options with checkboxes
                dim_options = {d.name: d.description for d in available_dims}
                selected_dims = []

                for dim_name, dim_desc in dim_options.items():
                    if st.checkbox(f"**{dim_name}**: {dim_desc}", key=f"l2_dim_{dim_name}", value=True):
                        selected_dims.append(dim_name)

                if not selected_dims:
                    st.warning("Select at least one dimension to ascend.")

                # Show current table structure
                current_dataset = nav_session.current_dataset
                if hasattr(current_dataset, 'get_data'):
                    current_data = current_dataset.get_data()
                    with st.expander("📊 Current Table Structure"):
                        st.write(f"**Columns:** {list(current_data.columns)}")
                        st.write(f"**Rows:** {len(current_data)}")

                # Preview section with duplicate detection
                if selected_dims and st.checkbox("Preview with duplicate detection", key="l2_preview"):
                    try:
                        from intuitiveness.redesign import Redesigner
                        preview_result = Redesigner.increase_complexity(
                            current_dataset,
                            ComplexityLevel.LEVEL_3,
                            dimensions=selected_dims
                        )
                        preview_data = preview_result.get_data()

                        st.write("**Preview (first 10 rows):**")
                        if len(preview_data) > 10:
                            st.dataframe(preview_data.head(10))
                            st.caption(f"...and {len(preview_data) - 10} more rows")
                        else:
                            st.dataframe(preview_data)

                        # Check for potential duplicates
                        dup_check = find_duplicates(preview_data, selected_dims)
                        dup_count = dup_check['is_potential_duplicate'].sum() if 'is_potential_duplicate' in dup_check.columns else 0
                        if dup_count > 0:
                            st.warning(f"⚠️ Found {dup_count} items with identical dimension values (potential duplicates)")
                        else:
                            st.success("✅ No duplicate dimension combinations detected")

                    except Exception as e:
                        st.error(f"Preview failed: {str(e)}")

                # Ascent button
                if selected_dims and st.button("⬆️ Ascend to L3 (Linkable)", key="nav_ascend_to_l3", type="primary"):
                    try:
                        nav_session.ascend(dimensions=selected_dims)
                        st.success("✅ Ascended to L3!")
                        st.rerun()
                    except NavigationError as e:
                        st.error(str(e))
            else:
                st.warning("No dimensions available for L2→L3 ascent.")
                if st.button("⬆️ Ascend to L3 (Linkable)", key="nav_ascend_to_l3_fallback"):
                    try:
                        nav_session.ascend()
                        st.rerun()
                    except NavigationError as e:
                        st.error(str(e))

        except ImportError:
            # Fallback if ascent module not available
            if st.button("⬆️ Ascend to L3 (Linkable)", key="nav_ascend_to_l3_basic"):
                try:
                    nav_session.ascend()
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    elif level == ComplexityLevel.LEVEL_1:
        # At L1 - show metric step for descending to L0
        st.markdown("**L1 → L0 Transition: Compute Atomic Metrics**")
        render_metric_step()

        # Navigation control: Allow descent and ascent from L1
        st.divider()
        st.markdown("#### 🧭 Navigate to Next Level")

        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            st.info("Descend to compute final metric")
            if st.button("⬇️ Descend to L0 (Datum)", key="nav_descend_to_l0", type="primary"):
                try:
                    nav_session.descend(aggregation="sum")
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

        with col_nav2:
            st.info("Ascend back to tables by adding dimensions")

        # L1→L2 Ascent UI with dimension selection
        st.markdown("---")
        st.markdown("#### ⬆️ Ascent Options (L1 → L2)")
        st.info("Add categorical dimensions to transform the vector into a table.")

        try:
            from intuitiveness.ascent import DimensionRegistry, suggest_dimensions
            dim_registry = DimensionRegistry.get_instance()

            # Get available dimensions for L1→L2
            available_dims = dim_registry.list_for_transition(
                ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2
            )

            if available_dims:
                st.markdown("##### Select Dimensions to Add")

                # Show dimension options with checkboxes
                dim_options = {d.name: d.description for d in available_dims}
                selected_dims = []

                for dim_name, dim_desc in dim_options.items():
                    if st.checkbox(f"**{dim_name}**: {dim_desc}", key=f"l1_dim_{dim_name}", value=True):
                        selected_dims.append(dim_name)

                if not selected_dims:
                    st.warning("Select at least one dimension to ascend.")

                # Suggest dimensions based on data patterns
                current_dataset = nav_session.current_dataset
                if hasattr(current_dataset, 'get_data'):
                    with st.expander("💡 Dimension Suggestions"):
                        try:
                            suggestions = suggest_dimensions(current_dataset.get_data())
                            if suggestions:
                                for sug in suggestions:
                                    confidence_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(sug['confidence'], "⚪")
                                    st.write(f"{confidence_color} **{sug['dimension']}** ({sug['confidence']}): {sug['reason']}")
                            else:
                                st.write("No specific suggestions - using defaults.")
                        except Exception as e:
                            st.write(f"Could not analyze data: {str(e)}")

                # Preview section
                if selected_dims and st.checkbox("Preview table result", key="l1_preview"):
                    try:
                        from intuitiveness.redesign import Redesigner
                        preview_result = Redesigner.increase_complexity(
                            current_dataset,
                            ComplexityLevel.LEVEL_2,
                            dimensions=selected_dims
                        )
                        st.write("**Preview (first 10 rows):**")
                        preview_data = preview_result.get_data()
                        if len(preview_data) > 10:
                            st.dataframe(preview_data.head(10))
                            st.caption(f"...and {len(preview_data) - 10} more rows")
                        else:
                            st.dataframe(preview_data)
                    except Exception as e:
                        st.error(f"Preview failed: {str(e)}")

                # Ascent button
                if selected_dims and st.button("⬆️ Ascend to L2 (Table)", key="nav_ascend_to_l2", type="primary"):
                    try:
                        nav_session.ascend(dimensions=selected_dims)
                        st.success("✅ Ascended to L2!")
                        st.rerun()
                    except NavigationError as e:
                        st.error(str(e))
            else:
                st.warning("No dimensions available for L1→L2 ascent.")
                if st.button("⬆️ Ascend to L2 (Table)", key="nav_ascend_to_l2_fallback"):
                    try:
                        nav_session.ascend()
                        st.rerun()
                    except NavigationError as e:
                        st.error(str(e))

        except ImportError:
            # Fallback if ascent module not available
            if st.button("⬆️ Ascend to L2 (Table)", key="nav_ascend_to_l2_basic"):
                try:
                    nav_session.ascend()
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    elif level == ComplexityLevel.LEVEL_0:
        # At L0 - ground truth reached, show result and ascent options
        st.markdown("**L0 (Datum): Ground Truth Reached**")

        # Display the computed metric if available
        current_dataset = nav_session.current_dataset
        metric_value = current_dataset.get_data() if hasattr(current_dataset, 'get_data') else st.session_state.get('computed_metric')

        if metric_value is not None:
            st.metric(label="Computed Value", value=str(metric_value))

            # Show aggregation method if available
            if hasattr(current_dataset, 'aggregation_method') and current_dataset.aggregation_method:
                st.caption(f"Aggregation: {current_dataset.aggregation_method}")
        else:
            data = nav_session.current_node
            st.metric(label="Datum Value", value=str(data))

        st.markdown("---")
        st.markdown("#### 🧭 Ascent Options (L0 → L1)")
        st.info("You've reached the ground truth (L0). You can ascend back up by enriching the datum into a vector.")

        # Import ascent functionality
        try:
            from intuitiveness.ascent import EnrichmentRegistry
            registry = EnrichmentRegistry.get_instance()

            # Get available enrichment functions for L0→L1
            enrichment_funcs = registry.list_for_transition(
                ComplexityLevel.LEVEL_0, ComplexityLevel.LEVEL_1
            )

            if enrichment_funcs:
                st.markdown("##### Select Enrichment Function")

                # Show available enrichment options
                func_options = {f.name: f.description for f in enrichment_funcs}
                selected_func = st.selectbox(
                    "Enrichment Function",
                    options=list(func_options.keys()),
                    format_func=lambda x: f"{x}: {func_options[x]}",
                    key="l0_enrichment_func"
                )

                # Check if parent data is available
                has_parent = hasattr(current_dataset, 'has_parent') and current_dataset.has_parent

                if not has_parent:
                    st.warning("⚠️ No parent data available. This L0 was not created by descent from L1. Some enrichment functions may not work.")

                # Preview section
                if st.checkbox("Preview enrichment result", key="l0_preview"):
                    try:
                        from intuitiveness.redesign import Redesigner
                        preview_result = Redesigner.increase_complexity(
                            current_dataset,
                            ComplexityLevel.LEVEL_1,
                            enrichment_func=selected_func
                        )
                        st.write("**Preview (first 10 items):**")
                        preview_data = preview_result.get_data()
                        if len(preview_data) > 10:
                            st.write(preview_data.head(10))
                            st.caption(f"...and {len(preview_data) - 10} more items")
                        else:
                            st.write(preview_data)
                    except Exception as e:
                        st.error(f"Preview failed: {str(e)}")

                # Show size warning for large parent data
                parent_size = 0
                if has_parent and hasattr(current_dataset, 'get_parent_data'):
                    parent_data = current_dataset.get_parent_data()
                    if parent_data is not None:
                        parent_size = len(parent_data)
                        if parent_size > 1000:
                            st.info(f"ℹ️ Parent data has {parent_size:,} items. Enrichment may take a moment.")

                # Ascent button with progress indicator
                if st.button("⬆️ Ascend to L1 (Vector)", key="nav_ascend_l0", type="primary"):
                    try:
                        if parent_size > 1000:
                            with st.spinner(f"Enriching {parent_size:,} items..."):
                                nav_session.ascend(enrichment_func=selected_func)
                        else:
                            nav_session.ascend(enrichment_func=selected_func)
                        st.success("✅ Ascended to L1!")
                        st.rerun()
                    except NavigationError as e:
                        st.error(str(e))
            else:
                st.warning("No enrichment functions available for L0→L1 ascent.")

        except ImportError:
            # Fallback if ascent module not available
            st.warning("Ascent functionality not fully configured.")
            if st.button("⬆️ Ascend to L1 (Vector)", key="nav_ascend_l0_fallback", type="primary"):
                try:
                    nav_session.ascend()
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    st.divider()

    # Navigation history (data preview is already shown by step renderers above)
    with st.expander("📜 Navigation History", expanded=st.session_state.get('nav_history_visible', False)):
        history = nav_session.get_history()
        if history:
            for i, step in enumerate(history):
                action_icons = {
                    "entry": "🚪",
                    "descend": "⬇️",
                    "ascend": "⬆️",
                    "exit": "🚪",
                    "resume": "▶️"
                }
                icon = action_icons.get(step.get('action', ''), "•")
                action = step.get('action', 'unknown')
                level = step.get('level', '?')
                level_name = step.get('level_name', '')
                node_id = step.get('node_id', '')

                # Enhanced display for ascent operations
                if action == 'ascend' and node_id:
                    # Parse node_id to show enrichment/dimension info
                    details = ""
                    if 'enrichment_func' in node_id:
                        func_match = node_id.split('enrichment_func=')
                        if len(func_match) > 1:
                            func_name = func_match[1].split('&')[0].split(')')[0]
                            details = f" (enrichment: {func_name})"
                    elif 'dimensions' in node_id:
                        details = " (with dimensions)"

                    st.markdown(f"{i+1}. {icon} **{action}** → L{level} ({level_name}){details}")
                else:
                    st.markdown(f"{i+1}. {icon} **{action}** → L{level} ({level_name})")
        else:
            st.caption("No history yet")

    # Session controls
    st.divider()
    ctrl_cols = st.columns(4)

    with ctrl_cols[0]:
        if st.button("💾 Save Session"):
            try:
                save_path = f"sessions/nav_session_{nav_session.session_id[:8]}.pkl"
                nav_session.save(save_path)
                st.success(f"Saved to {save_path}")
            except Exception as e:
                st.error(f"Save failed: {e}")

    with ctrl_cols[1]:
        if st.button("🚪 Exit Session"):
            nav_session.exit()
            st.info("Session exited. You can resume later.")

    with ctrl_cols[2]:
        if st.button("🔄 New Session"):
            st.session_state['nav_session'] = None
            st.rerun()

    with ctrl_cols[3]:
        if st.button("← Back to Workflow"):
            st.session_state['nav_mode'] = False
            st.rerun()


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Data Redesign Method",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    print(f"\n{'#'*60}")
    print(f"# DATA REDESIGN METHOD - Streamlit App")
    print(f"# Ollama Model: {OLLAMA_MODEL}")
    print(f"{'#'*60}\n")

    init_session_state()
    render_sidebar()

    # Check if in navigation mode
    if st.session_state.get('nav_mode', False):
        # Free navigation explorer mode (User Story 5)
        st.title("🧭 Data Navigation Explorer")
        st.markdown("Explore your data hierarchy freely through the abstraction levels.")
        render_navigation_explorer()
    else:
        # Guided workflow mode (default)
        st.title("🔄 Interactive Data Redesign Method")
        st.markdown("Transform your data from **L4 (chaos)** to **L0 (clarity)** through guided questions.")

        render_step_header()

        # Render current step
        step_id = DESCENT_STEPS[st.session_state.current_step]['id']
        print(f"\n[STEP] Current step: {step_id} (step {st.session_state.current_step + 1}/{len(DESCENT_STEPS)})")

        if step_id == "upload":
            render_upload_step()
        elif step_id == "entities":
            render_entities_step()
        elif step_id == "domains":
            render_domains_step()
        elif step_id == "features":
            render_features_step()
        elif step_id == "metric":
            render_metric_step()
        elif step_id == "results":
            render_results_step()

        # Navigation
        st.divider()
        render_navigation()


if __name__ == "__main__":
    main()

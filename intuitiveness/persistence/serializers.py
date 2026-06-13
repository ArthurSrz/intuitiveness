"""
Serializers for session persistence.

Handles serialization/deserialization of DataFrames and Graphs
for browser localStorage storage.
"""

import base64
import json
import zlib
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import networkx as nx


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            v = float(obj)
            return None if (v != v) else v  # NaN → null
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, float) and obj != obj:
            return None
        return super().default(obj)


def serialize_dataframe(df: pd.DataFrame) -> str:
    """
    Serialize a pandas DataFrame to compressed base64 string.

    Args:
        df: DataFrame to serialize

    Returns:
        Base64-encoded compressed JSON string
    """
    json_str = df.to_json(orient='split', date_format='iso')
    compressed = zlib.compress(json_str.encode('utf-8'))
    base64_str = base64.b64encode(compressed).decode('ascii')
    return base64_str


def deserialize_dataframe(data: str) -> pd.DataFrame:
    """
    Deserialize a compressed base64 string to DataFrame.

    Args:
        data: Base64-encoded compressed JSON string

    Returns:
        Reconstructed DataFrame

    Raises:
        ValueError: If data is invalid or corrupted
    """
    try:
        compressed = base64.b64decode(data)
        json_str = zlib.decompress(compressed).decode('utf-8')
        df = pd.read_json(StringIO(json_str), orient='split')
        return df
    except Exception as e:
        raise ValueError(f"Failed to deserialize DataFrame: {e}")


def serialize_graph(G: nx.Graph) -> str:
    """
    Serialize a networkx Graph to compressed base64 string.

    Args:
        G: Graph to serialize

    Returns:
        Base64-encoded compressed JSON string
    """
    data = nx.node_link_data(G)
    # Replace NaN with None in node attributes (not IDs) for JSON safety
    import math
    for node in data.get("nodes", []):
        for k, v in list(node.items()):
            if k == "id":
                continue
            if isinstance(v, float) and math.isnan(v):
                node[k] = None
    json_str = json.dumps(data, cls=NumpyEncoder)
    compressed = zlib.compress(json_str.encode('utf-8'))
    base64_str = base64.b64encode(compressed).decode('ascii')
    return base64_str


def deserialize_graph(data: str) -> nx.Graph:
    """
    Deserialize a compressed base64 string to Graph.

    Args:
        data: Base64-encoded compressed JSON string

    Returns:
        Reconstructed Graph

    Raises:
        ValueError: If data is invalid or corrupted
    """
    try:
        compressed = base64.b64decode(data)
        json_str = zlib.decompress(compressed).decode('utf-8')
        graph_data = json.loads(json_str)
        G = nx.node_link_graph(graph_data)
        return G
    except Exception as e:
        raise ValueError(f"Failed to deserialize Graph: {e}")


def serialize_value(value: Any) -> str:
    """
    Serialize a generic value to compressed base64 string.

    Args:
        value: Any JSON-serializable value (including NumPy types)

    Returns:
        Base64-encoded compressed JSON string
    """
    json_str = json.dumps(value, cls=NumpyEncoder)
    compressed = zlib.compress(json_str.encode('utf-8'))
    base64_str = base64.b64encode(compressed).decode('ascii')
    return base64_str


def deserialize_value(data: str) -> Any:
    """
    Deserialize a compressed base64 string to generic value.

    Args:
        data: Base64-encoded compressed JSON string

    Returns:
        Reconstructed value

    Raises:
        ValueError: If data is invalid or corrupted
    """
    try:
        compressed = base64.b64decode(data)
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Failed to deserialize value: {e}")


def get_compressed_size(data: str) -> int:
    """
    Get the size in bytes of a base64-encoded string.

    Args:
        data: Base64-encoded string

    Returns:
        Size in bytes
    """
    return len(data.encode('ascii'))

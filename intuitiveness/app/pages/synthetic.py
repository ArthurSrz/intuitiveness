"""
Synthetic Data Generation Page

Renders the UI for generating synthetic data using TabPFN (with Gaussian copula fallback).
Uses the existing quality/synthetic_generator.py backend.
"""

import streamlit as st
import pandas as pd
from typing import Optional

from intuitiveness.ui import t, render_page_header


def _get_source_dataframe() -> Optional[pd.DataFrame]:
    """
    Find the best available DataFrame from session state.

    Priority: quality_df > l3 dataset > l2 dataset > raw_data.
    Returns None if no data is available.
    """
    # Source 1: quality_df (already bridged from cart/upload/datasets)
    quality_df = st.session_state.get('quality_df')
    if quality_df is not None and isinstance(quality_df, pd.DataFrame) and not quality_df.empty:
        return quality_df

    # Source 2: datasets dict (prefer L3, then L2, then L1)
    datasets = st.session_state.get('datasets', {})
    for level_key in ('l3', 'l3_ascent', 'l2', 'l2_ascent', 'l1', 'l1_ascent'):
        ds = datasets.get(level_key)
        if ds is not None:
            df = ds.get_data() if hasattr(ds, 'get_data') else ds
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df

    # Source 3: raw_data
    raw_data = st.session_state.get('raw_data')
    if raw_data is not None:
        if isinstance(raw_data, pd.DataFrame) and not raw_data.empty:
            return raw_data
        if isinstance(raw_data, dict):
            dataframes = [v for v in raw_data.values() if isinstance(v, pd.DataFrame)]
            if dataframes:
                return dataframes[0]

    return None


def render_synthetic_page():
    """Render the synthetic data generation page."""
    from intuitiveness.quality.synthetic_generator import (
        generate_synthetic,
        check_tabpfn_auth,
        get_synthetic_summary,
    )

    render_page_header(
        title=t('synthetic_data'),
        subtitle=t('synthetic_subtitle'),
    )

    # Auth status check
    is_authed, auth_msg = check_tabpfn_auth()
    if is_authed:
        st.info(f"{t('synthetic_auth_status')}: TabPFN")
    else:
        st.warning(f"{t('synthetic_auth_status')}: {t('synthetic_fallback_info')}")

    st.divider()

    # Source data
    source_df = _get_source_dataframe()

    uploaded = st.file_uploader(
        t('synthetic_upload_or_use'),
        type=['csv'],
        key='synthetic_csv_upload',
    )

    if uploaded is not None:
        try:
            source_df = pd.read_csv(uploaded)
            st.success(f"{t('upload_success', filename=uploaded.name, rows=len(source_df), cols=len(source_df.columns))}")
        except Exception as e:
            st.error(str(e))
            return

    if source_df is None:
        st.warning(t('synthetic_no_data'))
        return

    # Show source data preview
    with st.expander(t('synthetic_source_preview'), expanded=False):
        st.dataframe(source_df.head(10))
        st.caption(f"{len(source_df)} {t('rows_label')}, {len(source_df.columns)} {t('columns_label')}")

    st.divider()

    # Configuration
    st.subheader(t('synthetic_config'))

    col1, col2 = st.columns(2)
    with col1:
        n_samples = st.slider(
            t('synthetic_samples'),
            min_value=10,
            max_value=10000,
            value=min(len(source_df) * 2, 1000),
            step=10,
            key='synthetic_n_samples',
        )
    with col2:
        temperature = st.slider(
            t('synthetic_temperature'),
            min_value=0.1,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key='synthetic_temperature',
            help=t('synthetic_temperature_help'),
        )

    st.divider()

    # Generate button
    if st.button(t('synthetic_generate_button'), type="primary", key='btn_generate_synthetic'):
        with st.spinner(t('synthetic_generating')):
            try:
                synthetic_df, metrics = generate_synthetic(
                    source_df,
                    n_samples=n_samples,
                    temperature=temperature,
                )
                st.session_state['synthetic_result'] = synthetic_df
                st.session_state['synthetic_metrics'] = metrics
            except Exception as e:
                st.error(f"{t('synthetic_error')}: {e}")
                return

    # Display results
    synthetic_df = st.session_state.get('synthetic_result')
    metrics = st.session_state.get('synthetic_metrics')

    if synthetic_df is not None and metrics is not None:
        st.success(t('synthetic_results'))

        # Quality metrics
        st.subheader(t('synthetic_quality_metrics'))
        m1, m2, m3 = st.columns(3)
        with m1:
            corr_pct = (1 - metrics.mean_correlation_error) * 100
            st.metric(t('synthetic_correlation'), f"{corr_pct:.1f}%")
        with m2:
            st.metric(t('synthetic_distribution'), f"{metrics.distribution_similarity * 100:.1f}%")
        with m3:
            st.metric(t('synthetic_time'), f"{metrics.generation_time_seconds:.1f}s")

        st.divider()

        # Preview
        st.subheader(t('synthetic_preview'))
        st.dataframe(synthetic_df.head(20))
        st.caption(f"{len(synthetic_df)} {t('rows_label')}, {len(synthetic_df.columns)} {t('columns_label')}")

        # Download button
        csv_data = synthetic_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=t('synthetic_download'),
            data=csv_data,
            file_name="synthetic_data.csv",
            mime="text/csv",
            key='btn_download_synthetic',
        )

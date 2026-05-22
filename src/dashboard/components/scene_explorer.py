from __future__ import annotations

import streamlit as st

from src.dashboard.data_loaders import get_scene_image_sources
from src.dashboard.overlays import draw_demo_overlays, load_display_image
from src.dashboard.styles import icon


def render(
    scene: dict,
    disaster_type: str,
    predictions: list[dict],
    confidence_pct: float,
    show_overlays: bool,
    overlay_opacity: float,
) -> None:
    """Hero scene explorer matching Stitch HTML layout."""
    pre_url, post_url, pre_path, post_path = get_scene_image_sources(scene)

    if pre_url and post_url:
        toolbar = f"""
        <div class="ds-img-toolbar">
            <span>{icon("zoom_in", size=20)}</span>
            <span>{icon("zoom_out", size=20)}</span>
            <span class="ds-tb-div"></span>
            <span>{icon("visibility", size=20)}</span>
        </div>
        """
        st.markdown(
            f"""
            <div class="ds-scene-card">
                <div class="ds-scene-card-head">
                    <h3>Scene Explorer - {disaster_type}</h3>
                    <span class="ds-confidence">Confidence: {confidence_pct:.0f}%</span>
                </div>
                <div class="ds-scene-images">
                    <div class="ds-scene-img-wrap pre">
                        <img src="{pre_url}" alt="Pre-disaster"/>
                        <span class="ds-img-chip">Pre-disaster</span>
                    </div>
                    <div class="ds-scene-img-wrap post">
                        <img src="{post_url}" alt="Post-disaster"/>
                        <span class="ds-img-chip">Post-disaster (Inference)</span>
                        {toolbar}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if show_overlays:
            st.caption("Damage overlays use demo polygons when viewing remote Stitch preview imagery.")
        return

    pre_img = load_display_image(pre_path, "Pre-disaster")
    post_img = load_display_image(post_path, "Post-disaster")
    if show_overlays:
        post_img = draw_demo_overlays(post_img, predictions, opacity=overlay_opacity)

    st.markdown(
        f"""
        <div class="ds-scene-card-head" style="background:#171c21;border:1px solid #2d3a4f;
        border-radius:0.5rem 0.5rem 0 0;padding:0.5rem 0.75rem;display:flex;
        justify-content:space-between;margin-bottom:0">
            <h3 style="margin:0;font-size:1rem;color:#dee3ea">Scene Explorer - {disaster_type}</h3>
            <span class="ds-confidence">Confidence: {confidence_pct:.0f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2, gap="small")
    with cols[0]:
        st.markdown('<span class="ds-img-chip" style="position:relative;display:inline-block;margin-bottom:0.5rem">Pre-disaster</span>', unsafe_allow_html=True)
        st.image(pre_img, use_container_width=True)
    with cols[1]:
        st.markdown('<span class="ds-img-chip" style="position:relative;display:inline-block;margin-bottom:0.5rem">Post-disaster (Inference)</span>', unsafe_allow_html=True)
        st.image(post_img, use_container_width=True)

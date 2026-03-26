"""Renderer helpers for ontology generation status panel."""

from __future__ import annotations

import streamlit as st


def render_generation_status(result: dict) -> None:
    if result.get("validation_passed"):
        st.success("Ontology generated and validated successfully.")
    else:
        st.error("Ontology generated but validation failed. Fix issues and regenerate.")

    issues = result.get("validation_issues", [])
    if issues:
        st.subheader("Validation Issues")
        for issue in issues:
            code = issue.get("code", "unknown")
            path = issue.get("path", "-")
            message = issue.get("message", "-")
            st.write(f"- [{code}] {path}: {message}")

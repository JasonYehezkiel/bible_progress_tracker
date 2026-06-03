import streamlit as st

@st.cache_resource(show_spinner='Loading pipeline...')
def get_pipeline():
    from pipelines import BibleProgressPipeline
    return BibleProgressPipeline()
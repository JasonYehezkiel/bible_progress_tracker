import pandas as pd
import warnings
import sys
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from config.settings import PROCESSED_DIR
from pipelines import BibleProgressPipeline
from bible_data import load_bible_data


# =====================================================
# INIT PIPELINE
# =====================================================
bible_books = load_bible_data()

bible_pipeline = BibleProgressPipeline(
    bible_books=bible_books,
    saved_path=PROCESSED_DIR
)

# =====================================================
# PAGE
# =====================================================
st.set_page_config(layout="wide")

st.title("Admin Dashboard")
st.caption("Sistem Rekapitulasi Progres Pembacaan Alkitab")

# =====================================================
# UPLOAD
# =====================================================
uploaded_file = st.file_uploader(
    "Upload CSV",
    type=["csv"]
)

# =====================================================
# MAIN
# =====================================================
if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    st.write("### Preview Data")
    st.dataframe(df.head())

    if st.button("🚀 Run Pipeline"):

        # ============================================
        # STEP 1: CLASSIFICATION
        # ============================================
        df_result = bible_pipeline.classify_dataframe(df)

        # hanya progress
        progress_df = df_result[
            df_result["prediction_label"] == "progress"
        ].copy()

        if not progress_df.empty:

            progress_df["timestamp"] = pd.to_datetime(
                progress_df["timestamp"],
                errors="coerce"
            )

            progress_df["date"] = (
                progress_df["timestamp"].dt.date
            )

            # ========================================
            # STEP 2: EXTRACTION
            # ========================================
            progress_df["ner_references"] = (
                progress_df["message"].apply(
                    bible_pipeline.extractor.extract
                )
            )

            progress_df["ner_ref_count"] = (
                progress_df["ner_references"]
                .apply(len)
            )

        # ============================================
        # METRICS
        # ============================================
        total_messages = len(df_result)
        progress_messages = len(progress_df)

        extracted_refs = (
            progress_df["ner_ref_count"].sum()
            if not progress_df.empty else 0
        )

        zero_refs = (
            (progress_df["ner_ref_count"] == 0).sum()
            if not progress_df.empty else 0
        )

        st.success("Pipeline selesai!")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Pesan", total_messages)
        col2.metric("Pesan Progress", progress_messages)
        col3.metric("Referensi Diekstrak", extracted_refs)
        col4.metric("Zero Reference", zero_refs)

        # ============================================
        # CLASSIFICATION RESULT
        # ============================================
        st.write("### Hasil Klasifikasi")

        st.dataframe(
            df_result[
                [
                    "sender",
                    "message",
                    "prediction_label"
                ]
            ]
        )

        # ============================================
        # EXTRACTION RESULT
        # ============================================
        if not progress_df.empty:

            st.write("### Hasil Information Extraction")

            st.dataframe(
                progress_df[
                    [
                        "sender",
                        "message",
                        "ner_ref_count"
                    ]
                ]
            )

        else:
            st.warning(
                "Tidak ada pesan progress terdeteksi."
            )

else:
    st.info("Silakan upload file CSV.")

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
[data-testid="stMetric"] {
    background-color: #f5f5f5;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)
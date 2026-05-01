import pandas as pd
import random
import warnings
import sys
from pathlib import Path
from sklearn.metrics import accuracy_score
warnings.filterwarnings('ignore')
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from config.settings import PROCESSED_DIR
from preprocessing import WhatsAppParser 
import streamlit as st
import joblib
from pathlib import Path


CLS_DIR = PROCESSED_DIR / "text classification"
MODEL_DIR = CLS_DIR / "model"
MODEL_PATH = MODEL_DIR / "random_forest_model.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)


def classify_dataframe(df, model, vectorizer):
    # pastikan kolom text tidak null
    df['text'] = df['text'].fillna('')

    # transform pakai TF-IDF 
    X = vectorizer.transform(df['text'])

    # prediksi random forest model
    df['prediction'] = model.predict(X)

    # ubah ke label yang readable
    df['label_name'] = df['prediction'].map({
        1: 'progress',
        0: 'non-progress'
    })
    return df

def evaluate_results(df):
    # y_true langsung dari kolom 'label'
    y_true = df['label']

    # y_pred dari kolom 'prediction' (hasil model)
    y_pred = df['prediction']

    # buang baris yang NaN supaya tidak error
    df_clean = df.dropna(subset=['label', 'prediction'])
    y_true = df_clean['label']
    y_pred = df_clean['prediction']

    accuracy = accuracy_score(y_true, y_pred)
    return accuracy



# HEADER
st.set_page_config(layout="wide")
st.title("Admin Dashboard")
st.caption("Sistem Rekapitulasi Progres Pembacaan Alkitab")

# UPLOAD SECTION
st.markdown("#### 📤 Upload WhatsApp Export")
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.write("### Preview Data")
    st.dataframe(df.head())

    if st.button("🚀 Run Classification"):
        df_result = classify_dataframe(df, model, vectorizer)

        st.success("Klasifikasi selesai!")

        # Setelah classify_dataframe menghasilkan df_result
        df_result['prediction_label'] = df_result['prediction'].map({
            1: 'progress',
            0: 'non-progress'
        })

        total = len(df_result)
        total_progress = (df_result['prediction'] == 1).sum()
        accuracy = evaluate_results(df_result)

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Pesan", total)
        col2.metric("Laporan Progres", total_progress)
        # col3.metric("Akurasi Model", f"{accuracy:.2%}")
        col3.metric("Akurasi Model", accuracy)

        st.write("### Hasil Klasifikasi")
        st.dataframe(df_result.head())

        st.write("### Distribusi Prediksi")
        st.bar_chart(df_result['prediction_label'].value_counts())
else:
    st.info("Silakan upload file WhatsApp untuk melihat dashboard.")


# ── STYLE ───
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

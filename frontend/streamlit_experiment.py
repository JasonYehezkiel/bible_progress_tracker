import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Admin Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Admin Dashboard")
st.subheader("Sistem Rekapitulasi Progres Pembacaan Alkitab")

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #f9f9f9;
    border: 1px solid #ddd;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

#tesst

# st.markdown("""
#     <style>
#         body {
#             background-color: #ffffff;
#         }
#     </style>
# """, unsafe_allow_html=True)

st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #f0f0f0;
        }
        h1, h2, h3, h4, h5, h6 { 
            color: #000000;
        }
        p, div, span { 
            color: #000000;
        } 
    </style>
""", unsafe_allow_html=True)

# st.markdown("""
#      <style> /* Background abu-abu */ 
#         [data-testid="stAppViewContainer"] { 
#             background-color: #f0f0f0; 
#         } /* Kotak metric */ 
#         div[data-testid="metric-container"] { 
#             background-color: #ffffff; 
#             border: 1px solid #ccc; 
#             padding: 20px; 
#             border-radius: 10px; 
#             box-shadow: 2px 2px 6px rgba(0,0,0,0.1); 
#         } /* Header judul */ 
#         h1, h2, h3,h4, h5, h6  { 
#             color: #000000; 
#         } 
#         p, div, span { 
#             color: #000000;
#         }
#     </style> 
# """, unsafe_allow_html=True)




# Upload file
uploaded_file = st.file_uploader("Upload WhatsApp Export (.txt)", type=["txt"])

# Dummy data 
total_pesan = 1247
laporan_progres = 342
akurasi = 94.5
total_user = 28

# Metrics row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Pesan", total_pesan)
col2.metric("Laporan Progres", laporan_progres)
col3.metric("Akurasi Deteksi", f"{akurasi}%")
col4.metric("Total Pengguna", total_user)

st.markdown("---")

st.subheader("Timeline Aktivitas")

# Dummy timeline data
timeline_data = {
    "Tanggal": ["18 Jan", "19 Jan", "20 Jan"],
    "Jumlah Laporan": [12, 15, 18]
}

df = pd.DataFrame(timeline_data)

for i, row in df.iterrows():
    st.write(row["Tanggal"])
    st.progress(row["Jumlah Laporan"] / df["Jumlah Laporan"].max())
    st.write(f'{row["Jumlah Laporan"]} laporan')

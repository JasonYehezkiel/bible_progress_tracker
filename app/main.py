import sys
import streamlit as st
from pathlib import Path

root = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'src'))
sys.path.insert(0, str(root / 'app'))

st.set_page_config(
    page_title='Bible Reading Tracker',
    page_icon='📖',
    layout='wide',
    initial_sidebar_state='collapsed',
)


st.markdown("""
<style>
h2 {
    font-weight: 700;
    letter-spacing: -0.5px;
}
h3 {
    font-weight: 600;
    letter-spacing: -0.3px;
    margin-bottom: 0.25rem !important;
}
 
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    border: 1px solid rgba(0, 0, 0, 0.06);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    opacity: 0.6;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.5px;
}
 
button[data-baseweb="tab"] {
    font-size: 0.9rem;
    font-weight: 500;
    padding: 0.5rem 1rem;
}
[data-baseweb="tab-highlight"] {
    height: 3px;
    border-radius: 3px 3px 0 0;
}
 
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(0, 0, 0, 0.07);
}

[data-testid="stBaseButton-secondary"] {
    border-radius: 8px;
    font-weight: 500;
}
 
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input {
    border-radius: 8px;
}
 
[data-testid="stExpander"] {
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.07) !important;
}
 

[data-testid="stFileUploader"] {
    border-radius: 10px;
}

hr {
    margin: 0.75rem 0 !important;
    opacity: 0.15;
}
 

[data-testid="stCaptionContainer"] {
    opacity: 0.55;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('## 📖 Bible Reading Progress Tracker')
st.caption('Upload WhatsApp reports · track reading progress · manage members')
st.divider()

from sessions import create_tables

@st.cache_resource
def init_database():
    create_tables()

init_database()

from components import upload, progress, members

tab1, tab2, tab3 = st.tabs(['📤  Upload', '📖  Progress', '👥  Members'])

with tab1:
    upload.render()

with tab2:
    progress.render()

with tab3:
    members.render()
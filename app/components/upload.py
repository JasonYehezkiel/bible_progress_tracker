import tempfile
import streamlit as st

from ingestion import WhatsAppParser
from state import get_pipeline
from components.members import build_stats

def render():
    st.markdown('### 📤 Upload WhatsApp Chat')
    st.caption('Export your group chat from WhatsApp and upload the .txt file here.')

    uploaded_file = st.file_uploader(
        'Choose a WhatsApp export file',
        type=['txt'],
        label_visibility='collapsed',
    )

    if uploaded_file is None:
        st.info('No file uploaded yet. Export a WhatsApp chat as .txt file and upload it above.')
        return
    
    with st.spinner('Parsing chat file...'):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='wb') as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        
        parser = WhatsAppParser()
        try:
            df = parser.parse_chat_file(tmp_path)
        except Exception as e:
            st.error(f'Failed to parse file: {e}')
            return
    
    if df.empty:
        st.warning('No messages found. Make sure the file is valid WhatsApp export.')
        return
    
    total_msgs = len(df)
    senders = df['sender'].nunique()
    date_range = f'{df["timestamp"].min().date()} -> {df["timestamp"].max().date()}'

    col1, col2, col3 = st.columns(3)
    col1.metric('Total Messages', f'{total_msgs:,}')
    col2.metric('Senders', senders)
    col3.metric('Date Range', date_range)

    with st.expander('Preview parsed messages', expanded=False):
        st.dataframe(
            df[['timestamp', 'sender', 'message']].head(20),
            width='stretch',
            hide_index=True,
        )

    st.divider()

    if st.button('▶ Run Pipeline', type='primary', width='stretch'):
        pipeline = get_pipeline()
        progress_bar = st.progress(0, text='Classifying messages...')
        
        try:
            with st.spinner('Running Bible reference extraction pipeline...'):
                progress_bar.progress(20, text='Classifying messages...')
                totals = pipeline.process_batch(df)
                progress_bar.progress(100, text='Done!')
                build_stats.clear()
        except Exception as e:
            st.error(f'Pipeline error: {e}')
            return
        
        st.success('Pipeline completed successfully!')
        r1, r2, r3, r4 = st.columns(4)
        r1.metric('References Found', totals.get('refs', 0))
        r2.metric('Chapters Logged', totals.get('chapters', 0))
        r3.metric('Skipped (Invalid)', totals.get('skipped', 0))
        r4.metric('Already Processed', totals.get('resumed', 0))

        # store result in session state for progress tab
        st.session_state['last_pipeline_result'] = totals
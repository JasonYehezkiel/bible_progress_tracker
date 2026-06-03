import pandas as pd
import streamlit as st
from datetime import date
from typing import Dict, List

from sessions import get_session, get_all_members, get_last_read_by_member_id, get_all_progress_grouped
from state import get_pipeline

def compute_streaks(active_dates: List[date]) -> int:
    if not active_dates:
        return 0
    
    sorted_dates = sorted(set(active_dates))

    # current streak: backward pass   
    current = 1
    for i in range(len(sorted_dates) -1, 0, -1):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current += 1
        else:
            break
    
    if (date.today() - sorted_dates[-1]).days > 1:
        current = 0

    return current

@st.cache_data(ttl=300, show_spinner=False)
def build_stats(plan_days_elapsed: int) -> pd.DataFrame:
    today = date.today()
    rows = []

    with get_session() as session:
        members = get_all_members(session)
        progress_by_member = get_all_progress_grouped(session)
        for member in members:
            progress = progress_by_member.get(member.id, [])
            last = get_last_read_by_member_id(session, member.id, today)

            active_dates = [r.date_read for r in progress]
            active_days = len(set(active_dates))
            retention = active_days / plan_days_elapsed if plan_days_elapsed else 0.0
            last_read = (f'{last.book_name} {last.chapter} ({last.date_read})' if last else '-')

            rows.append({
                'Member': member.name,
                'Chapters': len(progress),
                'Retention': retention,
                'Streak 🔥': compute_streaks(active_dates),
                'Last Read': last_read,
            })
    
    return pd.DataFrame(rows)


def render() -> None:
    st.markdown('### 👥 Members')

    try:
        pipeline = get_pipeline()
    except Exception:
        st.info('No data yet  — upload a WhatsApp chat file in **upload** tab to get started.')
        return

    today = date.today()
    plan_days_elapsed = sum(1 for d in pipeline.schedule.dates if d <= today)

    df = build_stats(plan_days_elapsed)

    member_count = len(df)
    if member_count == 0:
        st.info('No members found yet — upload a WhatsApp chat file in the **Upload** tab to get started')
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Members', member_count)
    c2.metric('Plan Days Elapsed', plan_days_elapsed)
    c3.metric('Total Chapters', int(df['Chapters'].sum()))
    c4.metric('Avg Retention', f'{df['Retention'].mean():.0%}')
    st.divider()

    col_search, col_sort = st.columns([3, 1])
    with col_search:
        search = st.text_input(
            '🔍 Search member',
            placeholder='Type a name...',
            label_visibility='collapsed',
            key='member_search',
        )
    
    with col_sort:
        sort_by = st.selectbox(
            'Sort by',
            ['Member', 'Chapters', 'Retention', 'Streak 🔥'],
            label_visibility='collapsed',
            key='member_sort',
    )
        
    display_df = df.copy()
    if search:
        display_df = display_df[display_df['Member'].str.contains(search, case=False)]
        if display_df.empty:
            st.caption('No members match your search.')
            return
    ascending = sort_by == 'Member'
    display_df = display_df.sort_values(sort_by, ascending=ascending)

    styled = (
        display_df.style
        .format({'Retention': '{:.0%}'})
        .background_gradient(subset=['Chapters'], cmap='Blues', vmin=0)
        .background_gradient(subset=['Retention'], cmap='RdYlGn', vmin=0, vmax=1)
        .background_gradient(subset=['Streak 🔥'], cmap='Oranges', vmin=0)
    )
    st.dataframe(styled, width='stretch', hide_index=True)

                
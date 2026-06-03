import pandas as pd
import streamlit as st
from datetime import date
from typing import List

from compliance.checker import READING_STATUS
from state import get_pipeline

def status_label(status: str) -> str:
    info = READING_STATUS[status]
    return f'{info['emoji']} {info['label']}'

def highlight_status(val: str) -> str:
    for info in READING_STATUS.values():
        if info['emoji'] in val:
            return (
                f"background-color: {info['bg']}; "
                f"color: {info['color']}; "
                f"font-weight: 600;"
            )
    return ''

def format_chapters(chapters: List) -> str:
    if not chapters:
        return '-'
    return ', '.join(f'{b} {c}' for b, c in chapters)

def render_summary_card(selected_date: date) -> None:
    pipeline = get_pipeline()
    with st.spinner('Generating daily summary...'):
        try:
            summary = pipeline.summarize(selected_date)
            st.markdown(f'**Daily Compliance Summary**')
            st.code(summary, language=None)
        except Exception as e:
            st.error(f'Could not generate summary: {e}')

def render_compliance_table(
        selected_date: date, 
        results: List, 
        assigned_count: int
    ) -> None:
    compliant = sum(1 for r in results if r.is_complete)
    ahead = sum(1 for r in results if r.status == 'ahead')
    avg_rate = sum(r.completion_rate for r in results) / len(results)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Members', len(results))
    c2.metric('Compliant', f'{compliant}/{len(results)}')
    c3.metric('Ahead', ahead)
    c4.metric('Avg Progress', f'{avg_rate:.0%}')
 
    st.markdown(f'**Compliance — {selected_date}** *(plan: {assigned_count} chapter(s))*')
    
    status_order = {'ahead': 0, 'on_time': 1, 'late': 2}

    rows = [
        {
            'Member': r.member,
            'Status': status_label(r.status),
            'Done': len(r.completed),
            'Assigned': len(r.assigned),
            'Progress': r.completion_rate,
            'Missing': format_chapters(r.missing),
            'Extra Read': format_chapters(r.extra),
        }
        for r in sorted(results, key=lambda r: (status_order[r.status], r.member))
    ]


    styled = (
        pd.DataFrame(rows).style
        .map(highlight_status, subset=['Status'])
        .format({'Progress': '{:.0%}'})
        .set_properties(subset=['Missing'], **{'color': '#dc2626'})
        .set_properties(subset=['Extra Read'], **{'color': '#16a34a'})
    )

    st.dataframe(styled, width='stretch', hide_index=True)

    late_results = [r for r in results if r.status == 'late' and r.missing]
    if late_results:
        with st.expander(f'📋 Missing chapters detail ({len(late_results)} member(s))'):
            for r in late_results:
                missing_str = "  ".join(f"`{b} {c}`" for b, c in r.missing)
                st.markdown(
                    f"**{r.member}** — {len(r.completed)}/{len(r.assigned)} done "
                    f"({r.completion_rate:.0%})  \n&nbsp;&nbsp;{missing_str}"
                )

def render():
    st.markdown('### 📖 Reading Progress')

    col_date, col_btn = st.columns([3, 1])
    with col_date:
        selected_date = st.date_input(
            'Select date',
            value=date.today(),
            max_value=date.today(),
            label_visibility='collapsed',
        )
    with col_btn:
        show_summary = st.button('📋 Generate Summary', width='stretch')

    st.divider()

    try:
        pipeline = get_pipeline()
    except Exception:
        st.info('No data yet  — upload a WhatsApp chat file in **upload** tab to get started.')
        return
    
    assigned_count = len(pipeline.schedule.get_by_date(selected_date))
    results = pipeline.checker.check_all(selected_date)

    if not results:
        st.info('No members found.')
        return
    
    if assigned_count == 0:
        st.info(f'No chapters are assigned for {selected_date} in the reading plan.')
        return

    if show_summary:
        render_summary_card(selected_date)
        st.divider()
    
    render_compliance_table(selected_date, results, assigned_count)

    st.divider()
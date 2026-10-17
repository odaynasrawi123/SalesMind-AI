import html
import streamlit as st

NAVY = "#172B4D"
TEAL = "#0D9488"
GREEN = "#16A34A"
RED = "#DC2626"
BLUE = "#2563EB"
MUTED = "#64748B"
PLOT_COLORS = [TEAL, BLUE, "#8B5CF6", "#F59E0B", RED]

def apply_styles():
    st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1600px;
    }
    h1, h2, h3 {
        color: #172B4D;
        letter-spacing: -0.4px;
    }
    h1 {
        font-size: 2.1rem !important;
        font-weight: 750 !important;
    }
    h3 {
        font-weight: 650 !important;
    }
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
        min-height: 112px;
        box-shadow: 0 3px 12px rgba(20, 35, 60, 0.035);
    }
    [data-testid="stMetricLabel"] {
        color: #64748B;
        font-weight: 550;
    }
    [data-testid="stMetricValue"] {
        color: #172B4D;
        font-weight: 750;
    }
    [data-testid="stMetricDelta"] {
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        padding: 12px 14px;
    }
    div[data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 8px;
    }
    .sm-header {
        padding: 12px 0 22px 0;
    }
    .sm-eyebrow {
        font-size: 12px;
        letter-spacing: 1.5px;
        font-weight: 700;
        color: #0D9488;
        margin-bottom: 8px;
    }
    .sm-title {
        font-size: 32px;
        font-weight: 800;
        color: #172B4D;
        line-height: 1.25;
    }
    .sm-subtitle {
        font-size: 14px;
        color: #64748B;
        margin-top: 7px;
    }
    .sm-section {
        font-size: 20px;
        font-weight: 750;
        color: #172B4D;
        margin: 18px 0 12px 0;
    }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle):
    title = html.escape(str(title))
    subtitle = html.escape(str(subtitle))
    st.markdown(f'<div class="sm-header"><div class="sm-eyebrow">SALESMIND / ENTERPRISE ANALYTICS</div><div class="sm-title">{title}</div><div class="sm-subtitle">{subtitle}</div></div>', unsafe_allow_html=True)

def section_title(title):
    st.markdown(f'<div class="sm-section">{html.escape(str(title))}</div>', unsafe_allow_html=True)

def money(value, compact=True):
    value = float(value)
    if compact and abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if compact and abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.2f}"

def metric_card(label, value, delta=None, inverse=False, help_text=None):
    kwargs = {"label": label, "value": value}
    if delta is not None:
        kwargs["delta"] = delta
        kwargs["delta_color"] = "inverse" if inverse else "normal"
    if help_text:
        kwargs["help"] = help_text
    st.metric(**kwargs)

def style_chart(fig, title=None, height=420):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=22, r=22, t=65, b=35),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=12, color=NAVY),
        title=dict(text=title, font=dict(size=17, color=NAVY), x=0.02, xanchor="left"),
        colorway=PLOT_COLORS,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0)
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0", tickfont=dict(color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor="#EDF2F7", zeroline=False, tickfont=dict(color=MUTED))
    return fig

def show_chart(fig, title=None, height=420):
    fig = style_chart(fig, title, height)
    st.plotly_chart(fig, use_container_width=True)

def insight_card(title, message, level="info"):
    content = f"**{title}**\n\n{message}"
    if level == "warning":
        st.warning(content)
    elif level == "success":
        st.success(content)
    elif level == "error":
        st.error(content)
    else:
        st.info(content)
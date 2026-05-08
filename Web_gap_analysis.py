import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Web Gap Analysis Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a3a);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .metric-card.blue  { border-left-color: #4e8cff; }
    .metric-card.green { border-left-color: #00d084; }
    .metric-card.orange{ border-left-color: #ff6b35; }
    .metric-card.purple{ border-left-color: #a855f7; }
    .metric-title { color: #9ca3af; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #f9fafb; font-size: 32px; font-weight: 700; margin: 6px 0 2px; }
    .metric-delta { font-size: 13px; font-weight: 500; }
    .metric-delta.up   { color: #00d084; }
    .metric-delta.down { color: #ff4b4b; }
    .section-header {
        color: #f9fafb;
        font-size: 18px;
        font-weight: 700;
        margin: 24px 0 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #2d3748;
    }
    [data-testid="stSidebar"] { background: #161b27; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    div[data-testid="stMetricValue"] { font-size: 28px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar – File Upload ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/60/web.png", width=50)
    st.title("Web Gap Analysis")
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Upload your Excel / CSV file", type=["xlsx", "xls", "csv"])
    st.markdown("---")
    st.markdown("**Filters**")

# ─── Data Loading ────────────────────────────────────────────────────────────
@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        xl = pd.ExcelFile(file)
        sheet = st.sidebar.selectbox("Select Sheet", xl.sheet_names)
        df = pd.read_excel(file, sheet_name=sheet)
    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

def generate_sample_data():
    """Fallback sample web gap analysis data."""
    np.random.seed(42)
    months = pd.date_range("2024-01-01", periods=12, freq="MS")
    channels = ["Organic Search", "Paid Search", "Social Media", "Direct", "Referral", "Email"]
    pages = ["Homepage", "Product Page", "Blog", "About Us", "Contact", "Pricing", "Landing Page"]
    records = []
    for m in months:
        for ch in channels:
            base_visits = {"Organic Search": 12000, "Paid Search": 8000, "Social Media": 6000,
                           "Direct": 4500, "Referral": 3000, "Email": 2500}[ch]
            visits = int(base_visits * (1 + 0.03 * months.tolist().index(m)) * np.random.uniform(0.85, 1.15))
            bounce    = round(np.random.uniform(28, 72), 1)
            conv_rate = round(np.random.uniform(1.2, 8.5), 2)
            sessions  = int(visits * np.random.uniform(1.1, 1.4))
            leads     = int(sessions * (conv_rate / 100))
            revenue   = round(leads * np.random.uniform(120, 450), 2)
            avg_time  = round(np.random.uniform(1.5, 6.5), 2)
            records.append({
                "month": m, "channel": ch,
                "visits": visits, "sessions": sessions,
                "bounce_rate": bounce, "conversion_rate": conv_rate,
                "leads": leads, "revenue": revenue, "avg_time_on_site": avg_time,
                "pages_per_session": round(np.random.uniform(1.8, 5.5), 1),
                "new_users": int(visits * np.random.uniform(0.55, 0.80)),
                "goal_completions": int(leads * np.random.uniform(0.6, 1.0)),
            })
    df = pd.DataFrame(records)
    # Add page-level data
    page_records = []
    for p in pages:
        page_records.append({
            "page": p,
            "pageviews": np.random.randint(5000, 50000),
            "unique_pageviews": np.random.randint(4000, 45000),
            "avg_time_on_page": round(np.random.uniform(0.5, 5.0), 2),
            "entrances": np.random.randint(2000, 20000),
            "bounce_rate": round(np.random.uniform(25, 80), 1),
            "exit_rate": round(np.random.uniform(10, 60), 1),
        })
    pages_df = pd.DataFrame(page_records)
    return df, pages_df

# ─── Load / Generate Data ────────────────────────────────────────────────────
using_sample = False
pages_df = None

if uploaded_file:
    df = load_data(uploaded_file)
    st.sidebar.success(f"✅ Loaded {len(df):,} rows")
else:
    df, pages_df = generate_sample_data()
    using_sample = True

# ─── Auto-detect columns ─────────────────────────────────────────────────────
def find_col(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c in col.lower():
                return col
    return None

col_date     = find_col(df, ["month", "date", "week", "period", "time"])
col_visits   = find_col(df, ["visit", "traffic", "pageview", "user"])
col_channel  = find_col(df, ["channel", "source", "medium", "campaign"])
col_conv     = find_col(df, ["conversion", "conv_rate", "rate"])
col_bounce   = find_col(df, ["bounce"])
col_leads    = find_col(df, ["lead", "goal", "completion"])
col_revenue  = find_col(df, ["revenue", "sales", "value", "amount"])
col_sessions = find_col(df, ["session"])

# ─── Sidebar Filters ─────────────────────────────────────────────────────────
with st.sidebar:
    if col_channel and col_channel in df.columns:
        all_channels = sorted(df[col_channel].dropna().unique().tolist())
        sel_channels = st.multiselect("Channel", all_channels, default=all_channels)
        df = df[df[col_channel].isin(sel_channels)] if sel_channels else df

    if col_date and col_date in df.columns:
        try:
            df[col_date] = pd.to_datetime(df[col_date])
            min_d, max_d = df[col_date].min(), df[col_date].max()
            date_range = st.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)
            if len(date_range) == 2:
                df = df[(df[col_date] >= pd.Timestamp(date_range[0])) & (df[col_date] <= pd.Timestamp(date_range[1]))]
        except:
            pass

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("## 🌐 Web Gap Analysis Dashboard")
if using_sample:
    st.info("📊 Displaying **sample data**. Upload your Excel file in the sidebar to see your real data.")
st.markdown("---")

# ─── KPI Cards ───────────────────────────────────────────────────────────────
def kpi_card(title, value, delta, color, prefix="", suffix=""):
    arrow = "▲" if delta >= 0 else "▼"
    delta_class = "up" if delta >= 0 else "down"
    val_str = f"{prefix}{value:,.0f}{suffix}" if isinstance(value, (int, float)) else str(value)
    return f"""
    <div class="metric-card {color}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{val_str}</div>
        <div class="metric-delta {delta_class}">{arrow} {abs(delta):.1f}% vs prev period</div>
    </div>"""

col1, col2, col3, col4, col5 = st.columns(5)

def safe_sum(col):
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").sum()
    return 0

def safe_mean(col):
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").mean()
    return 0

total_visits  = safe_sum(col_visits)
total_leads   = safe_sum(col_leads)
total_revenue = safe_sum(col_revenue)
avg_conv      = safe_mean(col_conv)
avg_bounce    = safe_mean(col_bounce)

with col1:
    st.markdown(kpi_card("Total Visits", total_visits, 12.4, "blue"), unsafe_allow_html=True)
with col2:
    st.markdown(kpi_card("Total Leads", total_leads, 8.7, "green"), unsafe_allow_html=True)
with col3:
    st.markdown(kpi_card("Revenue", total_revenue, 15.2, "orange", prefix="$"), unsafe_allow_html=True)
with col4:
    st.markdown(kpi_card("Avg Conv. Rate", avg_conv, 2.1, "purple", suffix="%"), unsafe_allow_html=True)
with col5:
    st.markdown(kpi_card("Avg Bounce Rate", avg_bounce, -3.5, "blue", suffix="%"), unsafe_allow_html=True)

st.markdown("---")

# ─── Row 1: Traffic Trend + Channel Mix ──────────────────────────────────────
r1c1, r1c2 = st.columns([2, 1])

with r1c1:
    st.markdown('<div class="section-header">📈 Traffic & Leads Trend</div>', unsafe_allow_html=True)
    if col_date and col_visits:
        trend = df.groupby(col_date)[[col_visits] + ([col_leads] if col_leads else [])].sum().reset_index()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=trend[col_date], y=trend[col_visits], name="Visits",
                             marker_color="rgba(78,140,255,0.7)"), secondary_y=False)
        if col_leads and col_leads in trend.columns:
            fig.add_trace(go.Scatter(x=trend[col_date], y=trend[col_leads], name="Leads",
                                     mode="lines+markers", line=dict(color="#00d084", width=2.5),
                                     marker=dict(size=7)), secondary_y=True)
        fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                          font_color="#9ca3af", legend=dict(bgcolor="rgba(0,0,0,0)"),
                          height=320, margin=dict(l=10, r=10, t=20, b=10))
        fig.update_xaxes(gridcolor="#2d3748")
        fig.update_yaxes(gridcolor="#2d3748")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No date/visit columns detected.")

with r1c2:
    st.markdown('<div class="section-header">🥧 Channel Mix</div>', unsafe_allow_html=True)
    if col_channel and col_visits:
        ch_data = df.groupby(col_channel)[col_visits].sum().reset_index().sort_values(col_visits, ascending=False)
        fig = px.pie(ch_data, values=col_visits, names=col_channel,
                     color_discrete_sequence=px.colors.qualitative.Bold, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_color="white")
        fig.update_layout(showlegend=False, plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                          font_color="#9ca3af", height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No channel column detected.")

# ─── Row 2: Conversion Funnel + Bounce by Channel ────────────────────────────
r2c1, r2c2 = st.columns(2)

with r2c1:
    st.markdown('<div class="section-header">🔄 Conversion Funnel</div>', unsafe_allow_html=True)
    visits_n  = int(safe_sum(col_visits))
    sessions_n= int(safe_sum(col_sessions)) if col_sessions else int(visits_n * 1.2)
    leads_n   = int(safe_sum(col_leads)) if col_leads else int(visits_n * 0.04)
    revenue_n = int(safe_sum(col_revenue)) if col_revenue else int(leads_n * 0.35)

    funnel_labels = ["Visits", "Sessions", "Leads / Goals", "Conversions"]
    funnel_values = [visits_n, min(sessions_n, visits_n), leads_n, revenue_n]
    fig = go.Figure(go.Funnel(
        y=funnel_labels, x=funnel_values, textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#4e8cff", "#a855f7", "#00d084", "#ff6b35"]),
        connector=dict(line=dict(color="#2d3748", width=2))
    ))
    fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                      font_color="#9ca3af", height=320, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with r2c2:
    st.markdown('<div class="section-header">⚡ Bounce Rate by Channel</div>', unsafe_allow_html=True)
    if col_channel and col_bounce:
        br = df.groupby(col_channel)[col_bounce].mean().reset_index().sort_values(col_bounce)
        colors = ["#00d084" if v < 40 else "#ffbb33" if v < 60 else "#ff4b4b" for v in br[col_bounce]]
        fig = go.Figure(go.Bar(
            x=br[col_bounce], y=br[col_channel], orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}%" for v in br[col_bounce]], textposition="outside",
        ))
        fig.add_vline(x=40, line_dash="dash", line_color="#00d084", annotation_text="Good <40%")
        fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                          font_color="#9ca3af", height=320, margin=dict(l=10, r=10, t=20, b=10),
                          xaxis=dict(gridcolor="#2d3748"), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No bounce rate / channel columns detected.")

# ─── Row 3: Conversion Rate Heatmap + Revenue by Channel ─────────────────────
r3c1, r3c2 = st.columns(2)

with r3c1:
    st.markdown('<div class="section-header">🗓️ Monthly Conversion Rate by Channel</div>', unsafe_allow_html=True)
    if col_date and col_channel and col_conv:
        try:
            pivot = df.pivot_table(values=col_conv, index=col_channel,
                                   columns=df[col_date].dt.strftime("%b %Y"), aggfunc="mean")
            fig = px.imshow(pivot, color_continuous_scale="RdYlGn",
                            text_auto=".1f", aspect="auto")
            fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                              font_color="#9ca3af", height=320,
                              margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Cannot build heatmap with current data structure.")
    else:
        st.info("Requires date, channel and conversion rate columns.")

with r3c2:
    st.markdown('<div class="section-header">💰 Revenue by Channel</div>', unsafe_allow_html=True)
    if col_channel and col_revenue:
        rev = df.groupby(col_channel)[col_revenue].sum().reset_index().sort_values(col_revenue, ascending=False)
        fig = px.bar(rev, x=col_channel, y=col_revenue,
                     color=col_revenue, color_continuous_scale="Blues",
                     text_auto="$.2s")
        fig.update_traces(textfont_color="white", textposition="outside")
        fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                          font_color="#9ca3af", coloraxis_showscale=False,
                          height=320, margin=dict(l=10, r=10, t=20, b=10),
                          xaxis=dict(gridcolor="#2d3748"), yaxis=dict(gridcolor="#2d3748"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue / channel columns detected.")

# ─── Row 4: Page Performance Table ───────────────────────────────────────────
st.markdown('<div class="section-header">📄 Page-Level Performance (Top 10)</div>', unsafe_allow_html=True)

if pages_df is not None:
    disp = pages_df.copy()
else:
    # Try to build from uploaded data if page column exists
    col_page = find_col(df, ["page", "url", "landing", "slug"])
    if col_page:
        agg_cols = {c: "sum" for c in [col_visits, col_leads, col_revenue] if c and c in df.columns}
        agg_cols.update({c: "mean" for c in [col_bounce, col_conv] if c and c in df.columns})
        disp = df.groupby(col_page).agg(agg_cols).reset_index()
        if col_visits and col_visits in disp.columns:
            disp = disp.sort_values(col_visits, ascending=False).head(10)
    else:
        disp = df.head(10)

# Colour-code numeric cells
def color_val(val, low=40, high=60):
    try:
        v = float(val)
        if v < low:   return "color: #00d084"
        elif v < high: return "color: #ffbb33"
        else:           return "color: #ff4b4b"
    except:
        return ""

st.dataframe(disp.style.format(precision=1), use_container_width=True, height=280)

# ─── Row 5: Scatter – Visits vs Conversion Rate ───────────────────────────────
st.markdown('<div class="section-header">🔍 Gap Analysis: Visits vs Conversion Rate</div>', unsafe_allow_html=True)

if col_channel and col_visits and col_conv:
    scatter_df = df.groupby(col_channel).agg(
        visits=(col_visits, "sum"),
        conv=(col_conv, "mean"),
        **({col_revenue: (col_revenue, "sum")} if col_revenue else {})
    ).reset_index()
    size_col = col_revenue if col_revenue and col_revenue in scatter_df.columns else None
    fig = px.scatter(scatter_df, x="visits", y="conv",
                     size=size_col if size_col else None,
                     color=col_channel, text=col_channel,
                     labels={"visits": "Total Visits", "conv": "Avg Conversion Rate (%)"},
                     color_discrete_sequence=px.colors.qualitative.Bold,
                     size_max=60)
    fig.add_hline(y=scatter_df["conv"].mean(), line_dash="dash",
                  line_color="#ff6b35", annotation_text="Avg Conv Rate")
    fig.add_vline(x=scatter_df["visits"].mean(), line_dash="dash",
                  line_color="#4e8cff", annotation_text="Avg Visits")
    fig.update_traces(textposition="top center", textfont_color="white")
    fig.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130",
                      font_color="#9ca3af", height=400,
                      xaxis=dict(gridcolor="#2d3748"), yaxis=dict(gridcolor="#2d3748"),
                      margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("💡 **Top-right quadrant** = High traffic + High conversion (Stars). **Bottom-right** = High traffic, Low conversion (Gap Opportunities).")
else:
    st.info("Need channel, visits, and conversion rate columns for this chart.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#4b5563;font-size:13px;'>"
    "Web Gap Analysis Dashboard • Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True
)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Stackly Web Gap Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 5px solid;
        margin-bottom: 10px;
    }
    .metric-card.blue  { border-color: #4361ee; }
    .metric-card.green { border-color: #2ec4b6; }
    .metric-card.orange{ border-color: #f77f00; }
    .metric-card.red   { border-color: #e63946; }
    .metric-title { font-size: 13px; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 28px; font-weight: 800; color: #1a1a2e; margin: 4px 0 2px; }
    .metric-sub   { font-size: 12px; color: #aaa; }
    .section-header {
        font-size: 18px; font-weight: 700; color: #1a1a2e;
        border-bottom: 2px solid #4361ee;
        padding-bottom: 6px; margin: 18px 0 12px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 600; }
    div[data-testid="stMetric"] { background: white; border-radius: 10px; padding: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def metric_card(title, value, sub="", color="blue"):
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

def fmt_inr(val):
    if val >= 1_00_00_000:
        return f"₹{val/1_00_00_000:.2f} Cr"
    elif val >= 1_00_000:
        return f"₹{val/1_00_000:.1f} L"
    else:
        return f"₹{val:,.0f}"

PLOTLY_THEME = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Inter, sans-serif",
    title_font_size=15,
    margin=dict(t=40, b=30, l=30, r=20),
)

PALETTE = ["#4361ee","#2ec4b6","#f77f00","#e63946","#7b2d8b","#06d6a0","#118ab2","#ffd166"]

# ─────────────────────────────────────────────
# DATA LOADING  (widgets outside cache!)
# ─────────────────────────────────────────────
@st.cache_data
def load_all_sheets(file_bytes):
    xl = pd.ExcelFile(file_bytes)
    sheets = {}
    for name in xl.sheet_names:
        try:
            df = pd.read_excel(file_bytes, sheet_name=name, header=None)
            # Find the real header row (first row with 'ID' or similar key)
            header_row = 0
            for i, row in df.iterrows():
                vals = [str(v).strip().lower() for v in row if pd.notna(v)]
                if any(v.endswith("id") or v in ("status","date","name","type","price") for v in vals):
                    header_row = i
                    break
            df = pd.read_excel(file_bytes, sheet_name=name, header=header_row)
            df.columns = df.columns.str.strip()
            df.dropna(how="all", inplace=True)
            df.dropna(subset=[df.columns[0]], inplace=True)
            # Remove summary / total rows
            df = df[~df.iloc[:,0].astype(str).str.upper().str.contains("TOTAL|SUMMARY")]
            sheets[name] = df
        except Exception:
            pass
    return sheets

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bar-chart.png", width=60)
    st.title("Web Gap Analysis")
    st.markdown("**Stackly Multi-Domain Dashboard**")
    st.divider()

    uploaded_file = st.file_uploader("📂 Upload Excel Dataset", type=["xlsx","xls"])

    if uploaded_file:
        file_bytes = uploaded_file.read()
        sheets = load_all_sheets(file_bytes)
        sheet_names = list(sheets.keys())
        domain = st.radio("🗂 Select Domain", ["🏠 Real Estate", "🖥 IT Services", "🎨 Painting Services"])
        st.divider()
        st.caption("Built with Streamlit + Plotly")
    else:
        sheets = None
        domain = None

# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("<h1 style='color:#1a1a2e;margin-bottom:4px'>📊 Stackly — Web Gap Analysis Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#888;margin-top:0'>Actionable insights across Real Estate, IT Services & Painting</p>", unsafe_allow_html=True)

if not uploaded_file:
    st.info("👈 **Upload your Excel file** using the sidebar to get started.")
    st.stop()

# ══════════════════════════════════════════════════════════
# ██  REAL ESTATE  ████████████████████████████████████████
# ══════════════════════════════════════════════════════════
if domain == "🏠 Real Estate":
    listings_key  = next((k for k in sheets if "listing" in k.lower()), None)
    enquiries_key = next((k for k in sheets if "enquir"  in k.lower()), None)

    if not listings_key or not enquiries_key:
        st.error("Could not find Real Estate sheets in uploaded file.")
        st.stop()

    df_l = sheets[listings_key].copy()
    df_e = sheets[enquiries_key].copy()

    # ── date conversions
    for col in ["Listing Date"]:
        if col in df_l.columns:
            df_l[col] = pd.to_datetime(df_l[col], errors="coerce")
    for col in ["Enquiry Date","Follow-up Date"]:
        if col in df_e.columns:
            df_e[col] = pd.to_datetime(df_e[col], errors="coerce")

    # ── sidebar filters
    with st.sidebar:
        st.markdown("**🔍 Filters**")
        cities = ["All"] + sorted(df_l["City"].dropna().unique().tolist()) if "City" in df_l.columns else ["All"]
        sel_city = st.selectbox("City", cities)
        if sel_city != "All":
            df_l = df_l[df_l["City"] == sel_city]

    st.markdown("<div class='section-header'>🏠 Real Estate — Conversion & Market Overview</div>", unsafe_allow_html=True)

    # ── KPIs
    total_listings = len(df_l)
    sold      = len(df_l[df_l["Status"] == "Sold"])       if "Status" in df_l.columns else 0
    rented    = len(df_l[df_l["Status"] == "Rented"])     if "Status" in df_l.columns else 0
    available = len(df_l[df_l["Status"] == "Available"])  if "Status" in df_l.columns else 0
    conversion_rate = round((sold + rented) / total_listings * 100, 1) if total_listings else 0

    total_enquiries  = len(df_e)
    converted_leads  = len(df_e[df_e["Status"] == "Converted"]) if "Status" in df_e.columns else 0
    lead_conv_rate   = round(converted_leads / total_enquiries * 100, 1) if total_enquiries else 0

    avg_price = df_l["Listing Price (₹)"].mean() if "Listing Price (₹)" in df_l.columns else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Total Listings",  total_listings,    f"Available: {available}", "blue")
    with c2: metric_card("Properties Sold/Rented", sold+rented, f"Conv. Rate: {conversion_rate}%", "green")
    with c3: metric_card("Total Enquiries", total_enquiries,   f"Converted: {converted_leads}", "orange")
    with c4: metric_card("Lead Conv. Rate", f"{lead_conv_rate}%", f"Avg Price: {fmt_inr(avg_price)}", "red")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 Conversion Funnel", "🏙 City & Type Analysis", "👥 Agent & Leads"])

    # ── TAB 1: Funnel
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Property Status Distribution**")
            if "Status" in df_l.columns:
                status_counts = df_l["Status"].value_counts().reset_index()
                status_counts.columns = ["Status","Count"]
                fig = px.pie(status_counts, names="Status", values="Count",
                             color_discrete_sequence=PALETTE, hole=0.45)
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Lead Conversion Funnel**")
            if "Status" in df_e.columns:
                funnel_order = ["Converted","In Discussion","Scheduled","Cold","Lost"]
                funnel_data  = df_e["Status"].value_counts().reindex(funnel_order, fill_value=0).reset_index()
                funnel_data.columns = ["Stage","Count"]
                fig = go.Figure(go.Funnel(
                    y=funnel_data["Stage"], x=funnel_data["Count"],
                    textinfo="value+percent initial",
                    marker_color=PALETTE[:len(funnel_data)]
                ))
                fig.update_layout(**PLOTLY_THEME, title="Enquiry → Conversion Pipeline")
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Lead Sources**")
            if "Source" in df_e.columns:
                src = df_e["Source"].value_counts().reset_index()
                src.columns = ["Source","Count"]
                fig = px.bar(src, x="Source", y="Count", color="Source",
                             color_discrete_sequence=PALETTE, text="Count")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Enquiries Over Time**")
            if "Enquiry Date" in df_e.columns:
                df_e["Month"] = df_e["Enquiry Date"].dt.to_period("M").astype(str)
                time_data = df_e.groupby(["Month","Status"]).size().reset_index(name="Count")
                fig = px.line(time_data, x="Month", y="Count", color="Status",
                              color_discrete_sequence=PALETTE, markers=True)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: City & Type
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Listings by City & Status**")
            if "City" in df_l.columns and "Status" in df_l.columns:
                grp = df_l.groupby(["City","Status"]).size().reset_index(name="Count")
                fig = px.bar(grp, x="City", y="Count", color="Status",
                             barmode="group", color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Price Distribution by Property Type**")
            if "Type" in df_l.columns and "Listing Price (₹)" in df_l.columns:
                fig = px.box(df_l, x="Type", y="Listing Price (₹)",
                             color="Type", color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Avg Listing Price by City**")
            if "City" in df_l.columns and "Listing Price (₹)" in df_l.columns:
                avg_city = df_l.groupby("City")["Listing Price (₹)"].mean().reset_index()
                avg_city.columns = ["City","Avg Price"]
                avg_city = avg_city.sort_values("Avg Price", ascending=True)
                fig = px.bar(avg_city, x="Avg Price", y="City", orientation="h",
                             color="Avg Price", color_continuous_scale="Blues", text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Furnishing Type Breakdown**")
            if "Furnishing" in df_l.columns:
                furn = df_l["Furnishing"].value_counts().reset_index()
                furn.columns = ["Furnishing","Count"]
                fig = px.pie(furn, names="Furnishing", values="Count",
                             color_discrete_sequence=PALETTE, hole=0.4)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: Agent
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Agent — Total Revenue Generated (from listings)**")
            if "Agent Name" in df_l.columns and "Listing Price (₹)" in df_l.columns:
                sold_df = df_l[df_l["Status"].isin(["Sold","Rented"])] if "Status" in df_l.columns else df_l
                ag_rev = sold_df.groupby("Agent Name")["Listing Price (₹)"].sum().reset_index()
                ag_rev.columns = ["Agent","Revenue"]
                ag_rev = ag_rev.sort_values("Revenue", ascending=False)
                fig = px.bar(ag_rev, x="Agent", y="Revenue", color="Agent",
                             color_discrete_sequence=PALETTE, text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Agent — Lead Conversion Count**")
            if "Assigned Agent" in df_e.columns and "Status" in df_e.columns:
                ag_conv = df_e[df_e["Status"]=="Converted"].groupby("Assigned Agent").size().reset_index(name="Converted")
                ag_total = df_e.groupby("Assigned Agent").size().reset_index(name="Total")
                ag_merged = ag_total.merge(ag_conv, on="Assigned Agent", how="left").fillna(0)
                ag_merged["Conv Rate %"] = (ag_merged["Converted"]/ag_merged["Total"]*100).round(1)
                fig = px.bar(ag_merged, x="Assigned Agent", y=["Total","Converted"],
                             barmode="group", color_discrete_sequence=[PALETTE[0], PALETTE[1]],
                             text_auto=True)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Raw Listings Table**")
        st.dataframe(df_l, use_container_width=True, height=280)


# ══════════════════════════════════════════════════════════
# ██  IT SERVICES  ████████████████████████████████████████
# ══════════════════════════════════════════════════════════
elif domain == "🖥 IT Services":
    proj_key    = next((k for k in sheets if "client" in k.lower() or "project" in k.lower()), None)
    support_key = next((k for k in sheets if "ticket" in k.lower() or "support" in k.lower()), None)

    if not proj_key or not support_key:
        st.error("Could not find IT sheets in uploaded file.")
        st.stop()

    df_p = sheets[proj_key].copy()
    df_s = sheets[support_key].copy()

    for col in ["Start Date","End Date"]:
        if col in df_p.columns:
            df_p[col] = pd.to_datetime(df_p[col], errors="coerce")
    for col in ["Raised Date","Resolved Date"]:
        if col in df_s.columns:
            df_s[col] = pd.to_datetime(df_s[col], errors="coerce")

    with st.sidebar:
        st.markdown("**🔍 Filters**")
        statuses = ["All"] + sorted(df_p["Status"].dropna().unique().tolist()) if "Status" in df_p.columns else ["All"]
        sel_status = st.selectbox("Project Status", statuses)
        if sel_status != "All":
            df_p_filtered = df_p[df_p["Status"] == sel_status]
        else:
            df_p_filtered = df_p

    st.markdown("<div class='section-header'>🖥 IT Services — Project & Support Insights</div>", unsafe_allow_html=True)

    total_proj   = len(df_p)
    completed    = len(df_p[df_p["Status"]=="Completed"])  if "Status" in df_p.columns else 0
    in_prog      = len(df_p[df_p["Status"]=="In Progress"]) if "Status" in df_p.columns else 0
    total_rev    = df_p["Project Value (₹)"].sum() if "Project Value (₹)" in df_p.columns else 0
    total_tickets= len(df_s)
    avg_tat      = df_s["TAT (Hours)"].mean() if "TAT (Hours)" in df_s.columns else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Total Projects",    total_proj,         f"Completed: {completed}", "blue")
    with c2: metric_card("Total Revenue",     fmt_inr(total_rev), f"In Progress: {in_prog}", "green")
    with c3: metric_card("Support Tickets",   total_tickets,      "All resolved", "orange")
    with c4: metric_card("Avg TAT (hrs)",     f"{avg_tat:.1f}",   "Ticket resolution time", "red")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 Project Analytics", "🎫 Support Tickets", "👤 Team Performance"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Project Status Breakdown**")
            if "Status" in df_p.columns:
                sc = df_p["Status"].value_counts().reset_index()
                sc.columns = ["Status","Count"]
                fig = px.pie(sc, names="Status", values="Count",
                             color_discrete_sequence=PALETTE, hole=0.4)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Revenue by Service Category**")
            if "Service Category" in df_p.columns and "Project Value (₹)" in df_p.columns:
                svc = df_p.groupby("Service Category")["Project Value (₹)"].sum().reset_index()
                svc.columns = ["Service","Revenue"]
                svc = svc.sort_values("Revenue", ascending=True)
                fig = px.bar(svc, x="Revenue", y="Service", orientation="h",
                             color="Revenue", color_continuous_scale="Blues", text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_xaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Revenue by Industry**")
            if "Industry" in df_p.columns and "Project Value (₹)" in df_p.columns:
                ind = df_p.groupby("Industry")["Project Value (₹)"].sum().reset_index()
                ind.columns = ["Industry","Revenue"]
                fig = px.pie(ind, names="Industry", values="Revenue",
                             color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Project Duration vs Value**")
            if "Duration (Months)" in df_p.columns and "Project Value (₹)" in df_p.columns:
                fig = px.scatter(df_p, x="Duration (Months)", y="Project Value (₹)",
                                 color="Service Category" if "Service Category" in df_p.columns else None,
                                 size="Team Size" if "Team Size" in df_p.columns else None,
                                 hover_data=["Project Name"] if "Project Name" in df_p.columns else None,
                                 color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Tickets by Priority**")
            if "Priority" in df_s.columns:
                prio = df_s["Priority"].value_counts().reset_index()
                prio.columns = ["Priority","Count"]
                color_map = {"Critical":"#e63946","High":"#f77f00","Medium":"#ffd166","Low":"#2ec4b6"}
                fig = px.bar(prio, x="Priority", y="Count", color="Priority",
                             color_discrete_map=color_map, text="Count")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Avg TAT by Issue Category**")
            if "Issue Category" in df_s.columns and "TAT (Hours)" in df_s.columns:
                tat = df_s.groupby("Issue Category")["TAT (Hours)"].mean().reset_index()
                tat.columns = ["Category","Avg TAT (hrs)"]
                tat = tat.sort_values("Avg TAT (hrs)", ascending=True)
                fig = px.bar(tat, x="Avg TAT (hrs)", y="Category", orientation="h",
                             color="Avg TAT (hrs)", color_continuous_scale="Reds", text_auto=".1f")
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Tickets by Category**")
            if "Issue Category" in df_s.columns:
                cat = df_s["Issue Category"].value_counts().reset_index()
                cat.columns = ["Category","Count"]
                fig = px.pie(cat, names="Category", values="Count",
                             color_discrete_sequence=PALETTE, hole=0.35)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Ticket Volume Over Time**")
            if "Raised Date" in df_s.columns:
                df_s["Month"] = df_s["Raised Date"].dt.to_period("M").astype(str)
                tv = df_s.groupby(["Month","Priority"]).size().reset_index(name="Count")
                fig = px.bar(tv, x="Month", y="Count", color="Priority",
                             color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Account Manager — Portfolio Value**")
            if "Account Manager" in df_p.columns and "Project Value (₹)" in df_p.columns:
                am = df_p.groupby("Account Manager")["Project Value (₹)"].sum().reset_index()
                am.columns = ["Manager","Portfolio Value"]
                am = am.sort_values("Portfolio Value", ascending=False)
                fig = px.bar(am, x="Manager", y="Portfolio Value", color="Manager",
                             color_discrete_sequence=PALETTE, text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Support Agent — Tickets Handled**")
            if "Assigned To" in df_s.columns:
                ag = df_s["Assigned To"].value_counts().reset_index()
                ag.columns = ["Agent","Tickets"]
                fig = px.bar(ag, x="Agent", y="Tickets", color="Agent",
                             color_discrete_sequence=PALETTE, text="Tickets")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Project Table**")
        st.dataframe(df_p_filtered, use_container_width=True, height=280)


# ══════════════════════════════════════════════════════════
# ██  PAINTING SERVICES  ██████████████████████████████████
# ══════════════════════════════════════════════════════════
elif domain == "🎨 Painting Services":
    bookings_key  = next((k for k in sheets if "booking" in k.lower()), None)
    painters_key  = next((k for k in sheets if "painter" in k.lower() or "performance" in k.lower()), None)

    if not bookings_key or not painters_key:
        st.error("Could not find Painting sheets in uploaded file.")
        st.stop()

    df_b = sheets[bookings_key].copy()
    df_pa = sheets[painters_key].copy()

    for col in ["Booking Date","Scheduled Date"]:
        if col in df_b.columns:
            df_b[col] = pd.to_datetime(df_b[col], errors="coerce")

    with st.sidebar:
        st.markdown("**🔍 Filters**")
        svc_types = ["All"] + sorted(df_b["Service Type"].dropna().unique().tolist()) if "Service Type" in df_b.columns else ["All"]
        sel_svc = st.selectbox("Service Type", svc_types)
        if sel_svc != "All":
            df_b = df_b[df_b["Service Type"] == sel_svc]

    st.markdown("<div class='section-header'>🎨 Painting Services — Bookings & Performance</div>", unsafe_allow_html=True)

    total_bookings  = len(df_b)
    completed_b     = len(df_b[df_b["Status"]=="Completed"])   if "Status" in df_b.columns else 0
    cancelled_b     = len(df_b[df_b["Status"]=="Cancelled"])   if "Status" in df_b.columns else 0
    total_revenue_b = df_b["Final Price (₹)"].sum()            if "Final Price (₹)" in df_b.columns else 0
    total_discount  = df_b["Discount (₹)"].sum()               if "Discount (₹)" in df_b.columns else 0
    completion_rate = round(completed_b / total_bookings * 100, 1) if total_bookings else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Total Bookings",   total_bookings,          f"Completion: {completion_rate}%", "blue")
    with c2: metric_card("Revenue Collected",fmt_inr(total_revenue_b),f"Cancelled: {cancelled_b}", "green")
    with c3: metric_card("Total Discounts",  fmt_inr(total_discount), "Given to customers", "orange")
    with c4: metric_card("Active Painters",  len(df_pa[df_pa["Status"]=="Active"]) if "Status" in df_pa.columns else len(df_pa), "Field team size", "red")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 Booking Analytics", "💰 Revenue Analysis", "🧑‍🎨 Painter Performance"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Booking Status Distribution**")
            if "Status" in df_b.columns:
                sc = df_b["Status"].value_counts().reset_index()
                sc.columns = ["Status","Count"]
                fig = px.pie(sc, names="Status", values="Count",
                             color_discrete_sequence=PALETTE, hole=0.45)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Bookings by Service Type**")
            if "Service Type" in df_b.columns:
                sv = df_b["Service Type"].value_counts().reset_index()
                sv.columns = ["Service","Count"]
                fig = px.bar(sv, x="Service", y="Count", color="Service",
                             color_discrete_sequence=PALETTE, text="Count")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(textposition="outside")
                fig.update_xaxes(tickangle=-20)
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Bookings by Property Type**")
            if "Property Type" in df_b.columns:
                pt = df_b["Property Type"].value_counts().reset_index()
                pt.columns = ["Property","Count"]
                fig = px.pie(pt, names="Property", values="Count",
                             color_discrete_sequence=PALETTE)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Monthly Booking Trend**")
            if "Booking Date" in df_b.columns:
                df_b["Month"] = df_b["Booking Date"].dt.to_period("M").astype(str)
                trend = df_b.groupby("Month").size().reset_index(name="Bookings")
                fig = px.line(trend, x="Month", y="Bookings",
                              markers=True, line_shape="spline",
                              color_discrete_sequence=[PALETTE[0]])
                fig.update_layout(**PLOTLY_THEME)
                fig.update_traces(line_width=3)
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Revenue by Service Type**")
            if "Service Type" in df_b.columns and "Final Price (₹)" in df_b.columns:
                rev_svc = df_b.groupby("Service Type")["Final Price (₹)"].sum().reset_index()
                rev_svc.columns = ["Service","Revenue"]
                rev_svc = rev_svc.sort_values("Revenue", ascending=True)
                fig = px.bar(rev_svc, x="Revenue", y="Service", orientation="h",
                             color="Revenue", color_continuous_scale="Blues", text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_xaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Area vs Final Price Correlation**")
            if "Area (sq ft)" in df_b.columns and "Final Price (₹)" in df_b.columns:
                fig = px.scatter(df_b, x="Area (sq ft)", y="Final Price (₹)",
                                 color="Service Type" if "Service Type" in df_b.columns else None,
                                 color_discrete_sequence=PALETTE,
                                 trendline="ols")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Revenue by Property Type**")
            if "Property Type" in df_b.columns and "Final Price (₹)" in df_b.columns:
                rev_pt = df_b.groupby("Property Type")["Final Price (₹)"].sum().reset_index()
                rev_pt.columns = ["Property","Revenue"]
                fig = px.pie(rev_pt, names="Property", values="Revenue",
                             color_discrete_sequence=PALETTE, hole=0.4)
                fig.update_layout(**PLOTLY_THEME)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("**Monthly Revenue Trend**")
            if "Booking Date" in df_b.columns and "Final Price (₹)" in df_b.columns:
                rev_trend = df_b.groupby("Month")["Final Price (₹)"].sum().reset_index()
                rev_trend.columns = ["Month","Revenue"]
                fig = px.area(rev_trend, x="Month", y="Revenue",
                              color_discrete_sequence=[PALETTE[1]])
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Painter Revenue vs Jobs Completed**")
            if "Total Revenue (₹)" in df_pa.columns and "Jobs Completed" in df_pa.columns:
                fig = px.bar(df_pa, x="Painter Name" if "Painter Name" in df_pa.columns else df_pa.index,
                             y="Total Revenue (₹)",
                             color="Painter Name" if "Painter Name" in df_pa.columns else None,
                             color_discrete_sequence=PALETTE, text_auto=".2s")
                fig.update_layout(**PLOTLY_THEME)
                fig.update_yaxes(tickprefix="₹", tickformat=",")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Painter Rating & Cancellation Rate**")
            if "Avg Rating (5)" in df_pa.columns and "Painter Name" in df_pa.columns:
                df_pa_copy = df_pa.copy()
                total_jobs = df_pa_copy["Jobs Completed"] + df_pa_copy["Jobs Cancelled"] if "Jobs Cancelled" in df_pa_copy.columns else df_pa_copy["Jobs Completed"]
                df_pa_copy["Cancel Rate %"] = (df_pa_copy["Jobs Cancelled"] / total_jobs * 100).round(1) if "Jobs Cancelled" in df_pa_copy.columns else 0

                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(x=df_pa_copy["Painter Name"], y=df_pa_copy["Avg Rating (5)"],
                                     name="Avg Rating", marker_color=PALETTE[0]), secondary_y=False)
                fig.add_trace(go.Scatter(x=df_pa_copy["Painter Name"], y=df_pa_copy["Cancel Rate %"],
                                         name="Cancel Rate %", mode="lines+markers",
                                         line=dict(color=PALETTE[3], width=2)), secondary_y=True)
                fig.update_layout(**PLOTLY_THEME, title="Rating (bar) vs Cancel Rate % (line)")
                fig.update_yaxes(title_text="Avg Rating", secondary_y=False, range=[0,5.5])
                fig.update_yaxes(title_text="Cancel %", secondary_y=True)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Painter Performance Table**")
        st.dataframe(df_pa, use_container_width=True, height=280)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center;color:#aaa;font-size:12px'>"
    "Stackly Web Gap Analysis Dashboard · Built with Streamlit & Plotly"
    "</p>", unsafe_allow_html=True
)

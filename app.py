import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# Set page configuration
# Trigger redeploy: 2026-06-10
st.set_page_config(
    page_title="HbA1c Landscape • EVINAHTA",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Styling
CSS_STRING = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Global overrides */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: #0B1120 !important;
    color: #F1F5F9 !important;
}
[data-testid="stSidebar"] {
    background-color: #0D1829 !important;
    border-right: 1px solid #1E3A5F !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem !important; }

/* Custom Cards */
.metric-card {
    background: #131F35;
    border: 1px solid #1E3A5F;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    transition: border-color 0.2s;
    margin-bottom: 1rem;
}
.metric-card:hover { border-color: #00C2FF44; }
.metric-value {
    font-size: 2.0rem;
    font-weight: 700;
    color: #00C2FF;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}
.metric-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.35rem;
}
.metric-sub {
    font-size: 0.8rem;
    color: #475569;
    margin-top: 0.2rem;
}

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    color: #00C2FF;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    border-bottom: 1px solid #1E3A5F;
    padding-bottom: 0.5rem;
    margin-bottom: 1.25rem;
}

/* Device tag pills */
.tag-ce { background:#10B98120; color:#10B981; border:1px solid #10B98140; 
          border-radius:4px; padding:2px 8px; font-size:0.72rem; font-weight:500; }
.tag-fda { background:#00C2FF20; color:#00C2FF; border:1px solid #00C2FF40;
           border-radius:4px; padding:2px 8px; font-size:0.72rem; font-weight:500; }
.tag-clia { background:#8B5CF620; color:#8B5CF6; border:1px solid #8B5CF640;
            border-radius:4px; padding:2px 8px; font-size:0.72rem; font-weight:500; }

/* Device fingerprint label */
.fingerprint-label {
    font-size: 0.68rem;
    color: #94A3B8;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
}

/* Dataframe overrides */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
"""
st.markdown(CSS_STRING, unsafe_allow_html=True)

# Load data
from data_loader import load_hba1c_data
df, avail_cols = load_hba1c_data("data/HbA1c_Data_for_Dashboard.xlsx")

# Plotly styling config
PLOTLY_THEME = dict(
    paper_bgcolor="#131F35",
    plot_bgcolor="#0B1120",
    font=dict(family="Inter", color="#F1F5F9"),
    title_font=dict(family="Inter", size=14, color="#F1F5F9"),
    colorway=["#00C2FF","#10B981","#8B5CF6","#F59E0B","#EF4444","#06B6D4","#F97316"],
    xaxis=dict(gridcolor="#1E3A5F", linecolor="#1E3A5F", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#1E3A5F", linecolor="#1E3A5F", tickfont=dict(size=11)),
    margin=dict(l=40, r=20, t=50, b=40),
)

def apply_theme(fig):
    fig.update_layout(**PLOTLY_THEME)
    return fig

# Helper to render HTML card
def render_metric_card(label, value, sub=None, border_left=False):
    border_style = "border-left: 3px solid #00C2FF;" if border_left else ""
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ''
    return f"""
    <div class="metric-card" style="{border_style}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {sub_html}
    </div>
    """

# Sidebar Navigation and Filters
with st.sidebar:
    st.markdown("""
    <div style="padding:0.5rem 0 1.5rem 0">
      <div style="font-size:0.65rem;color:#00C2FF;letter-spacing:0.15em;text-transform:uppercase;font-weight:600">
        EVINAHTA • HTA INTELLIGENCE
      </div>
      <div style="font-size:1.3rem;font-weight:700;color:#F1F5F9;line-height:1.2;margin-top:0.3rem">
        HbA1c Analyzer<br>Landscape
      </div>
      <div style="font-size:0.72rem;color:#475569;margin-top:0.3rem">
        52 devices • 2 categories
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigate",
        ["📊   Overview", "🔍   Device Explorer", 
         "⚡   Compare Devices", "🌏   Market & Pricing",
         "🔬   Technical Analysis"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown('<div class="section-header">FILTERS</div>', unsafe_allow_html=True)
    
    # Global filters
    filter_sheet = st.multiselect(
        "Category", ["HbA1c Only", "Multi-Parameter"], 
        default=["HbA1c Only", "Multi-Parameter"]
    )
    filter_ce = st.toggle("CE-IVD only", value=False)
    filter_fda = st.toggle("FDA cleared only", value=False)
    
    available_methods = sorted(df["method_category"].dropna().unique().tolist())
    filter_method = st.multiselect(
        "Method", available_methods, default=[]
    )
    
    available_forms = sorted(df["form_factor"].dropna().unique().tolist())
    filter_form = st.multiselect(
        "Form Factor", available_forms, default=[]
    )
    
    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:0.68rem;color:#475569;line-height:1.6">
      Data: HbA1c reference dataset<br>
      Source: EVINAHTA internal<br>
      Updated: 2026
    </div>
    """, unsafe_allow_html=True)

# Apply global filters to get df_filtered
df_filtered = df.copy()
if filter_sheet:
    df_filtered = df_filtered[df_filtered["_sheet"].isin(filter_sheet)]
if filter_ce:
    df_filtered = df_filtered[df_filtered["has_CE"] == True]
if filter_fda:
    df_filtered = df_filtered[df_filtered["has_FDA"] == True]
if filter_method:
    df_filtered = df_filtered[df_filtered["method_category"].isin(filter_method)]
if filter_form:
    df_filtered = df_filtered[df_filtered["form_factor"].isin(filter_form)]

# ----------------- PAGE 1: OVERVIEW -----------------
def render_overview(df_filtered):
    st.markdown("### Executive Landscape Overview")
    
    if df_filtered.empty:
        st.warning("No devices match the selected filters.")
        return
        
    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(df_filtered)
    ce_count = df_filtered["has_CE"].sum()
    fda_count = df_filtered["has_FDA"].sum()
    
    ce_pct = (ce_count / total * 100) if total > 0 else 0
    fda_pct = (fda_count / total * 100) if total > 0 else 0
    
    avg_duration = df_filtered["duration_min_num"].mean()
    avg_volume = df_filtered["volume_ul_num"].mean()
    
    col1.markdown(render_metric_card("Total Devices", f"{total}", "Discovered landscape"), unsafe_allow_html=True)
    col2.markdown(render_metric_card("CE-IVD Certified", f"{ce_count}", f"{ce_pct:.1f}% of filtered"), unsafe_allow_html=True)
    col3.markdown(render_metric_card("FDA Cleared", f"{fda_count}", f"{fda_pct:.1f}% of filtered"), unsafe_allow_html=True)
    
    dur_str = f"{avg_duration:.1f} min" if not pd.isna(avg_duration) else "N/A"
    col4.markdown(render_metric_card("Avg Test Duration", dur_str, "Minutes per assay"), unsafe_allow_html=True)
    
    vol_str = f"{avg_volume:.1f} µL" if not pd.isna(avg_volume) else "N/A"
    col5.markdown(render_metric_card("Avg Sample Vol", vol_str, "Microliter requirement"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Chart Row 1
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Chart A: Method Distribution
        method_counts = df_filtered["method_category"].value_counts().reset_index(name="count")
        fig_a = px.pie(
            method_counts, values="count", names="method_category",
            hole=0.6,
            title="Measurement Methods"
        )
        fig_a.update_traces(
            textposition="outside",
            textinfo="percent+label",
            marker=dict(line=dict(color="#0B1120", width=2))
        )
        fig_a.add_annotation(
            text=f"{total}<br>DEVICES",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=18, family="Inter", color="#F1F5F9", weight="bold")
        )
        apply_theme(fig_a)
        st.plotly_chart(fig_a, use_container_width=True)
        
    with col_b:
        # Chart B: Certification Landscape
        cert_sums = {
            "CE-IVD": df_filtered["has_CE"].sum(),
            "FDA": df_filtered["has_FDA"].sum(),
            "CLIA": df_filtered["has_CLIA"].sum(),
            "ISO 13485": df_filtered["has_ISO"].sum(),
            "NMPA": df_filtered["has_NMPA"].sum(),
            "CDSCO": df_filtered["has_CDSCO"].sum(),
            "JDS": df_filtered["has_JDS"].sum(),
        }
        cert_df = pd.DataFrame(list(cert_sums.items()), columns=["Certification", "Count"])
        fig_b = px.bar(
            cert_df, x="Certification", y="Count",
            title="Certification Landscape",
            text="Count"
        )
        fig_b.update_traces(textposition="outside", marker_color="#00C2FF")
        apply_theme(fig_b)
        st.plotly_chart(fig_b, use_container_width=True)
        
    # Chart Row 2
    col_c, col_d = st.columns(2)
    
    with col_c:
        # Chart C: Form Factor Split
        form_counts = df_filtered["form_factor"].value_counts().reset_index(name="count")
        fig_c = px.bar(
            form_counts, y="form_factor", x="count",
            orientation="h",
            color="form_factor",
            title="Form Factor Split"
        )
        apply_theme(fig_c)
        st.plotly_chart(fig_c, use_container_width=True)
        
    with col_d:
        # Chart D: Device Weight Distribution
        fig_d = go.Figure()
        fig_d.add_trace(go.Box(
            y=df_filtered["weight_kg_num"].dropna(),
            name="Weight (kg)",
            marker_color="#00C2FF",
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            line_color="#00C2FF"
        ))
        fig_d.update_layout(title="Device Weight Distribution")
        apply_theme(fig_d)
        st.plotly_chart(fig_d, use_container_width=True)
        
    st.markdown("---")
    st.markdown('<div class="section-header">DATA INSIGHT CALLOUTS</div>', unsafe_allow_html=True)
    
    # Bottom Row: Insight Callouts
    col_i1, col_i2, col_i3 = st.columns(3)
    
    # Lightest device
    df_weight = df_filtered[df_filtered["weight_kg_num"].notna()]
    if not df_weight.empty:
        idx_light = df_weight["weight_kg_num"].idxmin()
        light = df_weight.loc[idx_light]
        light_txt = f"{light['Product Name']} at {light['weight_kg_num']:.2f} kg ({light.get('Manufacturer', 'Unknown')})"
    else:
        light_txt = "No weight data available"
        
    # Fastest test
    df_dur = df_filtered[df_filtered["duration_min_num"].notna()]
    if not df_dur.empty:
        idx_fast = df_dur["duration_min_num"].idxmin()
        fast = df_dur.loc[idx_fast]
        fast_txt = f"{fast['Product Name']} at {fast['duration_min_num']:.1f} min ({fast.get('method_category', 'Unknown')})"
    else:
        fast_txt = "No duration data available"
        
    # Smallest volume
    df_vol = df_filtered[df_filtered["volume_ul_num"].notna()]
    if not df_vol.empty:
        idx_vol = df_vol["volume_ul_num"].idxmin()
        vol = df_vol.loc[idx_vol]
        vol_txt = f"{vol['Product Name']} needs only {vol['volume_ul_num']:.1f} µL sample"
    else:
        vol_txt = "No volume data available"
        
    col_i1.markdown(render_metric_card("LIGHTEST DEVICE", light_txt, "Min weight profile", border_left=True), unsafe_allow_html=True)
    col_i2.markdown(render_metric_card("FASTEST ASSAY", fast_txt, "Min wait duration", border_left=True), unsafe_allow_html=True)
    col_i3.markdown(render_metric_card("SMALLEST VOLUME", vol_txt, "Min sample size", border_left=True), unsafe_allow_html=True)

# ----------------- PAGE 2: DEVICE EXPLORER -----------------
def render_explorer(df_filtered):
    st.markdown("### Interactive Device Explorer")
    
    if df_filtered.empty:
        st.warning("No devices match the selected filters.")
        return
        
    # Search bar
    search = st.text_input("🔍 Search devices, manufacturers, methods...", 
                           placeholder="e.g. EKF, boronate, handheld...")
    
    # Filter columns/sort row
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_col = st.selectbox("Sort by", ["Product Name", "Manufacturer", "Duration", "Volume", "Weight"])
    with col2:
        sort_dir = st.radio("Order", ["↑ Asc", "↓ Desc"], horizontal=True)
        
    # Filter dataset based on search
    df_search = df_filtered.copy()
    if search:
        search_lower = search.lower()
        df_search = df_search[
            df_search["Product Name"].astype(str).str.lower().str.contains(search_lower) |
            df_search["Manufacturer"].astype(str).str.lower().str.contains(search_lower) |
            df_search["method_category"].astype(str).str.lower().str.contains(search_lower) |
            df_search["form_factor"].astype(str).str.lower().str.contains(search_lower)
        ]
        
    # Sort dataset
    sort_mapping = {
        "Product Name": "Product Name",
        "Manufacturer": "Manufacturer",
        "Duration": "duration_min_num",
        "Volume": "volume_ul_num",
        "Weight": "weight_kg_num"
    }
    col_to_sort = sort_mapping[sort_col]
    ascending = (sort_dir == "↑ Asc")
    df_search = df_search.sort_values(by=col_to_sort, ascending=ascending, na_position="last")
    
    # Main table display
    display_cols = {
        "Product Name": st.column_config.TextColumn("Product Name", width="large"),
        "Manufacturer": st.column_config.TextColumn("Manufacturer", width="medium"),
        "method_category": st.column_config.TextColumn("Method", width="medium"),
        "volume_ul_num": st.column_config.NumberColumn("Vol (µL)", format="%.1f µL"),
        "duration_min_num": st.column_config.NumberColumn("Duration", format="%.1f min"),
        "weight_kg_num": st.column_config.NumberColumn("Weight", format="%.2f kg"),
        "form_factor": st.column_config.TextColumn("Form"),
        "has_CE": st.column_config.CheckboxColumn("CE-IVD"),
        "has_FDA": st.column_config.CheckboxColumn("FDA"),
        "_avail_count": st.column_config.ProgressColumn(
            "Availability", min_value=0, max_value=11, format="%d countries"
        ),
    }
    
    st.dataframe(
        df_search[list(display_cols.keys())],
        column_config=display_cols,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Device Detail Expander
    st.markdown("---")
    st.markdown("### Device Specification Detail")
    
    selected = st.selectbox("Select a device to view deep dive specs:", df_filtered["Product Name"].tolist())
    if selected:
        row = df_filtered[df_filtered["Product Name"] == selected].iloc[0]
        
        with st.expander(f"📋  {selected} — Full Specification Sheet", expanded=True):
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            
            def render_val(val):
                return str(val).strip() if pd.notna(val) else "Not Provided"
            
            with col_t1:
                st.markdown('<div class="section-header">TECHNICAL SPECS</div>', unsafe_allow_html=True)
                st.markdown(f"**Manufacturer**: {render_val(row.get('Manufacturer'))}")
                st.markdown(f"**Weight**: {render_val(row.get('Device weight in kg'))}")
                st.markdown(f"**Dimensions**: {render_val(row.get('Dimensions in mm'))}")
                st.markdown(f"**Power**: {render_val(row.get('Power'))}")
                st.markdown(f"**Display**: {render_val(row.get('Display'))}")
                
            with col_t2:
                st.markdown('<div class="section-header">PERFORMANCE SPECS</div>', unsafe_allow_html=True)
                st.markdown(f"**Precision (CV)**: {render_val(row.get('Precision'))}")
                st.markdown(f"**Reference Range**: {render_val(row.get('Reference Range'))}")
                st.markdown(f"**Limitation**: {render_val(row.get('Limitation'))}")
                st.markdown(f"**Interference**: {render_val(row.get('Interference'))}")
                
            with col_t3:
                st.markdown('<div class="section-header">PROCEDURE SPECS</div>', unsafe_allow_html=True)
                st.markdown(f"**Sample Type**: {render_val(row.get('Type of Sample'))}")
                st.markdown(f"**Volume Requirement**: {render_val(row.get('Volume'))}")
                st.markdown(f"**Duration**: {render_val(row.get('Duration'))}")
                st.markdown(f"**Sample Prep**: {render_val(row.get('Sample Prep'))}")
                st.markdown(f"**Handling**: {render_val(row.get('Handling'))}")
                
            with col_t4:
                st.markdown('<div class="section-header">MARKET & REGULATORY</div>', unsafe_allow_html=True)
                st.markdown(f"**SRA Approvals**: {render_val(row.get('SRA Approvals'))}")
                st.markdown(f"**Certifications**: {render_val(row.get('Certifications'))}")
                st.markdown(f"**Control**: {render_val(row.get('Control'))}")
                st.markdown(f"**Calibration**: {render_val(row.get('Calibration'))}")
                st.markdown(f"**Sheet Source**: {render_val(row.get('_sheet'))}")

# ----------------- PAGE 3: COMPARE DEVICES -----------------
def render_compare(df_filtered):
    st.markdown("### Device Fingerprint & Comparison")
    
    if len(df_filtered) < 2:
        st.warning("Please adjust filters to show at least 2 devices for comparison.")
        return
        
    st.caption("Select up to 4 devices to compare their normalized performance profile")
    
    compare_devices = st.multiselect(
        "Select devices to compare", 
        df_filtered["Product Name"].tolist(),
        max_selections=4,
        default=df_filtered["Product Name"].tolist()[:3]
    )
    
    if not compare_devices:
        st.info("Select devices above to render comparison analysis.")
        return
        
    compare_df = df_filtered[df_filtered["Product Name"].isin(compare_devices)].copy()
    
    # 1. Radar Chart / Fingerprint
    def normalize(val, min_val, max_val):
        if pd.isna(val):
            return 0.0
        val = max(min(val, max_val), min_val)
        return (val - min_val) / (max_val - min_val)

    def cert_score(row):
        score = 0
        if row.get("has_CE"): score += 1
        if row.get("has_FDA"): score += 1
        if row.get("has_CLIA"): score += 1
        if row.get("has_ISO"): score += 1
        return score

    RADAR_AXES = {
        "Speed": lambda r: 1 - normalize(r["duration_min_num"], 1, 15),  # lower = better
        "Efficiency": lambda r: 1 - normalize(r["volume_ul_num"], 1, 20), # lower = better  
        "Portability": lambda r: 1 - normalize(r["weight_kg_num"], 0.05, 12), # lower = better
        "Certifications": lambda r: normalize(cert_score(r), 0, 4),  # CE+FDA+CLIA+ISO
        "Precision": lambda r: 1 - normalize(r["precision_num"], 1, 8), # lower CV = better
        "Multi-use": lambda r: 1.0 if r["_sheet"] == "Multi-Parameter" else 0.3,
    }
    
    fig = go.Figure()
    for device in compare_devices:
        rows_matched = compare_df[compare_df["Product Name"] == device]
        if rows_matched.empty:
            continue
        row = rows_matched.iloc[0]
        
        scores = []
        for axis_name, score_fn in RADAR_AXES.items():
            scores.append(score_fn(row))
        scores.append(scores[0])  # close polygon
        
        axes_labels = list(RADAR_AXES.keys()) + [list(RADAR_AXES.keys())[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=scores, theta=axes_labels,
            fill="toself", opacity=0.25,
            name=device[:30],
            line=dict(width=2)
        ))
        
    fig.update_layout(
        **PLOTLY_THEME,
        polar=dict(
            bgcolor="#0B1120",
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=9),
                            gridcolor="#1E3A5F", linecolor="#1E3A5F"),
            angularaxis=dict(gridcolor="#1E3A5F", linecolor="#1E3A5F",
                             tickfont=dict(size=11, color="#94A3B8"))
        ),
        showlegend=True,
        height=480,
        title="Device Performance Fingerprint"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 2. Side-by-Side Spec Comparison Table
    st.markdown("### Side-by-Side Attribute Comparison")
    st.caption("Highlights the best value in each row in green (for numerical metrics where lower is better)")
    
    COMPARE_FIELDS = [
        ("Sample Volume", "volume_ul_num", " µL", "lower"),
        ("Test Duration", "duration_min_num", " min", "lower"),
        ("Weight", "weight_kg_num", " kg", "lower"),
        ("Precision (CV%)", "precision_num", "%", "lower"),
        ("Method", "method_category", "", None),
        ("Form Factor", "form_factor", "", None),
        ("CE-IVD", "has_CE", "", None),
        ("FDA", "has_FDA", "", None),
    ]
    
    # Build HTML table
    headers = ["Field"] + compare_df["Product Name"].tolist()
    html = '<table style="width:100%; border-collapse: collapse; margin-top:1.5rem; background-color:#131F35; border:1px solid #1E3A5F; border-radius:8px; overflow:hidden;">'
    
    # Header row
    html += '<tr style="border-bottom: 2px solid #1E3A5F; background-color: #0D1829;">'
    for h in headers:
        html += f'<th style="padding:12px; text-align:left; color:#00C2FF; font-size:0.85rem; font-weight:600; font-family:\'Inter\', sans-serif;">{h}</th>'
    html += '</tr>'
    
    for label, col_name, unit, direction in COMPARE_FIELDS:
        html += '<tr style="border-bottom: 1px solid #1E3A5F;">'
        html += f'<td style="padding:10px 12px; color:#94A3B8; font-size:0.8rem; font-weight:500; font-family:\'Inter\', sans-serif; background-color:#0D1829; width:20%;">{label}</td>'
        
        # Calculate best value if direction is lower
        best_idx = None
        if direction == "lower":
            vals = compare_df[col_name].tolist()
            valid_vals = [(i, v) for i, v in enumerate(vals) if pd.notna(v)]
            if valid_vals:
                best_idx = min(valid_vals, key=lambda x: x[1])[0]
                
        for idx, (_, row) in enumerate(compare_df.iterrows()):
            val = row.get(col_name)
            if pd.isna(val):
                val_str = "N/A"
            elif isinstance(val, bool):
                val_str = "🟢 Yes" if val else "🔴 No"
            elif isinstance(val, (int, float)):
                val_str = f"{val:.2f}{unit}" if isinstance(val, float) else f"{val}{unit}"
            else:
                val_str = str(val)
                
            style = ""
            if idx == best_idx:
                style = "color: #10B981; font-weight: 700; background-color: #10B98115;"
            else:
                style = "color: #F1F5F9;"
                
            html += f'<td style="padding:10px 12px; font-size:0.8rem; font-family:\'Inter\', sans-serif; {style}">{val_str}</td>'
        html += '</tr>'
        
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)

# ----------------- PAGE 4: MARKET & PRICING -----------------
def render_market(df_filtered):
    st.markdown("### Market Penetration & Pricing Analytics")
    
    if df_filtered.empty:
        st.warning("No devices match the selected filters.")
        return
        
    # Availability Heatmap
    st.markdown("#### Country Availability Mapping")
    country_cols = [c for c in df_filtered.columns if any(
        country in str(c) for country in 
        ["Bangladesh","Bhutan","Korea","India","Indonesia","Maldives",
         "Myanmar","Nepal","Sri","Thailand","Timor"]
    )]
    
    if country_cols:
        avail_matrix = df_filtered[["Product Name"] + country_cols].copy()
        # Binarize
        for col in country_cols:
            avail_matrix[col] = avail_matrix[col].apply(
                lambda x: 1 if str(x).strip().lower() not in ["na","nan","","none"] else 0
            )
            
        fig_heatmap = px.imshow(
            avail_matrix.set_index("Product Name")[country_cols],
            color_continuous_scale=[[0, "#131F35"], [1, "#10B981"]],
            title="Market Availability Matrix (Green = Available)",
            aspect="auto"
        )
        fig_heatmap.update_xaxes(tickangle=45)
        fig_heatmap.update_coloraxes(showscale=False)
        apply_theme(fig_heatmap)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("No country availability columns found in the data.")
        
    # Pricing Charts Row
    st.markdown("<br>", unsafe_allow_html=True)
    col_p1, col_p2 = st.columns(2)
    
    df_priced = df_filtered[df_filtered["cost_usd_num"].notna()]
    
    with col_p1:
        if not df_priced.empty:
            fig_scatter = px.scatter(
                df_priced,
                x="duration_min_num",
                y="cost_usd_num",
                color="method_category",
                size="volume_ul_num",
                hover_name="Product Name",
                hover_data=["Manufacturer", "has_CE", "has_FDA"],
                title="Price vs Speed (bubble size = sample volume)",
                labels={"duration_min_num": "Test Duration (min)",
                        "cost_usd_num": "Price (USD)",
                        "method_category": "Method"}
            )
            apply_theme(fig_scatter)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("No pricing data available for scatter analysis.")
            
    with col_p2:
        if not df_priced.empty:
            fig_bar = px.bar(
                df_priced.sort_values("cost_usd_num"),
                y="Product Name",
                x="cost_usd_num",
                orientation="h",
                color="cost_usd_num",
                color_continuous_scale=[[0, "#10B981"], [0.5, "#F59E0B"], [1, "#EF4444"]],
                title="Device Price Ranking (USD)",
                text="cost_usd_num"
            )
            fig_bar.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            apply_theme(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No pricing data available for price ranking.")
            
    # Pricing KPIs Row
    st.markdown("---")
    st.markdown('<div class="section-header">MARKET & COST KEY METRICS</div>', unsafe_allow_html=True)
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    if not df_priced.empty:
        count_priced = len(df_priced)
        min_p = df_priced["cost_usd_num"].min()
        max_p = df_priced["cost_usd_num"].max()
        range_str = f"${min_p:,.0f} - ${max_p:,.0f}"
        median_p = df_priced["cost_usd_num"].median()
        median_str = f"${median_p:,.0f}"
    else:
        count_priced = 0
        range_str = "N/A"
        median_str = "N/A"
        
    if not df_filtered.empty:
        idx_max = df_filtered["_avail_count"].idxmax()
        best = df_filtered.loc[idx_max]
        avail_str = f"{best['Product Name']} ({best['_avail_count']} countries)"
    else:
        avail_str = "N/A"
        
    col_k1.markdown(render_metric_card("Devices with Pricing", f"{count_priced}", "Known USD cost"), unsafe_allow_html=True)
    col_k2.markdown(render_metric_card("Price Range", range_str, "Min to Max cost"), unsafe_allow_html=True)
    col_k3.markdown(render_metric_card("Median Price", median_str, "50th percentile cost"), unsafe_allow_html=True)
    col_k4.markdown(render_metric_card("Most Distributed", avail_str, "Max availability count"), unsafe_allow_html=True)

# ----------------- PAGE 5: TECHNICAL ANALYSIS -----------------
def render_technical(df_filtered):
    st.markdown("### Technical & Performance Deep-Dive")
    
    if df_filtered.empty:
        st.warning("No devices match the selected filters.")
        return
        
    # Performance Quadrant Row
    st.markdown("#### Performance Quadrant (Speed vs Sample Efficiency)")
    df_perf = df_filtered.dropna(subset=["volume_ul_num", "duration_min_num"])
    
    if not df_perf.empty:
        median_dur = df_filtered["duration_min_num"].median()
        median_vol = df_filtered["volume_ul_num"].median()
        
        fig_quad = px.scatter(
            df_perf,
            x="duration_min_num",
            y="volume_ul_num",
            color="method_category",
            symbol="form_factor",
            size="weight_kg_num",
            hover_name="Product Name",
            hover_data=["Manufacturer", "precision_num", "has_CE", "has_FDA"],
            title="Performance Quadrant: Speed vs Minimal Sample Requirement",
            labels={"duration_min_num": "Test Duration (min) ← Faster",
                    "volume_ul_num": "Sample Volume (µL) ← Less invasive",
                    "method_category": "Method"}
        )
        
        fig_quad.add_hline(y=median_vol, line_dash="dot", line_color="#1E3A5F", 
                          annotation_text="Median volume", annotation_font_color="#475569")
        fig_quad.add_vline(x=median_dur, line_dash="dot", line_color="#1E3A5F",
                          annotation_text="Median duration", annotation_font_color="#475569")
        
        fig_quad.add_annotation(x=0.05, y=0.05, xref="paper", yref="paper",
            text="✦ IDEAL", showarrow=False, 
            font=dict(color="#10B981", size=14, weight="bold"))
            
        apply_theme(fig_quad)
        st.plotly_chart(fig_quad, use_container_width=True)
    else:
        st.info("No volume or duration data available for performance quadrant.")
        
    # Precision violin plot row
    st.markdown("<br>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        df_prec = df_filtered.dropna(subset=["precision_num"])
        if not df_prec.empty:
            fig_prec = px.violin(
                df_prec,
                y="precision_num",
                x="method_category",
                color="method_category",
                box=True,
                points="all",
                hover_name="Product Name",
                title="Precision Distribution by Method (CV%)",
                labels={"precision_num": "CV%", "method_category": "Method"}
            )
            apply_theme(fig_prec)
            st.plotly_chart(fig_prec, use_container_width=True)
        else:
            st.info("No precision (CV%) data available for violin plot.")
            
    # Operating temperature Gantt row
    with col_t2:
        def parse_temp_range(s):
            if pd.isna(s):
                return None, None
            matches = re.findall(r'(\d+)', str(s))
            if len(matches) >= 2:
                return int(matches[0]), int(matches[1])
            return None, None

        temp_data = []
        t_col = "Operating temperature" if "Operating temperature" in df_filtered.columns else None
        if t_col:
            for _, row in df_filtered.iterrows():
                lo, hi = parse_temp_range(row.get(t_col))
                if lo is not None and hi is not None:
                    temp_data.append({
                        "device": row["Product Name"][:25],
                        "low": lo,
                        "high": hi,
                        "range": hi - lo,
                        "method": row.get("method_category", "Other"),
                        "manufacturer": row.get("Manufacturer", "Unknown")
                    })
        if temp_data:
            temp_df = pd.DataFrame(temp_data).sort_values("low")
            fig_temp = px.bar(
                temp_df, x="range", y="device",
                base="low", orientation="h",
                color="method",
                title="Operating Temperature Range by Device (°C)",
                labels={"range": "Temp Range (°C)", "device": "Device", "low": "Min Temp °C"}
            )
            apply_theme(fig_temp)
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("No operating temperature range data available.")
            
    # Memory Capacity Row
    st.markdown("<br>", unsafe_allow_html=True)
    
    def parse_memory_value(s):
        if pd.isna(s):
            return None
        matches = re.findall(r'(\d+)', str(s).replace(",", "").replace(" ", ""))
        if matches:
            return int(matches[0])
        return None

    memory_rows = []
    mem_col = "Memory" if "Memory" in df_filtered.columns else None
    if mem_col:
        for _, row in df_filtered.iterrows():
            val_mem = parse_memory_value(row.get(mem_col))
            if val_mem is not None:
                memory_rows.append({
                    "device": row["Product Name"][:25],
                    "memory_count": val_mem,
                    "manufacturer": row.get("Manufacturer", "Unknown")
                })
    if memory_rows:
        memory_df = pd.DataFrame(memory_rows)
        fig_mem = px.bar(
            memory_df.sort_values("memory_count", ascending=True).tail(20),
            x="memory_count", y="device",
            orientation="h",
            color="memory_count",
            color_continuous_scale=[[0, "#1A2B45"], [1, "#00C2FF"]],
            title="Device Memory Capacity (stored results — Top 20)",
            labels={"memory_count": "Stored Results", "device": "Device"}
        )
        apply_theme(fig_mem)
        st.plotly_chart(fig_mem, use_container_width=True)
    else:
        st.info("No memory capacity data available for bar chart.")

# Route Page to render the correct view
if "Overview" in page:
    render_overview(df_filtered)
elif "Explorer" in page:
    render_explorer(df_filtered)
elif "Compare" in page:
    render_compare(df_filtered)
elif "Market" in page:
    render_market(df_filtered)
elif "Technical" in page:
    render_technical(df_filtered)

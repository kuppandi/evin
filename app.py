import streamlit as st
import pandas as pd
import os
import io

st.set_page_config(page_title="Medical Device Intelligence", layout="wide", page_icon="🧬")

st.title("Medical Device Market Intelligence Dashboard")
st.markdown("Automated insights from FDA, EUDAMED, PubMed, and Web extraction.")

@st.cache_data
def load_data(file):
    try:
        # Read the main sheet
        df_data = pd.read_excel(file, sheet_name="Device Data", header=0)
        # Read the hidden scores sheet
        df_scores = pd.read_excel(file, sheet_name="Confidence Scores", header=0)
        
        # Remove the last summary row if it starts with 'TOTALS:'
        if df_data.iloc[-1].astype(str).str.contains('TOTALS:').any():
            df_data = df_data.iloc[:-1]
            df_scores = df_scores.iloc[:-1]
            
        return df_data, df_scores
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None, None

def get_color(score):
    if pd.isna(score) or score == 0:
        return "#FF4444"
    elif score < 40:
        return "#FF8888"
    elif score < 75:
        return "#FFD700"
    return "transparent"

# 1. FILE LOADER
st.sidebar.header("1. File Loader")
uploaded_file = st.sidebar.file_uploader("Upload Pipeline Output Excel", type=["xlsx"])

if not uploaded_file:
    # Look for files in output dir
    output_dir = "./output/"
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith(".xlsx")]
        if files:
            selected_file = st.sidebar.selectbox("Or select an existing file:", [""] + files)
            if selected_file:
                uploaded_file = os.path.join(output_dir, selected_file)

if uploaded_file:
    df, df_scores = load_data(uploaded_file)
    
    if df is not None and df_scores is not None:
        
        # 2. OVERVIEW
        st.header("2. Overview")
        col1, col2, col3 = st.columns(3)
        
        total_devices = len(df)
        flag_counts = df['Manual_Review_Flag'].value_counts()
        
        col1.metric("Total Devices Discovered", total_devices)
        col2.metric("Requires Manual Review", flag_counts.get('YES', 0))
        col3.metric("Ready to Use", flag_counts.get('OK', 0))
        
        # High/Med/Low distribution
        scores_flat = df_scores.drop(columns=["S.No", "Product Name", "Manufacturer", "Manual_Review_Flag"]).values.flatten()
        scores_flat = pd.Series(scores_flat)
        high = len(scores_flat[scores_flat >= 75])
        med = len(scores_flat[(scores_flat >= 40) & (scores_flat < 75)])
        low = len(scores_flat[scores_flat < 40])
        
        # Simple st.bar_chart or pie if we had plotly, but we only have streamlit built-ins
        chart_data = pd.DataFrame({"Count": [high, med, low]}, index=["High (>=75)", "Medium (40-74)", "Low/Missing (<40)"])
        st.bar_chart(chart_data)
        
        st.subheader("Devices Needing Attention")
        attention_df = df[df['Manual_Review_Flag'] != 'OK'].copy()
        st.dataframe(attention_df[["Product Name", "Manufacturer", "Manual_Review_Flag"]])
        
        # 3. DEVICE EXPLORER
        st.header("3. Device Explorer")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            ce_filter = st.selectbox("CE IVD Status", ["All", "Yes", "No/Unknown"])
        with col_f2:
            fda_filter = st.selectbox("FDA Clearance", ["All", "Yes", "No/Unknown"])
            
        filtered_df = df.copy()
        if ce_filter == "Yes":
            filtered_df = filtered_df[filtered_df['CE_IVD'] == "Yes"]
        elif ce_filter == "No/Unknown":
            filtered_df = filtered_df[filtered_df['CE_IVD'] != "Yes"]
            
        if fda_filter == "Yes":
            filtered_df = filtered_df[filtered_df['FDA_Clearance'] == "Yes"]
        elif fda_filter == "No/Unknown":
            filtered_df = filtered_df[filtered_df['FDA_Clearance'] != "Yes"]
            
        st.dataframe(filtered_df)
        
        # Expand details
        st.markdown("### Selected Device Details")
        selected_device = st.selectbox("Select a device to view deep dive:", filtered_df['Product Name'].tolist())
        
        if selected_device:
            idx = df[df['Product Name'] == selected_device].index[0]
            dev_data = df.iloc[idx]
            dev_scores = df_scores.iloc[idx]
            
            st.markdown(f"#### {dev_data['Product Name']} ({dev_data['Manufacturer']})")
            
            # Display fields with confidence badges
            cols = st.columns(4)
            for i, col in enumerate(df.columns[3:-2]): # Skip basic info and flag/studies
                val = dev_data[col]
                score = dev_scores[col]
                bg_color = get_color(score)
                badge = ""
                if score < 40:
                    badge = "🔴"
                elif score < 75:
                    badge = "🟡"
                else:
                    badge = "🟢"
                    
                cols[i % 4].markdown(f"**{col}**<br/><span style='background-color: {bg_color}; padding: 2px 5px; border-radius: 4px; color: black;'>{val if pd.notna(val) else 'N/A'} {badge} ({score})</span>", unsafe_allow_html=True)
                
            # 4. EVIDENCE PANEL
            st.header("4. Evidence Panel")
            st.info(f"Top Studies Found: {dev_data['PubMed_Evidence_Count']}")
            studies = str(dev_data['PubMed_Top_Studies'])
            if studies and studies.lower() != 'nan':
                for study in studies.split('\n'):
                    st.markdown(f"- {study}")
            else:
                st.write("No studies extracted.")
                
        # 5. MANUAL REVIEW QUEUE
        st.header("5. Manual Review Queue")
        st.write("Fields across all devices that scored < 40 (Requires Manual Research)")
        
        review_queue = []
        for idx, row in df.iterrows():
            scores_row = df_scores.iloc[idx]
            for col in df.columns[3:-1]:
                sc = scores_row[col]
                if pd.notna(sc) and sc < 40:
                    review_queue.append({
                        "Product Name": row["Product Name"],
                        "Manufacturer": row["Manufacturer"],
                        "Field Missing/Low Confidence": col,
                        "Current Value": row[col],
                        "Score": sc
                    })
                    
        review_df = pd.DataFrame(review_queue)
        st.dataframe(review_df)
        
        # Export
        if not review_df.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                review_df.to_excel(writer, index=False)
            st.download_button(
                label="📥 Download Manual Review Queue (Excel)",
                data=buffer.getvalue(),
                file_name="manual_review_queue.xlsx",
                mime="application/vnd.ms-excel"
            )
else:
    st.info("👈 Please upload an Excel file or select one from the output directory to begin.")

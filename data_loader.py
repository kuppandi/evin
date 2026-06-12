import pandas as pd
import re

def load_hba1c_data(filepath: str):
    """Load and merge both device sheets into one clean DataFrame."""
    # Load sheet 1: "HbA1c only"
    df1_raw = pd.read_excel(filepath, sheet_name="HbA1c only", header=None)
    row0_1 = df1_raw.iloc[0].astype(str).str.strip()
    cost_usd_idx_1 = row0_1[row0_1.str.lower() == "cost (usd)"].index[0]
    
    df1 = pd.read_excel(filepath, sheet_name="HbA1c only", header=1)
    df1.rename(columns={df1.columns[0]: "S.no", df1.columns[1]: "Product Name", df1.columns[cost_usd_idx_1]: "Cost (USD)"}, inplace=True)
    
    # Load sheet 2: "Multiple tests"
    df2_raw = pd.read_excel(filepath, sheet_name="Multiple tests", header=None)
    row0_2 = df2_raw.iloc[0].astype(str).str.strip()
    cost_usd_idx_2 = row0_2[row0_2.str.lower() == "cost (usd)"].index[0]
    
    df2 = pd.read_excel(filepath, sheet_name="Multiple tests", header=1)
    df2.rename(columns={df2.columns[0]: "S.no", df2.columns[1]: "Product Name", df2.columns[cost_usd_idx_2]: "Cost (USD)"}, inplace=True)
    
    # Extract certifications BEFORE columns are normalized and concatenated
    def get_certs(df_sheet):
        cols = df_sheet.columns[3:min(16, len(df_sheet.columns))]
        ce = pd.Series(False, index=df_sheet.index)
        fda = pd.Series(False, index=df_sheet.index)
        clia = pd.Series(False, index=df_sheet.index)
        iso = pd.Series(False, index=df_sheet.index)
        nmpa = pd.Series(False, index=df_sheet.index)
        cdsco = pd.Series(False, index=df_sheet.index)
        jds = pd.Series(False, index=df_sheet.index)
        
        for c in cols:
            val = df_sheet[c].astype(str).str.strip().str.lower()
            ce |= val.str.contains(r"\bce\b|ce-ivd|ce ivd", regex=True, na=False)
            fda |= val.str.contains(r"\bfda\b", regex=True, na=False)
            clia |= val.str.contains(r"\bclia\b", regex=True, na=False)
            iso |= val.str.contains(r"\biso\b|13485", regex=True, na=False)
            nmpa |= val.str.contains(r"\bnmpa\b", regex=True, na=False)
            cdsco |= val.str.contains(r"\bcdsco\b", regex=True, na=False)
            jds |= val.str.contains(r"\bjds\b", regex=True, na=False)
        return ce, fda, clia, iso, nmpa, cdsco, jds

    ce1, fda1, clia1, iso1, nmpa1, cdsco1, jds1 = get_certs(df1)
    df1["has_CE"] = ce1
    df1["has_FDA"] = fda1
    df1["has_CLIA"] = clia1
    df1["has_ISO"] = iso1
    df1["has_NMPA"] = nmpa1
    df1["has_CDSCO"] = cdsco1
    df1["has_JDS"] = jds1

    ce2, fda2, clia2, iso2, nmpa2, cdsco2, jds2 = get_certs(df2)
    df2["has_CE"] = ce2
    df2["has_FDA"] = fda2
    df2["has_CLIA"] = clia2
    df2["has_ISO"] = iso2
    df2["has_NMPA"] = nmpa2
    df2["has_CDSCO"] = cdsco2
    df2["has_JDS"] = jds2

    # Extract methods dynamically from the Method section columns
    # For df1, look at cols 9, 10
    methods1 = df1.iloc[:, 9].fillna("").astype(str).str.strip()
    methods1_col10 = df1.iloc[:, 10].fillna("").astype(str).str.strip()
    df1["parsed_method"] = methods1.where(methods1 != "", methods1_col10)

    # For df2, look at cols 16, 17, 18, 19
    methods2 = pd.Series("", index=df2.index)
    for col_idx in [16, 17, 18, 19]:
        val = df2.iloc[:, col_idx].fillna("").astype(str).str.strip()
        methods2 = methods2.where(methods2 != "", val)
    df2["parsed_method"] = methods2

    # Normalize column names
    def clean_col(c):
        return str(c).strip().replace("\n", " ").replace("  ", " ")
    
    df1.columns = [clean_col(c) for c in df1.columns]
    df2.columns = [clean_col(c) for c in df2.columns]
    
    # Tag source sheet
    df1["_sheet"] = "HbA1c Only"
    df2["_sheet"] = "Multi-Parameter"
    
    # Align columns
    df = pd.concat([df1, df2], ignore_index=True, sort=False)
    
    # Drop completely empty rows
    df = df.dropna(how="all")
    df = df[df["Product Name"].notna() & (df["Product Name"].astype(str).str.strip() != "")]
    
    # Parse numeric fields
    def parse_numeric(series):
        return pd.to_numeric(
            series.astype(str).str.extract(r'([\d.]+)')[0], 
            errors='coerce'
        )
    
    df["weight_kg_num"] = parse_numeric(df.get("Device weight in kg", pd.Series()))
    df["volume_ul_num"] = parse_numeric(df.get("Volume", pd.Series()))
    df["duration_min_num"] = parse_numeric(df.get("Duration", pd.Series()))
    
    # Device form factor
    dd_col = "Device Design" if "Device Design" in df.columns else None
    if dd_col:
        df["form_factor"] = df[dd_col].astype(str).apply(
            lambda x: "Handheld" if "handheld" in x.lower() 
                      else "Benchtop" if "benchtop" in x.lower() 
                      else "Other"
        )
    
    # Parse method category
    def categorize_method(m):
        m = str(m).lower()
        if "boronate" in m: return "Boronate Affinity"
        if "immunoassay" in m and "fluor" in m: return "Fluorescent Immunoassay"
        if "immunoassay" in m: return "Immunoassay"
        if "enzymatic" in m: return "Enzymatic"
        if "hplc" in m: return "HPLC"
        if "non-inv" in m or "non inv" in m: return "Non-Invasive"
        return "Other"
    
    df["method_category"] = df["parsed_method"].apply(categorize_method)
    
    # Parse precision as float
    prec_col = "Precision" if "Precision" in df.columns else None
    if prec_col:
        df["precision_num"] = parse_numeric(df[prec_col])
    
    # Parse availability columns
    avail_cols = [c for c in df.columns if any(
        country in str(c) for country in 
        ["Bangladesh","Bhutan","Korea","India","Indonesia","Maldives",
         "Myanmar","Nepal","Sri","Thailand","Timor"]
    )]
    df["_avail_count"] = df[avail_cols].apply(
        lambda row: sum(
            str(v).strip().lower() not in ["na","nan","","none"] 
            for v in row
        ), axis=1
    ) if avail_cols else 0
    
    # Parse cost USD
    cost_cols = [c for c in df.columns if "cost" in str(c).lower() or "usd" in str(c).lower()]
    if cost_cols:
        df["cost_usd_num"] = parse_numeric(df[cost_cols[0]])
        
    return df, avail_cols

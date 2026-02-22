import pandas as pd
import re
import os

# --- CONFIGURATION ---
data_path = 'boem_data' # Folder where your DAT files are located

def numeric_only(val):
    """Removes 'G' prefixes and non-digit characters."""
    if pd.isna(val): return val
    return re.sub(r'\D', '', str(val)).strip()

def process_lease_data(path):
    # 1. Define Layouts (Columns & Widths)
    prebid_specs = [(0, 5), (6, 13), (15, 21), (24, 31), (32, 43), (52, 54), (63, 65)]
    prebid_names = ['Lease_Number', 'Protraction_ID', 'Block_Number', 'Acreage', 'Royalty_Rate', 'Lease_Term', 'Num_Bids']
    
    bid_specs = [(0, 7), (8, 15), (16, 26), (27, 32), (35, 43)]
    bid_names = ['Sale_Number', 'Lease_Number', 'Bid_Amount', 'Company_Number', 'Bid_Percentage']

    # 2. Load Files
    df_prebid = pd.read_fwf(os.path.join(path, 'PREBID.DAT'), colspecs=prebid_specs, names=prebid_names)
    df_bid = pd.read_fwf(os.path.join(path, 'BID.DAT'), colspecs=bid_specs, names=bid_names)

    # 3. Normalize Lease IDs (The "G" Fix)
    for df in [df_prebid, df_bid]:
        df['Lease_Number'] = df['Lease_Number'].apply(numeric_only).str.zfill(7)
        # Standardize other join keys
        if 'Protraction_ID' in df.columns:
            df['Protraction_ID'] = df['Protraction_ID'].astype(str).str.strip()
        if 'Company_Number' in df.columns:
            df['Company_Number'] = df['Company_Number'].astype(str).str.strip().str.zfill(5)

    # 4. Final Cleanup
    df_prebid['Acreage'] = pd.to_numeric(df_prebid['Acreage'], errors='coerce') / 1000
    
    print("Lease Data Processed Successfully.")
    return df_prebid, df_bid

# Run Processing
df_prebid, df_bid = process_lease_data(data_path)
display(df_prebid.head())
import geopandas as gpd
import matplotlib.pyplot as plt
import zipfile
import os

# --- CONFIGURATION ---
shape_zip = 'GOM_blocks.zip'
shape_out = 'boem_shapes'

def process_spatial_data(zip_p, out_p):
    # 1. Unzip
    if not os.path.exists(out_p):
        with zipfile.ZipFile(zip_p, 'r') as z:
            z.extractall(out_p)
    
    # 2. Load Shapefile
    shp_file = [f for f in os.listdir(out_p) if f.endswith('.shp')][0]
    gdf = gpd.read_file(os.path.join(out_p, shp_file))

    # 3. Standardize Spatial Keys
    # Note: Column names may vary (PROT_NUMBER vs PROT_ID)
    rename_map = {'PROT_NUMBE': 'Protraction_ID', 'BLOCK_NUMB': 'Block_Number'}
    gdf = gdf.rename(columns=rename_map)
    
    for col in ['Protraction_ID', 'Block_Number']:
        if col in gdf.columns:
            gdf[col] = gdf[col].astype(str).str.strip()

    # 4. Plot
    print(f"Loaded {len(gdf)} blocks.")
    gdf.plot(figsize=(10, 6), color='whitesmoke', edgecolor='gray', linewidth=0.3)
    plt.title("Base Map: BOEM OCS Blocks")
    plt.show()
    
    return gdf

# Run Processing
gdf_blocks = process_spatial_data(shape_zip, shape_out)
display(gdf_blocks.head())
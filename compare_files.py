import pandas as pd

def get_hsn_map(filepath):
    df = pd.read_excel(filepath, sheet_name=0)
    hsn_map = {}
    for _, row in df.iterrows():
        raw_hsn = row.get('HSN CODE')
        raw_gst = row.get('GST %')
        hsn = str(raw_hsn).replace('.0', '').strip() if pd.notna(raw_hsn) else None
        if hsn == 'nan' or hsn == '0': hsn = None
        gst = float(raw_gst) if pd.notna(raw_gst) else None
        
        if hsn and gst is not None:
            # We will store a SET of all GSTs found for this HSN
            if hsn not in hsn_map:
                hsn_map[hsn] = set()
            hsn_map[hsn].add(gst)
    return hsn_map

map3 = get_hsn_map("./warehouse data/HALTE FIXED PRICE LIST 01.8.26. (3).xlsx")
map4 = get_hsn_map("./warehouse data/HALTE FIXED PRICE LIST 01.8.26. (4).xlsx")

print("Differences between file (3) and file (4):")
found_diff = False
for hsn in set(map3.keys()).union(set(map4.keys())):
    gsts3 = map3.get(hsn, set())
    gsts4 = map4.get(hsn, set())
    if gsts3 != gsts4:
        print(f"HSN {hsn} changed! File 3: {gsts3} -> File 4: {gsts4}")
        found_diff = True

if not found_diff:
    print("NO DIFFERENCES in HSN->GST mappings between file (3) and file (4)!")

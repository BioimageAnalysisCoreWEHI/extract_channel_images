from pathlib import Path

import numpy as np
import tifffile


BASE = Path(__file__).parent
INPUT_DIR = BASE / "data" / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# OPAL/OME-style sample (channels in OME metadata)
opal_path = INPUT_DIR / "opal_sample.ome.tiff"
opal_data = np.zeros((2, 16, 16), dtype=np.uint16)
opal_data[0, 2:8, 2:8] = 100
opal_data[1, 8:14, 8:14] = 200

tifffile.imwrite(
    opal_path,
    opal_data,
    photometric="minisblack",
    metadata={"axes": "CYX", "Channel": {"Name": ["Opal 520", "Opal 620"]}},
)

# MIBI-style sample (per-page tags)
mibi_path = INPUT_DIR / "mibi_sample.tiff"
with tifffile.TiffWriter(mibi_path) as writer:
    writer.write(np.full((16, 16), 25, dtype=np.uint16), photometric="minisblack", description="{}", extratags=[(285, "s", 1, "CD11c (144)", False)])
    writer.write(np.full((16, 16), 75, dtype=np.uint16), photometric="minisblack", description="{}", extratags=[(285, "s", 1, "dsDNA (89)", False)])

print(f"Wrote: {opal_path}")
print(f"Wrote: {mibi_path}")

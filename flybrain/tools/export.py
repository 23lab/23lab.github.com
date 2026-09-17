"""Export the FlyWire v783 connectome into the compact binary the web page loads.

Inputs (put them in tools/data/ or set FLY_DATA):
  Supplemental_file1_neuron_annotations.tsv  (Schlegel et al. 2024, CC BY 4.0)
    https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv
  connectome_graph.csv.gz  (Dorkenwald et al. 2024, CC BY 4.0; source,target,synapse count)
    https://storage.googleapis.com/flywire-data/challenges/mfas/connectome_graph.csv.gz
Outputs: ../brain.bin.gz and ../meta.json
"""
import gzip, json, os, struct
import numpy as np, pandas as pd
from flysim import DATA, load, select

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") + "/"
ann, W = load()
N = W.shape[0]; W = W.tocsr(); W.sort_indices()

pos = pd.read_csv(DATA + "Supplemental_file1_neuron_annotations.tsv", sep="\t",
                  usecols=["root_id", "pos_x", "pos_y", "soma_x", "soma_y"], low_memory=False).sort_values("root_id")
x = pos.soma_x.fillna(pos.pos_x).to_numpy(); y = pos.soma_y.fillna(pos.pos_y).to_numpy()
def q(a): lo, hi = a.min(), a.max(); return np.round((a - lo) / (hi - lo) * 65535).astype(np.uint16)
px, py = q(x), q(y)

sc_names = list(ann.super_class.fillna("unknown").unique())
sc = ann.super_class.fillna("unknown").map({n: i for i, n in enumerate(sc_names)}).to_numpy(np.uint8)
side_names = ["left", "right", "center", "unknown"]
side = ann.side.fillna("unknown").map(lambda s: side_names.index(s) if s in side_names else 3).to_numpy(np.uint8)
ct = ann.cell_type.fillna("").astype(str); ct_names = sorted(ct.unique())
ct_idx = ct.map({n: i for i, n in enumerate(ct_names)}).to_numpy(np.uint16)
rid = ann.root_id.to_numpy(np.uint64)
rid_hi, rid_lo = (rid >> 32).astype(np.uint32), (rid & 0xFFFFFFFF).astype(np.uint32)

with gzip.open(OUT + "brain.bin.gz", "wb", compresslevel=9) as f:
    f.write(b"FLYW"); f.write(struct.pack("<II", N, W.nnz))
    f.write(W.indptr.astype(np.uint32).tobytes()); f.write(W.indices.astype(np.uint32).tobytes())
    f.write(W.data.astype(np.int16).tobytes())
    f.write(sc.tobytes()); f.write(side.tobytes()); f.write(ct_idx.tobytes())
    f.write(rid_hi.tobytes()); f.write(rid_lo.tobytes()); f.write(px.tobytes()); f.write(py.tobytes())

def sel(**kw): return [int(i) for i in select(ann, **kw)]
presets = {
    "sugar":     {"label": "糖/水 味觉", "idx": sel(cell_sub_class="sugar/water"), "rate": 150},
    "bitter":    {"label": "苦味 味觉", "idx": sel(cell_sub_class="bitter"), "rate": 150},
    "olfactory": {"label": "嗅觉受体", "idx": sel(cell_class="olfactory"), "rate": 50},
    "pheromone": {"label": "信息素受体", "idx": sel(cell_sub_class="pheromone"), "rate": 100},
    "auditory":  {"label": "听觉 (触角)", "idx": sel(cell_sub_class="auditory"), "rate": 100},
    "wind":      {"label": "风 / 重力", "idx": sel(cell_sub_class="wind_gravity"), "rate": 100},
    "bristle":   {"label": "眼周刚毛 (触碰)", "idx": sel(cell_sub_class="eye bristle"), "rate": 100},
    "grooming":  {"label": "梳理触觉", "idx": sel(cell_sub_class="grooming"), "rate": 100},
    "photo":     {"label": "光感受器 R1-6", "idx": sel(cell_type="R1-6"), "rate": 30},
    "cold":      {"label": "冷", "idx": sel(cell_sub_class="cold"), "rate": 100},
    "heat":      {"label": "热", "idx": sel(cell_sub_class="heating"), "rate": 100},
}
watch = {
    "ingestion":  {"label": "伸喙 / 进食运动神经元", "idx": sel(cell_sub_class="ingestion_motor_neuron")},
    "motor":      {"label": "脑内运动神经元", "idx": sel(super_class="motor")},
    "descending": {"label": "下行神经元 (脑 → 腹神经索)", "idx": sel(super_class="descending")},
    "kc":         {"label": "蘑菇体 Kenyon 细胞", "idx": sel(cell_class="Kenyon_Cell")},
}
mn9 = [int(i) for i in pd.Index(ann.root_id).get_indexer([720575940660219265, 720575940618238523])]
json.dump({"n": N, "nnz": int(W.nnz), "super_classes": sc_names, "sides": side_names, "cell_types": ct_names,
           "presets": presets, "watch": watch, "mn9": mn9},
          open(OUT + "meta.json", "w"), ensure_ascii=False, separators=(",", ":"))
print({f: os.path.getsize(OUT + f) // 1024 for f in ("brain.bin.gz", "meta.json")}, "KB")

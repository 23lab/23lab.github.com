"""Whole-brain LIF simulation of the FlyWire v783 connectome.

Model constants follow Shiu et al. 2024 (Nature 634:210-219):
  dv/dt = (v_rest - v + g)/tau_m ; dg/dt = -g/tau_syn
  presynaptic spike (after delay) -> g += 0.275 mV * sign * n_syn
  v > v_th -> spike, v=v_reset, g=0, refractory 2.2 ms
Sign: GABA/glutamate inhibitory, others excitatory (per presynaptic top_nt).
"""
import sys, time
from collections import deque
import numpy as np, pandas as pd, scipy.sparse as sp

import os
DATA = os.environ.get("FLY_DATA", os.path.join(os.path.dirname(__file__), "data")) + "/"
NT_SIGN = {"acetylcholine": 1, "dopamine": 1, "serotonin": 1, "octopamine": 1, "gaba": -1, "glutamate": -1}

def load(min_syn=5):
    ann = pd.read_csv(DATA + "Supplemental_file1_neuron_annotations.tsv", sep="\t",
                      usecols=["root_id", "super_class", "cell_class", "cell_sub_class", "cell_type", "top_nt", "side"],
                      dtype={"root_id": np.int64}, low_memory=False).sort_values("root_id").reset_index(drop=True)
    try:
        W = sp.load_npz(DATA + f"W_min{min_syn}.npz").tocsr()
    except FileNotFoundError:
        g = pd.read_csv(DATA + "connectome_graph.csv.gz"); g.columns = ["pre", "post", "w"]
        g = g[g.w >= min_syn]
        idx = pd.Index(ann.root_id)
        pre, post = idx.get_indexer(g.pre), idx.get_indexer(g.post)
        keep = (pre >= 0) & (post >= 0)
        sign = ann.top_nt.map(NT_SIGN).fillna(1.0).to_numpy(np.float32)
        w = g.w.to_numpy(np.float32)[keep] * sign[pre[keep]]
        W = sp.csr_matrix((w, (pre[keep], post[keep])), shape=(len(ann),) * 2, dtype=np.float32)
        W.sum_duplicates(); sp.save_npz(DATA + f"W_min{min_syn}.npz", W)
    return ann, W

def select(ann, **kw):
    m = np.ones(len(ann), bool)
    for k, v in kw.items():
        m &= ann[k].astype("string").isin(v if isinstance(v, (list, tuple)) else [v]).fillna(False).to_numpy()
    return np.flatnonzero(m)

def run_trial(W, stim, rate, t_run=1000.0, rng=None, dt=0.1, v_rest=-52., v_th=-45., tau_m=20., tau_syn=5.,
              t_refr=2.2, delay=1.8, w_syn=0.275, silence=None):
    rng = rng or np.random.default_rng()
    N = W.shape[0]
    if silence is not None and len(silence):
        W = W.tolil(); W[silence, :] = 0; W = W.tocsr()
    W = W * np.float32(w_syn)
    n_steps = int(round(t_run / dt)); delay_steps = max(1, int(round(delay / dt))); refr_steps = int(round(t_refr / dt))
    dm, ds = np.float32(np.exp(-dt / tau_m)), np.float32(np.exp(-dt / tau_syn)); gain = np.float32(1 - dm)
    v = np.full(N, v_rest, np.float32); g = np.zeros(N, np.float32); refr_until = np.zeros(N, np.int64)
    stim = np.asarray(stim); p_stim = rate * dt / 1000.0
    is_stim = np.zeros(N, bool); is_stim[stim] = True
    pending = deque([np.empty(0, np.int64) for _ in range(delay_steps)])
    counts = np.zeros(N, np.int64); ts, ids = [], []
    for step in range(n_steps):
        arriving = pending.popleft()
        if len(arriving):
            g += np.asarray(W[arriving].sum(axis=0)).ravel()
        active = refr_until <= step
        v = np.where(active, v_rest + (v - v_rest) * dm + g * gain, v)
        g *= ds
        spk = np.flatnonzero((v > v_th) & active & ~is_stim)
        if len(stim):
            spk = np.concatenate([spk, stim[rng.random(len(stim)) < p_stim]])
        if len(spk):
            v[spk] = v_rest; g[spk] = 0; refr_until[spk] = step + refr_steps
            counts[spk] += 1; ts.append(np.full(len(spk), step * dt, np.float32)); ids.append(spk)
        pending.append(spk)
    return counts / (t_run / 1000.0), (np.concatenate(ts) if ts else np.empty(0)), (np.concatenate(ids) if ids else np.empty(0, np.int64))

def run(W, stim, rate, n_trials=3, seed=0, **kw):
    rng = np.random.default_rng(seed)
    rates = np.zeros(W.shape[0])
    for k in range(n_trials):
        t0 = time.time(); r, _, _ = run_trial(W, stim, rate, rng=rng, **kw); rates += r
        print(f"  trial {k+1}/{n_trials}: {time.time()-t0:.1f}s, {int((r>0).sum())} neurons spiked", file=sys.stderr)
    return rates / n_trials

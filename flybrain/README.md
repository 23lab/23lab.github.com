# 果蝇全脑模拟

在浏览器里刺激果蝇的感觉神经元，看真实接线图把信号传到哪里。页面：`/flybrain/`。

- 数据：FlyWire v783 成年雌性果蝇全脑连接组（Dorkenwald et al. 2024; Schlegel et al. 2024，CC BY 4.0），保留 ≥5 个突触的连接，139,248 个神经元、2,700,429 条连接。
- 模型：漏电积分放电（LIF），参数与 Shiu et al. 2024 (Nature) 相同。GABA / 谷氨酸能神经元输出为抑制，其余为兴奋。
- 计算全部在浏览器的 Web Worker 里完成，1 秒脑活动大约 1 到 10 秒算完（取决于刺激多少神经元）。

## 文件

- `index.html` 页面（含模拟器）
- `brain.bin.gz` 连接组二进制（CSR 邻接 + 每个神经元的类别 / 侧 / 类型 / root id / 坐标），10 MB
- `meta.json` 刺激预设、读出组、字符串表
- `tools/flysim.py` Python 版模拟器（同一模型，用来校验）
- `tools/export.py` 从原始数据生成 `brain.bin.gz` 和 `meta.json`

## 重新生成数据

```bash
mkdir -p tools/data && cd tools/data
curl -LO https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv
curl -LO https://storage.googleapis.com/flywire-data/challenges/mfas/connectome_graph.csv.gz
cd .. && pip install numpy scipy pandas && python3 export.py
```

## 校验结果（Python 与浏览器一致）

| 刺激（150 Hz，1 s） | MN9 右 | MN9 左 | 下游放电神经元 |
|---|---:|---:|---:|
| 糖/水 (129) | ~150 Hz | ~110 Hz | ~450 |
| 苦味 (65) | 0 | 0 | ~80 |
| 糖 + 苦 | ~10 Hz | ~7 Hz | ~410 |

与 Shiu et al. 2024 报告的“糖驱动伸喙运动神经元 MN9，苦味抑制之”一致。

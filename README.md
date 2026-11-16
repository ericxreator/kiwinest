# KiwiNest · 奇巢

**优先照顾三块硬盘散热的紧凑家用机箱。**

[English](README.en.md) · [在线 3D 预览](https://ericxreator.github.io/kiwinest/) · [下载原型](https://github.com/ericxreator/kiwinest/releases) · [设计说明](docs/design.md) · [已知问题](docs/known-issues.md)

![KiwiNest R9 CAD 预览](docs/kiwinest-r9.png)

KiwiNest 容纳三块 3.5 英寸硬盘、Mini-ITX 参考主板、独显和原厂固定线 Flex 电源。R9 为三块盘建立独立的前进风、盘间通道和上排风路径，顶部改用 200mm 风扇，底部改为四个圆脚。主板、显卡、完整 x8 转接端头和 CPU 40mm 保护基准保持不动。

**R9 `v0.4.0-r9` 的 CAD 与公共几何检查已通过，实物与制造尚未放行。** 本次记录包括原厂 STEP 重建的 39 组整机检查基线、前分配罩底板修正后的 23 组局部复验，以及全部资产重新导出。最终报告 41 条记录按 39 条基线、1 条局部复验汇总、1 条导出完整性计数，均无失败；43 个打印项的网格封闭且绕向一致，STEP 回读 782/782 个实体有效。详细范围见[检查报告](evidence/current-review.json)及[发布验证](evidence/publication-verification.json)；这些记录不表示修正后又重复了全部整机重建。CAD 空间安排不能证明实际温升、风量或 PCIe 协商。当前改动见 [R9 说明](docs/r9-changes.md)。

## R9 布局

| 项目 | 参考设计 |
| --- | --- |
| 外尺寸 | 主体 250 × 250 × 257mm，四脚高 18mm；总外包络 250 × 250 × 275mm，约 17.19L |
| 硬盘 | 3 × 3.5 英寸；连接器朝后，独立 SATA 数据线，无背板；每盘四颗原生 6-32 螺钉 |
| 硬盘风路 | 独立 92mm 前扇 → 密封分配腔 → 两侧和盘间四通道 → 后集风腔 → 上方扩散罩 → 顶扇 |
| 通道 | 名义宽度依次 5 / 7 / 7 / 5mm，连续主通道高 82mm；安装横条放在上下边缘 |
| 顶部 | Noctua NF-A20 PWM，200 × 200 × 30mm 裸框；卸下可拆防振垫，保留原厂标签包络 |
| 其余风路 | 120mm 底进风，CPU 右侧新风，GPU 独立进气；底部滤网向右抽出 |
| 电源 | Enhance ENP-7660B 绕长轴滚转 90°；交流接口和原厂排风仍朝后，已知百叶面直接通左侧外气窗 |
| 主板与 GPU | DS_2501 / Ryzen 7 5825U 照片参考板；GPU 以 Zotac ZT-B50620H-10M 外包络为参考 |
| x8 | K83UP-TL 定制 50cm，完整原厂端头与自由线束保留；目标 PCIe 3.0 x8，实机协商待验 |

按原厂静态风扇框投影扣除遮挡后，顶扩散口的保守几何净面积约 2192.51mm²，高于四条主通道合计的 1968mm²，见[顶扇核对](evidence/top-fan-verification.json)。几何通路不代表实际流量分配、风阻、漏气、积尘或噪声通过。前部目前为进风格栅；可侧抽的滤网位于底部，不能据此把前扇也称作已过滤进风。

## 维护

前扇和分配罩分步拆卸，前左柱上段、风扇集线器和余线篮保持安装。三块盘都先断电、逐片拆后部本盘电源口和数据口两片小检修盖、拔下并停放本盘电源/数据头，再解除盘锁前抽；第一盘另需移走前左柱的可拆下段。检修盖和出线件采用开边槽与可拆密封，成品接头不需要穿闭孔。步骤与检查范围见[设计说明](docs/design.md)。这套结构没有热插拔认证。

底扇 PWM 中转头放在分配罩抽出路径右侧，底扇原线与 SYS 信号末段为盘锁扳手留出操作包络；维护检查继续保留完整线段和接头。实际工具与手部空间仍须试装。

原厂电源线和未使用的分支全部保留，标准端延长线的余线计入共享收纳区。32 条电源、数据、PWM 等完整线路预算包含曲线中心线、接头占长和装配余量，最小剩余 25.434mm，超过 R9 的 25mm 门槛；这是工程预算，真实线材仍须测量。未用 EPS 半头、Molex/FDD 和散线按完整库存与收纳体积保留，不表示每根导体或线圈都已实测建模。

## 文件与重建

- [`cad/parts/`](cad/parts/)：原创打印件 STEP / STL；薄 PC 片、泡棉、FR4、钢垫和电源金属法兰另见 [CAD 说明](cad/README.md)。
- [`cad/kiwinest-public.glb`](cad/kiwinest-public.glb) 与 [`docs/preview.html`](docs/preview.html)：原创箱体、五金和线缆工程代理；预览需要联网加载固定版本 Three.js。
- [`design/`](design/)：参数化源代码；[`bom/`](bom/)：部件与材料清单；[`evidence/`](evidence/)：实际验证范围。

使用 Python 3.13 和冻结依赖。R9 的完整本地输出包含原厂输入，只供审阅；公开资产另行筛选。

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
python scripts/prepare_references.py
python design/r9_export.py --out-dir out-r9
python scripts/build_public_assets.py --input out-r9
python scripts/build_public_bom.py --input out-r9/report.json
```

可选的顶扇核对使用另行取得的 [Noctua 官方 STEP](references/README.md#风扇参考)，只输出数值证据。安装 `shapely==2.1.2` 后，将本地文件路径交给脚本；`--source-report` 将结果绑定到本次通过的 R9 报告：

```sh
pip install shapely==2.1.2
python scripts/verify_top_fan.py --official-step /path/to/NF-A20_Public-CAD.stp --source-report out-r9/report.json --output evidence/top-fan-verification.json
```

公开模型省略两个原厂转接端头和含厂商来源曲面的受压泡棉代理，也移除它们未引用的二进制数据；泡棉另提供独立生成的平片。完整检查使用本地原厂实体，公开预览的省略不能证明真实端头适配。Noctua 官方 CAD 仅用于本地核对风扇代理，未随仓库或 Release 分发。详见[来源与分发边界](THIRD_PARTY.md)。

历史原型保留：[R8 / v0.3.0-r8](https://github.com/ericxreator/kiwinest/releases/tag/v0.3.0-r8)、[R7](https://github.com/ericxreator/kiwinest/releases/tag/v0.2.0-r7)、[R6](https://github.com/ericxreator/kiwinest/releases/tag/v0.1.0-r6)。欢迎提交实板测量、打印试装和逐盘温度记录，并区分 CAD 结果与实物验收。

## 许可

Copyright © 2026 [ericxreator](https://github.com/ericxreator)。原创代码采用 [MIT](LICENSE)；原创 CAD、网格、说明、截图和工程数据采用 [CC BY 4.0](LICENSES/CC-BY-4.0.txt)。保留作者、项目链接并说明修改；[许可范围](LICENSES/README.md)不包含独立获取的第三方材料。

布局思路参考 [QNAS7](https://github.com/thunder439/QNAS7) / [QNAS8](https://github.com/thunder439/QNAS8)，本项目重新参数化构造原创零件，不分发其原始资产。

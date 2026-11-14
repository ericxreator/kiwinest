# KiwiNest · 奇巢

**一台给家庭计算留空间的紧凑三盘机箱。**

[English](README.en.md) · [在线 3D 预览](https://ericxreator.github.io/kiwinest/) · [下载当前原型](https://github.com/ericxreator/kiwinest/releases) · [设计说明](docs/design.md) · [已知问题](docs/known-issues.md)

![KiwiNest R7 CAD 预览](docs/kiwinest-r7.png)

KiwiNest 把三块 3.5 英寸硬盘、Mini-ITX 参考主板、独显和 Flex 电源放进约 17.19L 的立式机身。硬盘独立 SATA 直连，机箱依靠自身进排风散热，外壳、托架与固定件以 CadQuery 参数化构造。

**当前为 R7 工程原型，仍需实物验收。** 本版保留现有5825U主板和40mm CPU空间，改用较短的R23SR端头；显卡连接采用 **PCIe 3.0 x4**，相较原计划x8减少链路带宽，实际应用性能与稳定性待实测。EPS/GPU原厂线重新核算出口段、接头和装配余量，增加分体隔离通道及底部开口的GPU线U形槽。当前整机23组CAD检查零失败，40个打印件网格闭合，STEP回读623个实体一致。结果见[检查报告](evidence/current-review.json)，改动见[R7说明](docs/r7-changes.md)。原R6保留在`v0.1.0-r6`标签。

原型尚未完成实板尺寸、收到的线缆、PCIe供电/稳定性、打印承载和热/噪声验收。ATX24原厂线从电源前面至工程出线点的过渡尚未完整建模；现有CAD结果只覆盖明确建模的范围。CAD检查不会自动构成制造放行。

## 主要规格

| 项目 | R7 参考布局 |
| --- | --- |
| 外尺寸 | 主体 250 × 250 × 255mm；含 20mm 独立脚座总高 275mm |
| 主板 | 170 × 170mm DS_2501 / Ryzen 7 5825U 参考板；接口位置来自照片估计，不能等同通用兼容认证 |
| CPU 空间 | 元件面向外硬留 40mm；不压缩保护空间来掩盖转接端头干涉 |
| 硬盘 | 3 × 3.5 英寸，独立数据线与成品电源原厂供电线，无背板 |
| GPU | 以 Zotac ZT-B50620H-10M / RTX 5060 Ti 16GB 的 220.5 × 120.25 × 41.6mm 包络为参考 |
| 电源 | Enhance ENP-7660B 原厂固定线 Flex；标准4pin延长，真实出口/可用线长待实配 |
| 显卡转接 | ADT-Link R23SR 30cm，电气PCIe3.0 x4，GPU端物理x16 |
| 风路 | 120mm 底进、140mm 顶排、CPU 侧进风、PSU 独立前进后出 |
| 打印基线 | 256 × 256 × 256mm 构建空间；装配公差、材料、蠕变和承载待实测 |

这套布局针对明确的部件组合，更换显卡、主板或电源后需要重新检查。风路模型仅表达空间安排，没有 CFD 或温升结论。

GPU拆卸前须断电、拆顶盖/顶扇、拔下并停放8pin延长线头；还须松开底部软绑带，使用预留余量把原厂300mm线的自由段移到前侧停放，保持原厂中转接头固定，再按步骤拆夹具、脱槽上提。正常走线不能直接视为GPU上拔时的走线，实际软线变形与停放动作仍待实配。

## 文件和查看方式

- [`cad/parts/`](cad/parts/)：40 个原创机箱零件，各提供 STEP 与 STL。
- [`cad/PSU-flange-1mm-REVIEW.dxf`](cad/PSU-flange-1mm-REVIEW.dxf)：1mm 金属电源法兰，另附 STEP；**不是打印件**。
- [`cad/kiwinest-public.glb`](cad/kiwinest-public.glb)：原创箱体、五金和线缆工程代理的装配预览。
- [`docs/preview.html`](docs/preview.html)：下载后在浏览器打开，可旋转、缩放和隐藏外壳；Three.js 通过固定版本 CDN 加载，需要联网。
- [`bom/`](bom/)：部件选型、五金、打印件清单；未知容量、数量、价格不补造。
- [`design/`](design/)：完整当前 参数化构造与导出入口，旧版辅助模块仅保留使用的函数。
- [`evidence/current-review.json`](evidence/current-review.json)：当前真实检查结果、完整线长预算、零件指标与来源报告 SHA-256。

公开装配省略两个 ADT-Link 原厂端头 CAD，连同未引用的二进制数据。整机检查使用包含真实原厂端头的本地模型；公开预览的省略不能用来掩盖碰撞或判定通过。厂商图纸、原始照片与 QNAS 模型没有随仓库分发，详见 [来源说明](THIRD_PARTY.md)。

## 本地重建

已验证的源环境是 Python 3.13.13、CadQuery 2.8.0。完整冻结依赖见 `requirements.lock`；`requirements.txt` 列出直接依赖。

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
python scripts/prepare_references.py
python design/r6_export.py
```

准备脚本从原厂下载固定 SHA-256 的参考输入，仅写入 Git 忽略的 `references/private/`。原厂地址内容变化时停止，须重新审查。也支持经同样校验的离线文件，见 [`references/README.md`](references/README.md)。

源模块沿用`r6_`文件名；当前版本以参数中的`release_revision`为准。`out-r6/` 是包含原厂输入几何的**本地审阅输出**，不会自动成为公开产物。导出成功、STEP 回读通过与打印网格闭合，不代表碰撞、实际装配或制造通过。需要生成本项目相同边界的公开资产时，再运行：

```sh
python scripts/build_public_assets.py
python scripts/build_public_bom.py
python scripts/airflow_projection.py --pattern 'CABLE_R7_R23SR_band_*.step' --output evidence/airflow-current.json
```

当前发布的实际验证范围见 [`evidence/publication-verification.json`](evidence/publication-verification.json)。几何检查、STEP回读、打印网格与浏览器验收分别记录，实物/热验证保持独立状态。

## 参与改进

欢迎通过 Issue / PR 反馈实板测量、线缆与打印试装结果，继续改进余线收纳和维护结构。提交时请附参数、部件版本、检查结果，并分别说明 CAD 检查和实物测试。当前优先事项见 [已知问题](docs/known-issues.md)。

结构思路参考了 [thunder439/QNAS7](https://github.com/thunder439/QNAS7) 和 [QNAS8](https://github.com/thunder439/QNAS8)，感谢原作者的工作；本仓库发布的是重新参数化构造的原创零件与代码，参考资产的权利与许可范围见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## 许可证

Copyright © 2026 [ericxreator](https://github.com/ericxreator)。

- 原创 Python、HTML/JavaScript 源码：**MIT**，见 [`LICENSE`](LICENSE)。
- 原创 CAD、网格、设计说明、截图及工程数据：**CC BY 4.0**，见 [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt)。

使用或修改 CAD 时保留作者和项目链接，并说明改动。项目许可证不涵盖独立获取的第三方材料；完整文件范围见 [`LICENSES/README.md`](LICENSES/README.md)。

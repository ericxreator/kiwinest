# KiwiNest · 奇巢

**一台给家庭计算留空间的紧凑三盘机箱。**

[English](README.en.md) · [在线 3D 预览](https://ericxreator.github.io/kiwinest/) · [下载 R6 原型](https://github.com/ericxreator/kiwinest/releases) · [设计说明](docs/design.md) · [已知问题](docs/known-issues.md)

![KiwiNest R6 CAD 预览](docs/kiwinest-r6.png)

KiwiNest 把三块 3.5 英寸硬盘、Mini-ITX 参考主板、独显和 Flex 电源放进约 17.19L 的立式机身。硬盘独立 SATA 直连，机箱依靠自身进排风散热，外壳、托架与固定件以 CadQuery 参数化构造。

**当前发布为 R6 工程原型：几何检查未通过，尚未制造放行。** 转接线端头及固定件与 CPU 40mm 保护空间仍有干涉，原厂 EPS 线长也未满足完整路径；不据此采购转接线或打印整机定稿。开源是为了继续改进结构，实物、承载、热与噪声验收仍未完成。

## 主要规格

| 项目 | R6 参考布局 |
| --- | --- |
| 外尺寸 | 主体 250 × 250 × 255mm；含 20mm 独立脚座总高 275mm |
| 主板 | 170 × 170mm DS_2501 / Ryzen 7 5825U 参考板；接口位置来自照片估计，不能等同通用兼容认证 |
| CPU 空间 | 元件面向外硬留 40mm；不压缩保护空间来掩盖转接端头干涉 |
| 硬盘 | 3 × 3.5 英寸，独立数据线与成品电源原厂供电线，无背板 |
| GPU | 以 Zotac ZT-B50620H-10M / RTX 5060 Ti 16GB 的 220.5 × 120.25 × 41.6mm 包络为参考 |
| 电源 | Enhance ENP-7660B 原厂固定线 Flex；具体线长仍须确认 |
| 风路 | 120mm 底进、140mm 顶排、CPU 侧进风、PSU 独立前进后出 |
| 打印基线 | 256 × 256 × 256mm 构建空间；装配公差、材料、蠕变和承载待实测 |

这套布局针对明确的部件组合，更换显卡、主板或电源后需要重新检查。风路模型仅表达空间安排，没有 CFD 或温升结论。

## 文件和查看方式

- [`cad/parts/`](cad/parts/)：40 个原创机箱零件，各提供 STEP 与 STL。
- [`cad/PSU-flange-1mm-REVIEW.dxf`](cad/PSU-flange-1mm-REVIEW.dxf)：1mm 金属电源法兰，另附 STEP；**不是打印件**。
- [`cad/kiwinest-r6-public.glb`](cad/kiwinest-r6-public.glb)：原创箱体、五金和线缆工程代理的装配预览。
- [`docs/preview.html`](docs/preview.html)：下载后在浏览器打开，可旋转、缩放和隐藏外壳；Three.js 通过固定版本 CDN 加载，需要联网。
- [`bom/`](bom/)：部件选型、五金、打印件清单；未知容量、数量、价格不补造。
- [`design/`](design/)：完整 R6 参数化构造与导出入口，旧版辅助模块仅保留使用的函数。
- [`evidence/r6-review.json`](evidence/r6-review.json)：原始检查的失败结果、零件指标与来源报告 SHA-256。

公开装配省略两个 ADT-Link 原厂端头 CAD；所有未引用的端头二进制数据也已移除。**这不改变原 R6 已知干涉的失败结论**，不能由公开预览中的省略宣称通过检查。厂商图纸、原始照片与 QNAS 模型没有随仓库分发，详见 [来源说明](THIRD_PARTY.md)。

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

`out-r6/` 是包含原厂输入几何的**本地审阅输出**，不会自动成为公开产物。导出成功、STEP 回读通过与打印网格闭合，不代表碰撞、实际装配或制造通过。需要生成本项目相同边界的公开资产时，再运行：

```sh
python scripts/build_public_assets.py
```

首次开源时验证了源码解析与导入、辅助函数一致性、原厂输入校验和端头提取、40 组零件逐文件 SHA，以及公开 GLB 的逐 accessor 字节范围；未重新执行耗时整机几何构建。原 R6 几何失败继续保留。

## 参与改进

欢迎通过 Issue / PR 改进转接端头避让、EPS 路径、余线收纳、打印与维护结构。提交时请附参数、部件版本、检查结果，并分别说明 CAD 检查和实物测试。当前优先事项见 [已知问题](docs/known-issues.md)。

结构思路参考了 [thunder439/QNAS7](https://github.com/thunder439/QNAS7) 和 [QNAS8](https://github.com/thunder439/QNAS8)，感谢原作者的工作；本仓库发布的是重新参数化构造的原创零件与代码，参考资产的权利与许可范围见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## 许可证

Copyright © 2026 [ericxreator](https://github.com/ericxreator)。

- 原创 Python、HTML/JavaScript 源码：**MIT**，见 [`LICENSE`](LICENSE)。
- 原创 CAD、网格、设计说明、截图及工程数据：**CC BY 4.0**，见 [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt)。

使用或修改 CAD 时保留作者和项目链接，并说明改动。项目许可证不涵盖独立获取的第三方材料；完整文件范围见 [`LICENSES/README.md`](LICENSES/README.md)。

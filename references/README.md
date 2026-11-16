# 外部参考与原创代理

`original/` 只包含项目自行构造的 GPU 包络、I/O 安装耳、PCIe 卡边代理，以及电源机械尺寸的事实性转录。代理不能替代原厂精确 CAD 或实物合板。R9 保留商业 x8 端头与原创 FR4 / 绝缘泡棉夹持、钢制沉头承载垫，重排硬盘、电源和风路；实际夹持、槽供电和 x8 协商仍待实物验收。

## 完整本地模型的输入

K83UP-TL 原厂 CAD 与 ENP-7660B PDF 不在公开仓库中。准备入口固定 ZIP 成员和 SHA-256，只把核对后的下载、提取产物和回执写入 Git 忽略的 `private/`：

```sh
python scripts/prepare_references.py
python design/r9_export.py --out-dir out-r9
```

| 输入 | 来源 / 固定成员 | SHA-256 |
| --- | --- | --- |
| K83UP-TL ZIP，36,635,266 字节 | [官方下载](https://www.adtlink.cn/download/ADT_K83UP-TL_3D.zip) | `1971eca32a1d68b7ef9b86890fe03d989d0ddb1659a6031c6fe1f2e425eb2c56` |
| 指定原始 STEP，96,869,926 字节 | `K83UP-TL 5.0 20260707.step` | `e156ba5c03c742bebcb18983eb98ac41141be0d495ccd572c6015d496692b309` |
| ENP-7660B PDF，325,319 字节 | [原厂规格](https://www.enhanceusa.com/upload/DM/202510080638420.pdf) | `8df699a26d42f0849d06c9cd043733581196acea124f6a97b5c515b07cce7c4e` |

原始 STEP 应分解为 1012 个实体，按天然 PCB 端头分界及明确来源分类提取公端 143 个、母端 219 个唯一实体，输出 `K83UP_TL_official_male_endpoint.step` 与 `K83UP_TL_official_female_endpoint.step`。去重仅使用序列化 BRep 完全相同的 SHA 标识，保留套管内芯线和原厂固定扇出；演示自由束线由机箱完整路径替代。归属、哈希或数量不符时停止，不能通过删实体凑数。

准备后的原厂输入与装配改造分别记录。FR4、泡棉和钢垫不裁切 PCB / 触点；原厂完整锁扣可逆拆下并保管。公端需台面预装，原厂 M2 扣持、泡棉预紧、真实槽型和在位工具空间仍须实物核对。泡棉受压曲面只留本地检查；公开提供独立生成的 1.5mm 平片外形和孔，不提供沿厂家线束曲面加工的槽面。

定制 50cm 的工程口径为两端各 18mm 套管加 464mm 完整自由束线，实际厂商测法和批次公差仍须确认。旧 R7 输入或回执不能替代当前 K83UP-TL 准备结果。

断网时可提供已有文件，校验不变：

```sh
python scripts/prepare_references.py --adt-archive /path/to/ADT_K83UP-TL_3D.zip --psu-pdf /path/to/enp7660b-official-spec-20251008.pdf
```

## 风扇参考

R9 的 NF-A20 顶扇公开代理由独立基础几何构造，保留 200mm 框、安装孔和标签包络。Noctua 官方 STEP / PDF 仅在本地核对保守代理包含性、间隙、实际框开口与固定支撑投影，不导入公开风道或加工件。投影净口核对只公开源哈希、方法和面积结果，不公开厂商投影几何。官方来源见 [THIRD_PARTY.md](../THIRD_PARTY.md)。

可选的原厂核对脚本只输出标量结果，不导出厂商几何。另装验证用依赖后，将从[官方压缩包](https://cdn.noctua.at/media/4d019b79/NF-A20_Public-CAD.zip?download=true)取得的 STEP 显式交给脚本：

```sh
pip install shapely==2.1.2
python scripts/verify_top_fan.py --official-step references/private/NF-A20_Public-CAD.stp --source-report out-r9/report.json --output evidence/top-fan-verification.json
```

脚本固定核对 STEP SHA-256 `4dba51c63094d461351024ba1314afb87714d43e6bee220bdab2d93a21563498`，检查去掉八片可拆防振垫后整框、转子及标签被原创代理包含，并按静态固定框投影复算保守净口。实际叶轮、固定框和动态气动作用分别处理，输出不含输入路径、网格、投影轮廓或 BRep。

这些风扇核对资料不属于准备脚本生成完整电源 / x8 模型所必需的运行时输入。原厂几何、机械公差、线出口和真实风阻仍须样件确认，不能把代理包含性当成散热验收。

## 本地输出与公开边界

`out-r9/` 含原厂几何，只供本地审阅，由 `.gitignore` 排除。公开资产从实际报告与明确排除清单生成：

```sh
python scripts/build_public_assets.py --input out-r9
python scripts/build_public_bom.py --input out-r9/report.json
```

公开 GLB / HTML 只分发原创几何与工程代理，剔除两个完整原厂端头和含厂商来源曲面的泡棉受压代理，也移除其未引用二进制数据。泡棉公开文件为 `R8_RISER_MALE_SILICONE_FOAM_FLAT_STOCK_1p5.{step,dxf}` 独立平片；原厂受压曲面 STEP 不公开。

R9 本次记录包含原厂 STEP 重建的 39 组整机基线、分配罩底板修正后的 23 组局部复验，以及全套资产重新导出。最终报告 41 条记录（39 条基线、1 条局部复验汇总、1 条导出完整性）均无失败，43 个打印项的网格封闭且绕向一致，STEP 回读 782/782 个有效实体；这不表示局部修复后又重复了全量重建。来源、网格及分发边界见[本次报告](../evidence/current-review.json)、[公开几何审计](../evidence/public-geometry-audit.json)及[发布验证](../evidence/publication-verification.json)。导出成功或省略后的预览不能证明真实装配、制造或温度通过。历史 [R8 发布](https://github.com/ericxreator/kiwinest/releases/tag/v0.3.0-r8)保留其自身的结果与来源记录。

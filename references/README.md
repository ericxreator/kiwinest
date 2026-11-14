# 外部参考与原创代理

`original/`只包含项目自行构造的GPU包络、I/O安装耳、PCIe卡边代理，以及电源机械尺寸的事实性转录。这些代理不是原厂精确CAD，不能替代实物合板与接口核对。当前`v0.3.0-r8`工程原型使用商业x8端头及原创FR4/绝缘硅胶泡棉夹持件、两片钢制沉头承载垫，完整模型通过25组CAD检查；实物夹持和实板x8协商尚未验收。

## R8原厂输入

K83UP-TL原厂CAD与ENP-7660B PDF没有包含在公开仓库中。准备入口固定具体ZIP成员和SHA-256，只把校验后的下载、提取产物和回执写入Git忽略的`private/`：

```sh
python scripts/prepare_references.py
python design/r6_export.py --out-dir out-r8
```

当前准备脚本声明的输入如下，实际执行还须满足全部校验，不能因文件名相同而跳过哈希检查。

| 输入 | 原厂来源 / 固定成员 | SHA-256 |
| --- | --- | --- |
| K83UP-TL ZIP，36,635,266字节 | [官方下载](https://www.adtlink.cn/download/ADT_K83UP-TL_3D.zip) | `1971eca32a1d68b7ef9b86890fe03d989d0ddb1659a6031c6fe1f2e425eb2c56` |
| 明确指定的原始STEP，96,869,926字节 | `K83UP-TL 5.0 20260707.step` | `e156ba5c03c742bebcb18983eb98ac41141be0d495ccd572c6015d496692b309` |
| ENP-7660B原厂PDF，325,319字节 | [原厂规格](https://www.enhanceusa.com/upload/DM/202510080638420.pdf) | `8df699a26d42f0849d06c9cd043733581196acea124f6a97b5c515b07cce7c4e` |

脚本应确认原始STEP分解为1012个实体，按天然PCB端头分界及明确来源分类提取原厂公端143个、母端219个唯一实体，输出`K83UP_TL_official_male_endpoint.step`与`K83UP_TL_official_female_endpoint.step`。去重只使用序列化BRep完全相同的SHA标识，保留端头套筒内的芯线和原厂固定扇出；自由演示线束由机箱完整路由代替。若归属或数量不符，停止并检查厂商模型，不能通过删除实体来凑出预期结果。

准备后的原厂端头与本项目装配时的改造夹持件分别记录：替换可拆下夹条/前M2不表示裁切PCB或触点。原厂完整锁扣在本版装配中可逆拆下，固定在原创一体桥保管夹内，以M2x25横销和捕获M2螺母保持；厂家锁扣材料全部保留。GPU由I/O耳、导轨与上夹保持，实际拆件、保持力、承载和链路尚未验收，不能称原厂直接装入。

公端保留的中/后M2头朝下、轴朝上，仅沿原轴向拧入0.399997425mm至FR4承压面并在台面预装。原厂上夹条CAD为2.2mm无牙孔，实际厂家扣持方式与额外进入量未验；维护先释放支架/束线并整体移出，工具可达与组合完整移出路径未验。绝缘硅胶泡棉使用1.5mm原片，仅裁外形及两孔；名义1.4mm受压贴合曲面含厂商来源几何，只留本地检查，不能沿原厂线束曲面铣槽。受控局部压接0.150796mm³、域外0、上限0.5mm³，压缩曲线、预紧与回弹仍须实测。

完整原厂输入及改造前后对应关系留在本地验证；型号与净距以R8实际报告为准。线长采用50cm，500mm包含两端各18mm原厂套管与464mm完整自由曲线；同一路由族紧凑参考414.787125mm，49.212875mm几何回环已包含在464mm内。供应商测量口径和实际线长仍须收到样品后确认。旧R7的R23SR输入或旧回执不能代替K83UP-TL准备结果。

断网环境可使用已有原厂文件，校验要求保持不变：

```sh
python scripts/prepare_references.py --adt-archive /path/to/ADT_K83UP-TL_3D.zip --psu-pdf /path/to/enp7660b-official-spec-20251008.pdf
```

## 本地输出与公开边界

`out-r8/`含原厂几何，只供本地审阅，已由`.gitignore`排除。稳定导出入口仍名为`design/r6_export.py`，版本由参数中的`release_revision`确定。公开产物从当前报告及明确排除清单生成：

```sh
python scripts/build_public_assets.py --input out-r8
python scripts/build_public_bom.py --input out-r8/report.json
python scripts/airflow_projection.py --cables-dir out-r8/cables --pattern 'CABLE_R8_K83*.step' --output evidence/airflow-current.json
```

公开装配只分发原创几何与工程代理，剔除两个完整原厂端头和含厂商来源几何的泡棉受压曲面共三个节点，连同相关未引用二进制数据。泡棉公开加工文件为独立生成的`R8_RISER_MALE_SILICONE_FOAM_FLAT_STOCK_1p5.{step,dxf}`，外形7.6 × 60.427 × 1.5mm、两D2.4孔；受压NURBS STEP不公开。原厂文件依各自条款使用，本项目许可证不授予其再分发权。导出按当前实际检查生成状态，STEP回读或公开模型省略不构成真实装配/制造通过。实际接口、线长测法、弯曲、供电、绝缘、强度和热/噪声验收仍须实物验证；详见[来源说明](../THIRD_PARTY.md)与[R8改动](../docs/r8-changes.md)。

本版[发布检查](../evidence/publication-verification.json)记录完整STEP回读731/731实体有效、40/40打印网格闭合，公开370节点的[字节审计](../evidence/public-geometry-audit.json)通过。检查对应源报告SHA-256 `ba4dd297f32b29356117de27b970dbf2806e9d80595a0c258c1f7f63e8f6e319`；这些结果保持本地完整模型和公开精简模型的范围区分。

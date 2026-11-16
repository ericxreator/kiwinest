# 来源、致谢与未分发材料

KiwiNest 发布原创参数化代码、机箱零件、夹持件、工程代理和说明。原创代码采用 MIT，原创 CAD 与工程资料采用 CC BY 4.0；引用下列来源不扩大第三方材料的授权范围。R9 本次 CAD 与公共几何字节检查已通过；记录区分原厂 STEP 整机基线、分配罩底板局部复验及全套重新导出，实际版本和文件成员以发布清单和本次报告为准。物理、热和制造验收仍单独记录。

## 布局参考

| 来源 | 固定参考版本 | 使用边界 |
| --- | --- | --- |
| [thunder439/QNAS7](https://github.com/thunder439/QNAS7) | `27e5919ad2c74ecf2df49603879b9dd32447d121` | 结构思路参考；不分发其 STEP、STL、照片或源码 |
| [thunder439/QNAS8](https://github.com/thunder439/QNAS8) | `492cbcc55a5f0c1f36b2798a21b64ffed85c3c4a` | 紧凑布局参考；不分发其 STEP、STL、照片或源码 |

核对的上游根目录未见明确 LICENSE，不据此推定再分发或改许可授权。本项目的机箱、托架、风道、薄片轮廓、金属法兰、FR4 和钢垫由数值参数及基础几何重新构造，没有导入上游几何。

## 原厂机械参考

- [ADT-Link K83 产品页](https://adtlink.cn/cn/product/K83UX-FG.html)及[K83UP-TL 官方模型 ZIP](https://www.adtlink.cn/download/ADT_K83UP-TL_3D.zip)：本地 x8 端头 STEP / PDF 来源。选择定制 50cm，模型保留两端各 18mm 套管及 464mm 完整自由束线；PCB / 连接器与供应商线长测量口径、实际公差仍须实物核对。目录 Gen5 标称不代表本机已协商 PCIe 3.0 x8。
- [Enhance ENP-7660B 规格](https://www.enhanceusa.com/upload/DM/202510080638420.pdf)：原厂机身、原生安装、固定线束与进排风参考。R9 将原机滚转，保留交流接口朝后；开孔、未显示的对侧大面和出口 XYZ 仍须收到原机后确认。`references/original/native-mechanical.json` 为事实尺寸的工程转录，不能当作厂家三维出口测量。
- [Seagate IronWolf 100844482 Rev F](https://www.seagate.com/files/www-content/product-content/ironwolf/en-us/docs/100844482f.pdf)：参考硬盘的尺寸、原生安装孔与螺钉最大进入量。实际更换盘型号须重新核对。
- [Zotac ZT-B50620H-10M 规格](https://www.zotac.com/download/mediadrivers/External/GraphicsCard/5060Ti/Brochure/ZT-B50620H-10M-brochure.pdf)：显卡外包络参考；仓库 GPU 实体为原创尺寸代理。
- PCI-SIG CEM 3.0 Fig.6-3：卡边机械尺寸参考，只构造工程接口代理，不分发规范文件。
- DS_2501 主板：接口坐标来自参考照片估计，照片不分发；实际版次、槽型、针脚、电流与尺寸仍待确认。
- [Noctua NF-A20 PWM 规格](https://www.noctua.at/en/products/nf-a20-pwm/specifications)、[官方下载](https://www.noctua.at/en/products/nf-a20-pwm/downloads)与[机械规格 PDF](https://cdn.noctua.at/media/73165231/Noctua%20NF-A20%20PWM%20Specification.pdf?download=true)：200mm 顶扇外形、可拆防振垫、标签、安装孔、原线和随附延长线参考。官方精确 CAD 仅用于本地代理包含性、间隙与固定框投影的数值核对；不作为公开箱体、风道或加工件的几何来源。
- [Noctua NF-A9 PWM 规格](https://www.noctua.at/en/products/nf-a9-pwm/specifications)：92mm 前扇的 92 × 92 × 25mm 裸框、93 × 93 × 27mm 含垫包络、82.5mm 孔距、200mm 原线和随附 300mm NA-EC1 参考。目录最大风量和静压不是本机安装值。
- [Noctua NF-P12 redux-1700 PWM 规格](https://www.noctua.at/en/products/nf-p12-redux-1700-pwm/specifications)：120mm 底扇与 400mm 原线参考。25mm 实扇与 26mm 保守代理的垫片厚度须按实物调整。

## x8 夹持与加工边界

FR4 下压条、绝缘硅胶泡棉平片、固定支架和主板 2/4 号齐平钢制沉头承载垫属于原创加工件。原厂 PCB、触点、完整扇出和上夹条继续作为本地输入。原厂中/后 M2 头朝下、轴朝上，台面预装；原上夹条 CAD 未建螺纹，实际扣持、进入量、绝缘、预紧和载荷未验收，不能称厂家原装兼容认证。

泡棉采用 1.5mm 原片，仅裁外形和两孔。公开 `R8_RISER_MALE_SILICONE_FOAM_FLAT_STOCK_1p5.{step,dxf}` 独立生成；复用厂商曲面的名义 1.4mm 受压代理只留本地检查，不分发，不用于按线束曲面铣槽。受控软压接不等于压缩、回弹、拉脱和信号已验收。

原厂完整锁扣在装配中可逆拆下，放入原创保管夹，由 M2x25 横销和捕获螺母保持，厂家锁扣材料全部保留。GPU 由 I/O 耳、导轨和上夹保持；实际拆装、承载及链路仍须验证。旧 R6 / R7 输入保留在历史标签，不能替代 R9 的 x8 要求。

## 标准线材与控制部件

- [MODDIY CO581](https://www.moddiy.com/products/2256/Premium-Custom-PSU-Extension-Cable-4-Pin-CPU-EPS-Power.html)：标准 4pin CPU / EPS 公对母延长线，选型 60cm。
- [MODDIY CAB534](https://www.moddiy.com/products/3281/Premium-Custom-PSU-Extension-Cable-8-Pin-PCIE-Power.html)：标准 8pin PCIe 公对母延长线，配置长度以本次 BOM 与完整线长报告为准。
- [MODDIY CAB456](https://www.moddiy.com/products/1662/SATA-Power-Extension-Cable-50cm.html)：三根 50cm 标准 SATA 电源公对母延长线。标准端延长不改变 PSU 内部或模组接口接线。
- [StarTech SATAPOWEXT8](https://media.startech.com/cms/pdfs/satapowext8_datasheet.pdf)：集线器标准 SATA 电源延长线，203.2mm；实际接头与绝缘外形仍待测量。
- [StarTech LSATA24](https://media.startech.com/cms/pdfs/lsata24_datasheet.pdf)：三根 609.6mm 直连 SATA 数据线；模型端头和线径是工程代理。
- [MODDIY CAB529](https://www.moddiy.com/products/3246/Premium-Custom-PSU-Extension-Cable-24-Pin-Main-Power.html)：标准 ATX24pin 公对母延长线，配置长度以本次 BOM 和完整预算为准。
- [Noctua NA-SEC1](https://www.noctua.at/en/products/na-sec1)：每套三根 300mm NA-EC1。每根路径和中转头分别核算，不用总长掩盖某一段不足。
- [Noctua NA-FH1](https://www.noctua.at/en/products/na-fh1)：SATA 供电风扇集线器参考；实际供电与主板 SYS / CPUFAN 针脚、允许电流仍须核对实物。

目录用于建立选型和完整线长预算，不表示已核实库存、交期、价格或安装兼容性。收到的线材、接头、实际可用长度、绝缘、弯曲、余线收纳与供电能力仍需验收。商标归各自权利人，不表示其认可本项目；原厂图片或资料没有打包。

## 公开模型与软件

厂商 ZIP、PDF、照片、精确 STEP、提取端头、Noctua 原厂 CAD 和泡棉受压曲面不随仓库及发布包分发。准备脚本只提供自行下载、哈希核对与本地提取，输入留在 Git 忽略目录。公开 GLB / HTML 剔除两个转接端头和受压泡棉节点，连同相关未引用二进制数据；[公开几何审计](evidence/public-geometry-audit.json)记录实际分发边界，不能构成厂商授权或实物适配认证。

Noctua 风扇公开模型采用独立圆、方框和孔位工程代理。任何原厂固定框投影只在本地用于净口数值核对，公开资料只记录方法、源哈希与结果，不含投影轮廓或派生 BRep。完整检查与公开精简模型保持独立范围。

- [Three.js](https://github.com/mrdoob/three)：MIT，预览经 CDN 加载固定版本 `0.181.0`，未打包库本体。
- [CadQuery](https://github.com/CadQuery/cadquery)：Apache-2.0，经依赖安装提供，运行库不随发布 ZIP 打包。
- [Shapely](https://github.com/shapely/shapely)：`verify_top_fan.py` 的可选本地验证依赖，固定使用 2.1.2，不随发布包打包；主 CAD 重建不依赖它。
- 其他软件依赖按各自许可安装，版本见 `requirements.lock`。

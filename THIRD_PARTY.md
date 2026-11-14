# 来源、致谢与未分发材料

本项目发布原创参数化代码、机箱零件、夹持件、工程代理与说明。引用下列来源不改变这些独立材料的权利或许可证。当前`v0.3.0-r8`工程原型的完整模型通过25组CAD检查，型号、文件成员与SHA-256与准备脚本及实际检查报告对应；物理、制造与热验收保持独立且尚未放行。

## 结构思路参考

| 来源 | 固定参考版本 | 使用边界 |
| --- | --- | --- |
| [thunder439/QNAS7](https://github.com/thunder439/QNAS7) | `27e5919ad2c74ecf2df49603879b9dd32447d121` | 结构思路参考；不分发其STEP、STL、照片或源码 |
| [thunder439/QNAS8](https://github.com/thunder439/QNAS8) | `492cbcc55a5f0c1f36b2798a21b64ffed85c3c4a` | 紧凑布局参考；不分发其STEP、STL、照片或源码 |

核对的上游根目录未见明确LICENSE，不据此推定再分发或改许可授权。机箱零件、支架、FR4压条、绝缘硅胶泡棉外形、自制钢承载垫与电源法兰由数值参数及基础几何重新构造，没有导入上游几何。

## 原厂端头与机械参考

- [ADT-Link K83产品页](https://adtlink.cn/cn/product/K83UX-FG.html)及其链接的[K83UP-TL官方模型ZIP](https://www.adtlink.cn/download/ADT_K83UP-TL_3D.zip)：本版x8端头的原厂STEP/PDF来源。厂家目录将PCB/连接器排除在线长外；实际线长误差、型号和收到的样品仍须核对。本版选择定制50cm，模型将500mm分为两端各18mm保留套管与464mm自由线束，其中约49.213mm是同一路由族内的几何回环分配，须核对供应商测量口径。本机目标链路以主板和本项目要求为准，不把线材目录的Gen5标称当作整机协商结果。
- R8夹持方案的FR4下压条、绝缘硅胶泡棉平片外形、机架支撑以及主板2/4号安装点的两片齐平钢制沉头承载垫是本项目原创制造件；原厂PCB、触点、完整扇出和上夹条继续作为本地审阅输入。原厂中/后M2头朝下、轴朝上，只沿原轴向拧入约0.400mm，按FR4承压面台面预装；原上夹条CAD的2.2mm孔未建牙，实际扣持/进入量待验。维护先释放支架与束线、整体移出后再操作头部，在位工具空间和组合完整移出路径未验。泡棉1.5mm原片仅裁外形及两孔，公开文件`R8_RISER_MALE_SILICONE_FOAM_FLAT_STOCK_1p5.{step,dxf}`独立生成；含厂商来源曲面的1.4mm受压包络只留本地检查，不分发也不用于铣槽。受控局部压接不等于材料压缩、预紧、回弹、负载、绝缘和信号已验收，不能视为厂家原装兼容认证。
- 原厂完整锁扣在本版装配中可逆拆下并固定在原创一体桥保管夹，以M2x25横销和捕获M2螺母保持，厂家锁扣材料全部保留。GPU由I/O耳、导轨及上夹保持；实际拆装、承载、保持力和链路尚未验收，不表示原厂直接装入或厂家认可改造。
- R6使用R83SL、R7使用R23SR的模型记录保留在历史标签；R7x4不能替代R8的x8要求。
- [Enhance ENP-7660B规格](https://www.enhanceusa.com/upload/DM/202510080638420.pdf)：机身、安装和固定线束尺寸参考。`references/original/native-mechanical.json`是事实尺寸的工程转录；出口XYZ仍为工程假设，不是厂家三维出口测量。
- [Seagate IronWolf 100844482 Rev F](https://www.seagate.com/files/www-content/product-content/ironwolf/en-us/docs/100844482f.pdf)：硬盘尺寸、原生安装孔和螺钉进入深度参考。
- [Zotac ZT-B50620H-10M规格](https://www.zotac.com/download/mediadrivers/External/GraphicsCard/5060Ti/Brochure/ZT-B50620H-10M-brochure.pdf)：显卡外包络参考；仓库GPU实体为自行构造的代理。
- PCI-SIG CEM3.0 Fig.6-3：卡边机械尺寸参考；仅构造接口代理，不分发规范文件。
- DS_2501主板：接口坐标由参考照片估计，照片不分发；板版次、针脚、电流和实物尺寸仍须确认。

厂商ZIP、PDF、照片、STEP原件、提取的原厂端头及泡棉受压贴合曲面均不随仓库及发布包分发。准备脚本只提供自行下载、哈希核对和本地提取途径，写入忽略的`references/private/`。公开GLB/HTML移除两个原厂端头和泡棉受压曲面共三个节点，连同全部未引用二进制数据；公开泡棉加工件是独立生成的7.6 × 60.427 × 1.5mm平片及两D2.4孔。完整干涉检查继续使用本地原厂模型和受压代理，省略后的预览不证明真实装配适配。

[公开几何审计](evidence/public-geometry-audit.json)确认公开GLB为370节点，16,494个保留访问器与源数据逐字节一致，与被排除厂商访问器的字节重叠为0，未引用非零字节为0。这项审计记录分发边界，不构成厂商授权或实物装配认证。

## 线材与控制部件目录

- [MODDIY CO581](https://www.moddiy.com/products/2256/Premium-Custom-PSU-Extension-Cable-4-Pin-CPU-EPS-Power.html)：标准4pin CPU/EPS公对母延长线，本版选60cm。供应商提供10–100cm定制长度。
- [MODDIY CAB534](https://www.moddiy.com/products/3281/Premium-Custom-PSU-Extension-Cable-8-Pin-PCIE-Power.html)：标准8pin PCIe公对母延长线，本版选70cm。此类标准端延长不替换PSU内部或模组接口接线。
- [StarTech SATAPOWEXT8数据表](https://media.startech.com/cms/pdfs/satapowext8_datasheet.pdf)：SATA15pin公对母电源延长线，8英寸（203.2mm）、18AWG，公布产品宽30mm、高8mm。模型新增端头采用30mm宽度，轴向长度与绝缘外形仍待实测。
- [StarTech LSATA24数据表](https://media.startech.com/cms/pdfs/lsata24_datasheet.pdf)：三根24英寸SATA数据线的选型参考，实际端头/线径代理不等于厂家三维CAD。
- [Phanteks标准延长线目录](https://phanteks.com.tw/Extension-Cables.html)：PH-CB24P_BK 500mm标准ATX24pin延长线参考；R7曾用的500mm EPS延长线不再作为R8选型。
- [Noctua NA-SEC1](https://www.noctua.at/en/products/na-sec1)：一套三根300mm NA-EC1 PWM延长线。本版按每根线路和中转头核算，不以总长度掩盖单根不足。

目录长度与选项用于预算；收到的线材、端头尺寸、实际可用长度、绝缘、弯曲、余线收纳和对应供电能力仍需验收。未把网站库存、交期、价格或供应商宣传当作本项目装配保证。产品名及商标属于各自权利人，不表示其认可本项目；没有打包Noctua、ITW、Phanteks、StarTech、MODDIY等原厂图片或资料。

## 运行时软件

- [Three.js](https://github.com/mrdoob/three)：MIT；预览通过CDN加载固定版本`0.181.0`，未vendoring库本体。
- [CadQuery](https://github.com/CadQuery/cadquery)：Apache-2.0；经安装包提供，不随发布ZIP打包运行库。
- 其他依赖由包管理器按各自许可安装，冻结版本见`requirements.lock`。

原始R6失败与后续改动记录保留在历史发布和验证资料中。来源、几何检查和实物验收分别记录，不能用公开模型的省略来宣布整机通过或制造放行。

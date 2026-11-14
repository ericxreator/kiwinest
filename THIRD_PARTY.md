# 来源、致谢与未分发材料

核对日期：2026-11-14（Asia/Singapore）。本项目仅发布原创参数化代码、机箱零件、工程代理与说明。下列参考来源不因被引用而获得本项目许可证。

## 结构思路参考

| 来源 | 固定参考版本 | 使用边界 |
| --- | --- | --- |
| [thunder439/QNAS7](https://github.com/thunder439/QNAS7) | `27e5919ad2c74ecf2df49603879b9dd32447d121` | 结构思路参考；不分发其 STEP、STL、照片或源码 |
| [thunder439/QNAS8](https://github.com/thunder439/QNAS8) | `492cbcc55a5f0c1f36b2798a21b64ffed85c3c4a` | 紧凑布局参考；不分发其 STEP、STL、照片或源码 |

核对的上游根目录未见明确 LICENSE；不据此推定任何再分发或改许可授权。当前40个箱体零件与电源法兰使用数值参数和基础几何重新构造，没有导入上游几何。

## 硬件尺寸与原厂模型

- [ADT-Link R23](https://www.adtlink.cn/en/product/R23.html)：R7完整本地审阅使用原厂 R23SR 端头模型（R6历史使用R83SL）；公开仓库、GLB、HTML 和发布包均不包含该几何。下载脚本只提供用户自行获取和本地提取的途径，输入 SHA 与 URL 见脚本。
- [Enhance ENP-7660B 原厂规格](https://www.enhanceusa.com/upload/DM/202510080638420.pdf)：机身、安装与固定线束尺寸来源；PDF 不分发。`references/original/native-mechanical.json` 为工程尺寸的事实性转录，不是原厂图纸。
- [Seagate IronWolf 100844482 Rev F](https://www.seagate.com/files/www-content/product-content/ironwolf/en-us/docs/100844482f.pdf)：3.5 英寸硬盘尺寸、原生安装孔及螺钉进入深度参考；PDF 不分发。
- [Zotac ZT-B50620H-10M 规格](https://www.zotac.com/download/mediadrivers/External/GraphicsCard/5060Ti/Brochure/ZT-B50620H-10M-brochure.pdf)：显卡外包络参考；仓库 GPU 实体为自行构造的保守代理，不是 Zotac CAD。
- PCI-SIG CEM 3.0 Fig. 6-3：卡边机械尺寸参考；规范文件不分发，仓库仅含自行构造的接口代理。
- DS_2501 主板：接口坐标由参考照片估计，照片不分发，板版次、针脚、电流与实物尺寸仍须确认。

各产品名、商标和资料属于各自权利人，不表示其对本项目的认可。Noctua、ITW、Phanteks、Akasa、StarTech 等名称仅用于型号选择与接口说明，未打包其原厂图片或资料。

[Phanteks标准延长线](https://phanteks.com.tw/Extension-Cables.html)提供PH-CB4P_BK 4pin主板延长线的500mm规格；这是产品目录参考，未确认即时库存或交期。

## 运行时软件

- [Three.js](https://github.com/mrdoob/three)：MIT；预览从 jsDelivr 加载固定版本 `0.181.0`，库本体没有 vendoring。
- [CadQuery](https://github.com/CadQuery/cadquery)：Apache-2.0；经安装包提供，源码与运行库不随发布 ZIP 打包。
- 其他依赖由包管理器依据各自许可安装，冻结版本见 `requirements.lock`。

公开装配将两个原厂端头连同其全部 accessor 数据剔除；不能把省略模型后的视觉净空解释为原设计通过。原始失败在 `evidence/r6-review.json` 与已知问题中保留。

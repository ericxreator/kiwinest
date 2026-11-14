# 当前原创 CAD

本目录的原创机箱零件、金属法兰与工程代理采用 **CC BY 4.0**；作者 ericxreator，项目 https://github.com/ericxreator/kiwinest 。许可正文见 `../LICENSES/CC-BY-4.0.txt`。

`parts/` 内40个R7零件各有STEP与STL。部分文件名沿用R6工程标识，当前几何与检查版本以 `../evidence/current-review.json` 为准。文件未自动安排打印朝向、支撑或切片；BOM材料仅为原型建议，不能把网格有效当成可直接量产。

`PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT.step` 与同名用途DXF是1mm金属法兰，不能用普通打印件替代。

`kiwinest-public.glb` 为原创箱体、五金与线缆工程代理，省略两个第三方端头且移除它们的二进制数据。完整检查使用含原厂端头的本地模型；公开可见模型不能单独构成碰撞或制造结论。请先读 `../docs/known-issues.md`。

R7电源基座包含底部开口的GPU线U形槽，成品线从开口侧放入并用可拆软绑带固定；绑带材料、保持力与密封尚待实物验证。GPU上拔前需松绑并把原厂300mm线自由段前移停放，不能按静态走线直接上拔。分体线道屋顶维护还需支撑主板/电源并拆顶框，顶框完整拆出动作尚未验证。ATX24原厂出口过渡、线长测法、打印强度与热接受仍是明确的未完成项。

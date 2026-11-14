# 外部参考与原创代理

`original/` 只包含项目自行构造的 GPU 包络、I/O 安装耳、PCIe 卡边机械代理，以及电源机械尺寸的事实性转录。这些代理不是原厂精确 CAD，也不能替代实物合板与接口核对。

原厂 R83SL CAD 和 ENP-7660B PDF **没有包含在此公开仓库中**。完整本地重建需要先运行：

```sh
python scripts/prepare_references.py
python design/r6_export.py
```

准备脚本校验已记录的原厂 ZIP/PDF SHA-256，仅读取 ZIP 中明确指定的 R83SL STEP，再提取两端。下载、提取和回执只写入 Git 忽略的 `private/`。原厂文件依其各自条款使用，项目许可证不授予原厂材料的再分发权。

断网环境可以将已有原厂文件作为输入，校验要求不变：

```sh
python scripts/prepare_references.py --adt-archive /path/to/ADT_R83_3D.zip --psu-pdf /path/to/enp7660b-official-spec-20251008.pdf
```

重建生成的 `out-r6/` 含原厂几何，只供本地审阅，已由 `.gitignore` 排除。公开发布应只包含经审查的原创零件与源码。即使本地导出成功，R6 仍保留转接线端头与 CPU 40mm 保护空间干涉的失败结论；这不是打印、采购或制造放行。

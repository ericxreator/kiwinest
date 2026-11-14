# KiwiNest

A compact, parametric three-drive home-server chassis: 250 × 250 × 275mm including feet, approximately 17.19L. Mini-ITX reference board, discrete GPU, fixed-wire Flex PSU, direct SATA cabling and independent bottom-to-top cooling.

![KiwiNest R7 CAD preview](docs/kiwinest-r7.png)

**R7 remains an engineering prototype awaiting physical validation.** It retains the 5825U reference board and 40mm CPU envelope, using the shorter ADT-Link R23SR with a deliberate **PCIe 3.0 x4** link. This reduces link bandwidth from the planned x8; application performance and stability require hardware tests. EPS/GPU cable budgets include exit segments, connector allowances and assembly slack, with split channels and a bottom-open U-channel for the factory GPU lead. The fresh integrated CAD run passes all 23 check groups; all 40 print meshes are watertight and STEP round-trip preserves 623 solids. See the [actual current checks](evidence/current-review.json) and [R7 changes](docs/r7-changes.md).

Board dimensions, received cables, PCIe slot power/link stability, printed load/creep, thermal and noise acceptance remain incomplete. The factory ATX24 transition from the PSU face to its assumed cable exit is not fully modeled. CAD results cover the declared modeled scope and remain separate from manufacturing acceptance. R6 is preserved at tag `v0.1.0-r6`.

- [Download STEP/STL and source](https://github.com/ericxreator/kiwinest/releases)
- [View the interactive model online](https://ericxreator.github.io/kiwinest/)
- 40 original chassis parts in [`cad/parts/`](cad/parts/), plus a separate sheet-metal PSU flange.
- Download and open [`docs/preview.html`](docs/preview.html) for the interactive CAD viewer. It needs an internet connection for pinned Three.js modules.
- Original source: [`design/`](design/). Parts lists: [`bom/`](bom/). Current checks: [`evidence/current-review.json`](evidence/current-review.json).

For a local rebuild, use Python 3.13 and install `requirements.lock`, run `python scripts/prepare_references.py`, then `python design/r6_export.py`. Manufacturer references are checksum-verified and kept in the ignored `references/private/` directory. Local full-assembly outputs contain those references and are not distributable project artifacts.

Public previews omit the two manufacturer connector models, including their unused binary data. Checks use the complete local manufacturer geometry; an omission in the public viewer never establishes clearance. Component proxies are planning references, not manufacturer mechanical CAD or compatibility certification.

GPU removal requires power-off, removal of the top cover/fan and parking of the unplugged 8pin extension head. Release the bottom soft straps and feed the reserved slack to park the free span of the factory 300mm GPU lead toward the front, keeping its coupling fixed, before releasing the bracket and lifting the card. Physical cable deformation, retention and the parking motion remain unverified.

Inspired by [QNAS7](https://github.com/thunder439/QNAS7) / [QNAS8](https://github.com/thunder439/QNAS8); their files are not redistributed. See [third-party sources](THIRD_PARTY.md), [known issues](docs/known-issues.md), and the [Chinese documentation](README.md) for dimensions and service procedures.

Original source code: MIT. Original CAD and design documentation: CC BY 4.0. Copyright © 2026 ericxreator. See [`LICENSES/README.md`](LICENSES/README.md) for scope.

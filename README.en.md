# KiwiNest

A compact parametric three-drive home-server chassis: 250 × 250 × 275mm including feet, approximately 17.19L. Mini-ITX reference board, discrete GPU, fixed-wire Flex PSU, direct SATA cabling and independent cooling.

![KiwiNest R8 CAD preview](docs/kiwinest-r8.png)

**Current version: `v0.3.0-r8` engineering prototype. All 25 CAD check groups pass; physical and manufacturing acceptance remain pending.** It retains the 5825U reference board, 40mm CPU envelope and x8 electrical requirement, using K83UP-TL endpoints with a custom insulating clamp. Minimum nominal CPU-envelope clearance across the male and its mounts is 2.311mm. The selected 50cm cable comprises a complete 464mm free bundle and two retained 18mm sleeves, including 49.213mm of geometric loop allocation relative to a compact route in the same family. The complete factory ATX transition starts at the engineering PSU-face datum. All 22 power, PWM/control and SATA budgets retain at least 20mm after connector allowances and assembly slack, with a minimum of 21.770mm; all extension surplus enters shared storage calculations. See the [actual checks](evidence/current-review.json) and [R8 changes](docs/r8-changes.md) for scope and bounded contact allowances.

Full STEP readback is valid at 731/731 solids, and all 40 printable meshes are watertight. Public geometry byte checks and desktop/mobile viewport browser checks pass; the mobile check is not a physical-phone test. The PCIe x8 bundle's geometric projection onto the bottom-fan disk is 9.3943%, which does not measure airflow loss, pressure drop or thermal performance. See the [publication checks](evidence/publication-verification.json).

The earlier R83 front mounting ear/fastener entered the CPU clearance volume because of its shape and orientation. Eight electrical lanes do not inherently cause that collision. The custom clamp preserves the vendor PCB, contacts, complete fanout and upper bar, retaining the middle/rear M2 fasteners while replacing the lower bar/front fastener with an original FR4/electrically insulating silicone foam assembly. The retained M2 fasteners point upward with their heads below and require bench preassembly. Both lower motherboard mounts 2/4 use original OD9 × 1.5mm steel countersunk bearing washers and M3x8 countersunk screws, preserving the board/standoff datum and adjustment bores. Local PCB geometry is checked; bearing loads, tolerances, clamp preload and x8 negotiation still require validation.

Cut only the outline and two holes in 1.5mm foam stock. Public fabrication assets provide an independently generated flat-stock STEP/DXF. Its nominal 1.4mm compressed envelope incorporates vendor-derived surfaces and stays local to the fit checks; it is not a machining profile for grooves. Checks allow bounded local soft-pad preload, rather than claiming every contact volume is zero. Foam compression, preload and rebound remain unverified. Retained factory M2 fasteners move only about 0.400mm along their original axes; the upper-bar CAD has unthreaded 2.2mm bores, so actual retention and insertion require inspection. Male-clamp service requires releasing the carrier and cable restraints and moving the assembly out before accessing the screw heads. In-place tool access and the complete combined removal path remain unverified.

The complete factory socket latch must be reversibly removed and stored in a keeper integrated into the bridge, secured by an M2x25 cross-pin and captured M2 nut. All factory latch material is retained; the GPU is held by its I/O ears, guides and upper clamp. This requires modified assembly, with physical disassembly, retention, load and link tests still pending.

- [Download STEP/STL and source](https://github.com/ericxreator/kiwinest/releases)
- [Interactive model](https://ericxreator.github.io/kiwinest/)
- Original printable parts: [`cad/parts/`](cad/parts/); separate FR4, insulating silicone foam, steel bearing-washer and sheet-metal fabrication: [CAD notes](cad/README.md) and [`bom/`](bom/).
- Download and open [`docs/preview.html`](docs/preview.html). It needs a network connection for pinned Three.js modules.
- [Source](design/), [known issues](docs/known-issues.md), [third-party references](THIRD_PARTY.md), [Chinese documentation](README.md).

Use Python 3.13 and the locked dependencies. The stable source-module names still use `r6_`, while revision is recorded in the exported parameters:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
python scripts/prepare_references.py
python design/r6_export.py --out-dir out-r8
python scripts/build_public_assets.py --input out-r8
python scripts/build_public_bom.py --input out-r8/report.json
python scripts/airflow_projection.py --cables-dir out-r8/cables --pattern 'CABLE_R8_K83*.step' --output evidence/airflow-current.json
```

Manufacturer inputs are checksum-verified and remain in ignored `references/private/`. Full local outputs in `out-r8/` contain those inputs and are not distributable artifacts. Public previews omit three nodes: both manufacturer endpoints and the vendor-derived compressed-foam surface, including all their unused binary data. Public foam fabrication files instead describe an independent 1.5mm flat blank. Checks use the actual complete local geometry; public omissions never establish clearance.

GPU removal still requires power-off, removal of the top cover/fan and parking of the unplugged card-side 8pin head/free extension tail before releasing the bracket and lifting the card. The factory 300mm lead and its fixed coupling stay outside the extraction space; R7's factory-lead forward-parking step is retired. Disk3 service releases its local flexible tail while the fourth SATA coupling and the hub extension remain fixed.

Received board dimensions, factory exit coordinates, cables, surplus packing, custom-clamp loads, PCIe slot power/link stability, printed load/creep, temperature and noise remain unaccepted. Complete ATX CAD does not certify a measured factory exit. Each first SATA factory A/B segment reserves 10.5mm for its unmodeled PSU-face transition; its source geometry/isolation is not certified by the completed ATX model. Manufacturing and physical acceptance remain separate from CAD results. Earlier releases are retained at `v0.1.0-r6` and `v0.2.0-r7`.

Inspired by [QNAS7](https://github.com/thunder439/QNAS7) / [QNAS8](https://github.com/thunder439/QNAS8); their files are not redistributed. Original source code: MIT. Original CAD/design documentation: CC BY 4.0. Copyright © 2026 ericxreator. See [`LICENSES/README.md`](LICENSES/README.md) for scope.

# Thermo shared circuit generator

Circuit-only copy of `hardware/24ch/gen/`, parameterized by `gen/boards.py`.
The original 24-channel folder remains unchanged. No placement, routing, PCB,
fabrication or `pcbnew` tools were copied. The 8-channel configuration is REV B0.
The owner's task brief supplies decision 0039; its file is absent in this checkout.
40-channel / RTD work remains with the orchestrator.

From the repository root, **outside the Codex sandbox**, run:

```powershell
pwsh -NoProfile -File hardware/family/gen/gate.ps1
```

The gate uses `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` and ordinary
Python (`-Python <absolute-python-path>` overrides PATH). It does not need KiCad's
Python. `-Release <release-directory>` overrides the supplied 4b1601 release.
Exit 0 and `FAMILY GATES: PASS` mean every required stage passed. Any missing tool,
failed build/export, original-vs-release discrepancy, family-vs-release discrepancy,
uncaught deliberate fault or change to `hardware/24ch/` fails the gate.
A baseline discrepancy stops the 8-channel build and the scratch fault proof.

Each run writes `out/gate-<timestamp>/`, including per-stage logs, ERC reports,
exported XML, BOM/DNP files, comparison SHA256 manifests and `gate-summary.txt`.
Gate A requires zero ERC messages, zero pin mismatches/missing parts and zero
release differences for the original and shared 24-channel generators. Gate B
requires zero ERC messages, zero pin mismatches/missing parts and A4/A3 pages only.
The fault proof separately changes R111's value, swaps R111 pins 1/2 and removes
C111 in three scratch builds. It checks for the corresponding component/net
messages, rather than accepting just any nonzero result.

Individual entry points (all KiCad-dependent commands run by the orchestrator):

```powershell
python -B hardware/family/gen/build.py 24 --out hardware/family/out/24
python -B hardware/family/gen/build.py 8 --out hardware/family/out/8
python -B hardware/family/gen/compare_release.py hardware/family/out/24 D:\tasks\thermo\production\24ch-reva3-20261014-072946-4b1601
python -B hardware/family/gen/fault_proof.py hardware/family/out/faults D:\tasks\thermo\production\24ch-reva3-20261014-072946-4b1601
```

Comparison independently reads exported XML, retaining every component field,
value, footprint and DNP/exclusion flag; it compares all pin membership and net
names. Only known sheet-path prefixes and automatic unconnected names are
normalized. Separate net partitions remain separate, so a split net is detected.
BOM grouping/order/exclusions exactly follow `24ch/gen/fab.py`. No generator model
is imported by the comparator. SHA256 records cover schematic sets, project,
local library/tables and release XML/BOM/DNP inputs, plus the new exported XML.

Plain-Python tests (safe inside the sandbox):

```powershell
python -B hardware/family/gen/test_family.py
python -B docs/check_docs.py
```

The tests compare complete 24-channel model records to the original source,
verify the exact 8-channel subset and isolator/MCU pins, and exercise field,
footprint, flag, component, pin, net-name, partition and BOM differences.
Generation/pagination itself uses plain Python and library files; `build.generate`
can write a scratch schematic without invoking KiCad. Export/ ERC still need KiCad.

Offline prices are optional: `gate.ps1 -PriceCache <cost.csv>` accepts a saved
`24ch/gen/cost.py` cache. With no cache the gate explicitly prints `UNAVAILABLE`;
no network request or estimated current price is substituted. Partial caches
print an incomplete subtotal. Assembly, stock and price freshness are unverified.

The orchestrator must ignore **`hardware/family/out/`**. Python cache paths are
already ignored globally. This sandbox cannot write `.gitignore` files.

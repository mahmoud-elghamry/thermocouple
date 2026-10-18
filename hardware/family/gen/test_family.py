"""Plain-Python regression checks; never start KiCad or import pcbnew."""
import ast
import copy
import importlib
import json
import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from boards import B24, B8, CS24, CS8
from bom import grouped_bom
from c_bank import bank
from c_iso import isolation
from c_mcu import mcu
from c_out import outputs
from c_power import power
from compare_release import compare_roots, compare_rows

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def model(config):
    sheets = [power(), mcu(config), isolation(config), outputs()]
    sheets += [bank(i, config) for i in range(1, config.bank_count + 1)]
    return {p.ref: vars(p) for sheet in sheets for p in sheet.parts()}


class FamilyTests(unittest.TestCase):
    def test_source_syntax_and_imports(self):
        for path in HERE.glob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if path.stem != "test_family":
                importlib.import_module(path.stem)
        self.assertNotIn("pcbnew", sys.modules)

    def test_24_model_identical_to_original(self):
        code = """
import json, sys
sys.path.insert(0, sys.argv[1])
from c_bank import bank
from c_iso import isolation
from c_mcu import mcu
from c_out import outputs
from c_power import power
sheets = [power(), mcu(), isolation(), outputs(), bank(1), bank(2), bank(3)]
print(json.dumps({p.ref: vars(p) for s in sheets for p in s.parts()}, sort_keys=True))
"""
        r = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "hardware/24ch/gen")],
                           capture_output=True, text=True, check=True)
        self.assertEqual(model(B24), json.loads(r.stdout))

    def test_8_exact_requested_subset(self):
        a, b = model(B24), model(B8)
        removed = {r for r in a if len(r.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) == 3
                   and r.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[0] in "23"}
        removed |= {"U405", "C411", "C412", "R431", "R432", "R435", "R436", "R437", "R438", "R443",
                    "R191"}                                              # SYNC tied high (0039 P8)
        self.assertEqual(set(a) - set(b), removed)
        added = {"U411", "C421", "R445", "R446", "R447", "R439"}     # gated SIO driver (0039, I-124)
        self.assertEqual(set(b) - set(a), added)
        for ref in set(b) - added:
            actual, expected = copy.deepcopy(b[ref]), copy.deepcopy(a[ref])
            if expected["lib_id"].startswith("thermo24:"):
                expected["lib_id"] = expected["lib_id"].replace("thermo24:", "thermo8:")
            if ref == "U501":
                expected["_nets"] = B8.mcu_pins
            elif ref in ("U403", "U404"):
                expected["_nets"] = actual["_nets"]  # separately checked below
            elif ref == "U101":
                expected["_nets"] = dict(expected["_nets"], SYNC="+3V3_ISO")
            elif ref in ("U102", "U103"):
                expected["desc"] = expected["desc"].replace("R443", "the gated SIO driver U411 (0039)")
            elif ref == "R427":
                expected["desc"] = expected["desc"].replace("24 R_b", "8 R_b")
            self.assertEqual(actual, expected, ref)
        self.assertEqual(dict(B8.mounting_holes), {**dict(B24.mounting_holes), 4: "plain"})
        self.assertEqual(B8.cs_pullups, (("R430", "CS_ADC1"), ("R433", "CS_CJ1"), ("R434", "CS_CJ2"),
                                         ("R439", "SIO_WR_N")))
        unused = {p for p, n in B24.mcu_pins.items() if n in set(CS24) - set(CS8)} - {"PC1"}
        self.assertEqual(unused, {"PB0", "PB1", "PC3", "PC4", "PC5"})
        self.assertEqual({p for p, n in B8.mcu_pins.items() if n == "<NC>"}, unused)
        self.assertEqual(B8.mcu_pins["PC1"], "SIO_WR_N")
        for ref, ins, outs, fout, fin in (
            ("U403", ("SCK", "MOSI", "CS_ADC1", "CS_CJ1", "CS_CJ2"),
             ("SCLK_ISO_RAW", "DIN_ISO_RAW", "CS_ADC1_ISO", "CS_CJ1_ISO", "CS_CJ2_ISO"),
             "MISO_ISO", "DOUT_ISO_RAW"),
            ("U404", ("REFTEST", "SIO_WR_N", "GND", "GND", "GND"),
             ("REFTEST_ISO", "SIO_WR_N_ISO", "<NC>", "<NC>", "<NC>"), "REFOK", "REFOK_ISO")):
            nets = b[ref]["_nets"]
            want = {"Vcc1": "+5V", "GND1": "GND", "Vcc2": "+3V3_ISO", "GND2": "GND_ISO",
                    "OUTF": fout, "INF": fin}
            want.update({"IN"+c: n for c, n in zip("ABCDE", ins)})
            want.update({"OUT"+c: n for c, n in zip("ABCDE", outs)})
            self.assertEqual(nets, want)

    def test_comparator_faults_and_flags(self):
        text = '<export><design><sheet name="/BANK_A/"/></design><components><comp ref="R1"><value>10k</value><footprint>R:R</footprint>'
        text += '<fields><field name="MPN">part1</field></fields></comp></components>'
        text += '<nets><net name="/BANK_A/N"><node ref="R1" pin="1"/></net>'
        text += '<net name="GND"><node ref="R1" pin="2"/></net></nets></export>'
        root = ET.fromstring(text)
        self.assertEqual(compare_roots(root, copy.deepcopy(root)), [])
        for fault, marker in (("value", "R1 value"), ("pin", "NET"), ("removed", "missing R1"),
                              ("field", "field:MPN"), ("footprint", "footprint"),
                              ("dnp", "dnp"), ("exclude_from_bom", "exclude_from_bom"),
                              ("exclude_from_board", "exclude_from_board")):
            mutated = copy.deepcopy(root)
            c = mutated.find("components/comp")
            if fault == "value":
                c.find("value").text = "100k"
            elif fault == "pin":
                mutated.find("nets/net/node").set("pin", "2")
                mutated.findall("nets/net")[1].find("node").set("pin", "1")
            elif fault == "removed":
                mutated.find("components").remove(c)
            elif fault == "field":
                c.find("fields/field").text = "part2"
            elif fault == "footprint":
                c.find("footprint").text = "R:other"
            else:
                ET.SubElement(c, "property", name=fault)
            self.assertTrue(any(marker in d for d in compare_roots(mutated, root)), fault)
        self.assertTrue(compare_rows([["a"]], [["b"]]))

    def test_net_names_and_partitions(self):
        def r(nets):
            return ET.fromstring('<export><design><sheet name="/S1/"/><sheet name="/S2/"/></design>'
                                 '<components/><nets>' + nets + '</nets></export>')
        a = r('<net name="/S1/N"><node ref="R1" pin="1"/></net>')
        self.assertEqual(compare_roots(a, r('<net name="/S2/N"><node ref="R1" pin="1"/></net>')), [])
        self.assertTrue(compare_roots(a, r('<net name="/S2/M"><node ref="R1" pin="1"/></net>')))
        a = r('<net name="/S1/N"><node ref="R1" pin="1"/><node ref="R2" pin="1"/></net>')
        b = r('<net name="/S1/N"><node ref="R1" pin="1"/></net>'
              '<net name="/S2/N"><node ref="R2" pin="1"/></net>')
        self.assertTrue(compare_roots(a, b))
        a = r('<net name="/S1/group/N"><node ref="R1" pin="1"/></net>')
        b = r('<net name="/S2/other/N"><node ref="R1" pin="1"/></net>')
        self.assertTrue(compare_roots(a, b))
        a = r('<net name="unconnected-old"><node ref="U1" pin="1"/></net>')
        b = r('<net name="/S2/unconnected-new"><node ref="U1" pin="1"/></net>')
        self.assertEqual(compare_roots(a, b), [])
        b.find("nets/net/node").set("pin", "2")
        self.assertTrue(compare_roots(a, b))

    def test_model_counts(self):
        from build import root_parts
        import build
        for config, count, bom_lines, fitted in ((B24, 463, 95, 442), (B8, 264, 92, 243)):
            build.CONFIG = config
            parts = model(config)
            parts.update({p.ref: vars(p) for p in root_parts()})
            root = ET.Element("export")
            for ref, part in parts.items():
                comp = ET.SubElement(root, "comp", ref=ref)
                ET.SubElement(comp, "value").text = part["value"]
                ET.SubElement(comp, "footprint").text = part["footprint"]
                fields = ET.SubElement(comp, "fields")
                for name, key in (("MPN", "mpn"), ("LCSC", "lcsc")):
                    ET.SubElement(fields, "field", name=name).text = part[key]
            rows, _ = grouped_bom(root)
            print(f"MODEL {config.key}: {len(parts)} components; {len(rows)-1} BOM lines; "
                  f"{sum(int(r[-1]) for r in rows[1:])} fitted parts")
            self.assertEqual(len(parts), count)
            self.assertEqual(sum(int(r[-1]) for r in rows[1:]), fitted)
            self.assertEqual(len(rows)-1, bom_lines)
        build.CONFIG = B24

    def test_bom_matches_original_fab(self):
        root = ET.fromstring('<export><components><comp ref="R2"><value>1k</value>'
                            '<footprint>R:R_0805</footprint><fields><field name="LCSC">C1</field>'
                            '<field name="MPN">X</field></fields></comp>'
                            '<comp ref="R1"><value>1k</value><footprint>R:R_0805</footprint>'
                            '<fields><field name="LCSC">C1</field><field name="MPN">X</field></fields></comp>'
                            '<comp ref="C1"><footprint>C:C</footprint><property name="dnp"/></comp>'
                            '<comp ref="TP1"><footprint>T:T</footprint></comp></components></export>')
        rows, dnp = grouped_bom(root)
        self.assertEqual(rows[1:], [["1k", "R1,R2", "R_0805", "C1", "X", "2"]])
        self.assertEqual(dnp, ["C1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

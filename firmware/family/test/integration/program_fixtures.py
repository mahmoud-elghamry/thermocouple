"""Independent HEX/record/CRC fixtures; never invoke a physical programmer."""
import binascii
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from image_metadata import IDENTITY_ADDRESS, MAGIC, MCU_SIGNATURE, repo_commit


def record(address, kind, data):
    raw = bytes([len(data), address >> 8, address & 255, kind]) + data
    return ":" + (raw + bytes([-sum(raw) & 255])).hex().upper() + "\n"


root = Path(sys.argv[1])
current = repo_commit()
old = ("0" if current[0] != "0" else "1") + current[1:]
names = ("fixture", "clean", "tiny", "tiny-with-record", "old", "legacy", "other-mcu", "missing-record",
         "unpatched", "wrong-crc", "identity-crc", "identity-sidecar", "identity-magic",
         "changed", "missing", "bad-checksum")
for name in names:
    commit = old if name == "old" else current
    dirty = name not in ("old", "clean")
    body = bytes(range(64)) if name in ("tiny", "tiny-with-record") else bytes(range(256)) * 2
    identity = MAGIC + bytes([24]) + MCU_SIGNATURE + bytes([1, 0, 0, dirty])
    identity += commit.encode("ascii") + bytes(36)
    if name == "legacy":
        identity = identity[:8] + bytes([8]) + identity[9:]
    if name == "other-mcu":
        identity = identity[:11] + bytes([identity[11] ^ 1]) + identity[12:]
    if name == "identity-magic":
        identity = bytes([identity[0] ^ 1]) + identity[1:]
    present = name not in ("tiny", "missing-record")
    crc = binascii.crc_hqx(body + (identity if present else b""), 0xFFFF)
    assert crc != 0xFFFF  # The unpatched fixture differs from an erased CRC word.
    if name == "identity-crc":
        identity = identity[:14] + bytes([1]) + identity[15:]  # retain old stored CRC
    data = "".join(record(a, 0, body[a:a + 16]) for a in range(0, len(body), 16))
    data += record(0, 4, bytes([0, 1]))
    if present:
        data += "".join(record((IDENTITY_ADDRESS & 0xFFFF) + a, 0, identity[a:a + 16])
                        for a in range(0, len(identity), 16))
    stored = 0xFFFF if name == "unpatched" else crc
    data += record(0xFFFE, 0, stored.to_bytes(2, "little")) + record(0, 1, b"")
    if name == "bad-checksum":
        first, rest = data.split("\n", 1)
        data = first[:-2] + f"{int(first[-2:], 16) ^ 1:02X}\n" + rest
    path = root / (name + ".hex")
    path.write_text(data, encoding="ascii")
    claim = dict(board=24, mcu="atmega1284p", firmware_version="1.0.1" if name == "identity-crc" else "1.0.0",
                 commit=old if name == "identity-sidecar" else commit, dirty=dirty)
    metadata = dict(format="thermo-production-v2", board=24, mcu="atmega1284p",
                    image=path.name, byte_count=len(body) + (64 if present else 0),
                    crc16=crc ^ (1 if name == "wrong-crc" else 0), identity=claim,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    sidecar = path.with_suffix(".hex.json")
    if name != "missing":
        sidecar.write_text(json.dumps(metadata))
    else:
        sidecar.unlink(missing_ok=True)
    if name == "changed":
        path.write_text(data + "\n", encoding="ascii")
(root / "profile.elf").write_bytes(b"\x7fELF simulator")
metadata.update(image="profile.elf", sha256=hashlib.sha256((root / "profile.elf").read_bytes()).hexdigest())
(root / "profile.elf.json").write_text(json.dumps(metadata))

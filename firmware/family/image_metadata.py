"""Production HEX identity and boot CRC, shared by build and programming tools.

Metadata binds an artifact to its build; it is not a cryptographic signature.
"""
import argparse
import binascii
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = (ROOT / "include/app/image_identity.h").read_text()


def constant(name):
    return int(re.search(r"#define\s+" + name + r"\s+(0x[0-9A-Fa-f]+|\d+)", HEADER)[1], 0)


IDENTITY_ADDRESS = constant("APP_IDENTITY_ADDRESS")
IDENTITY_BYTES = constant("APP_IDENTITY_BYTES")
MAGIC = re.search(r'#define APP_IDENTITY_MAGIC "([^"]+)"', HEADER)[1].encode("ascii")
MCU_SIGNATURE = bytes(constant("APP_IDENTITY_MCU_" + str(i)) for i in range(3))


def repo_commit():
    commit = subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT),
                                      "rev-parse", "HEAD"], text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ValueError("Cannot establish current repository HEAD")
    return commit[:12]


def embedded_identity(memory):
    try:
        record = bytes(memory[IDENTITY_ADDRESS + i] for i in range(IDENTITY_BYTES))
    except KeyError as error:
        raise ValueError("Embedded firmware identity missing") from error
    if record[:8] != MAGIC or record[8] != 24 or record[9:12] != MCU_SIGNATURE:
        raise ValueError("Embedded identity is not 24-channel ATmega1284P production firmware")
    if (record[15] not in (0, 1) or record[28] != 0 or any(record[29:]) or
            not re.fullmatch(b"[0-9a-f]{12}", record[16:28])):
        raise ValueError("Invalid embedded firmware identity record")
    return dict(board=record[8], mcu="atmega1284p",
                firmware_version=".".join(map(str, record[12:15])),
                commit=record[16:28].decode("ascii"), dirty=bool(record[15]))


def image_bytes(path):
    if path.suffix.lower() != ".hex":
        raise ValueError("Only a production Intel HEX image is programmable")
    memory = {}
    base = 0
    eof = False
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        if eof or not line.startswith(":"):
            raise ValueError("Malformed HEX record or data after EOF")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) & 255:
            raise ValueError("HEX length/checksum mismatch")
        length, address, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        data = record[4:-1]
        if kind == 0:
            for offset, value in enumerate(data):
                target = base + address + offset
                if target >= 0x20000 or target in memory:
                    raise ValueError("Out-of-range or overlapping HEX data")
                memory[target] = value
        elif kind == 1 and length == 0 and address == 0:
            eof = True
        elif kind in (2, 4) and length == 2 and address == 0:
            base = int.from_bytes(data, "big") << (4 if kind == 2 else 16)
        elif kind not in (3, 5) or length != 4 or address != 0:
            raise ValueError("Unsupported HEX record")
    if not eof:
        raise ValueError("Missing HEX EOF")
    return memory


def verify_payload(path, count, expected):
    if type(count) is not int or not 0 < count <= 98302:
        raise ValueError("Invalid production byte count")
    if type(expected) is not int or not 0 <= expected <= 65535:
        raise ValueError("Invalid CRC16 metadata")
    memory = image_bytes(path)
    identity = embedded_identity(memory)
    body_count = count - IDENTITY_BYTES
    if body_count < constant("APP_IMAGE_VECTOR_BYTES") or set(memory) != (set(range(body_count)) |
            set(range(IDENTITY_ADDRESS, IDENTITY_ADDRESS + IDENTITY_BYTES)) | {0x1FFFE, 0x1FFFF}):
        raise ValueError("Production extent/CRC bytes missing or extra image data")
    # Same two programmed spans as flash_crc(): code/data, then identity.
    covered = bytes(memory[a] for a in range(body_count))
    covered += bytes(memory[IDENTITY_ADDRESS + i] for i in range(IDENTITY_BYTES))
    calculated = binascii.crc_hqx(covered, 0xFFFF)
    stored = memory[0x1FFFE] | memory[0x1FFFF] << 8
    if calculated != expected or stored != calculated:
        raise ValueError("Stored boot CRC at 0x1FFFE does not match the image")
    return identity


def write_metadata(path, count, crc):
    identity = verify_payload(path, count, crc)
    metadata = dict(format="thermo-production-v2", board=24, mcu="atmega1284p",
                    image=path.name, byte_count=count, crc16=crc,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(), identity=identity)
    path.with_suffix(path.suffix + ".json").write_text(json.dumps(metadata, indent=2) + "\n")


def check_metadata(path, release=False):
    metadata = json.loads(path.with_suffix(path.suffix + ".json").read_text())
    if (metadata["format"] != "thermo-production-v2" or metadata["board"] != 24 or
            metadata["mcu"] != "atmega1284p" or metadata["image"] != path.name):
        raise ValueError("Not a production 24-channel image")
    if metadata["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("HEX SHA-256 does not match build metadata")
    identity = verify_payload(path, metadata["byte_count"], metadata["crc16"])
    if metadata["identity"] != identity:
        raise ValueError("Sidecar identity does not match embedded firmware identity")
    if not release and identity["commit"] != repo_commit():
        raise ValueError("Embedded commit differs from repository HEAD; select an approved -Release explicitly")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--bytes", type=int)
    parser.add_argument("--crc", type=lambda s: int(s, 0))
    parser.add_argument("--release", action="store_true", help="Explicit approved release: skip only HEAD freshness")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.write:
            write_metadata(args.image, args.bytes, args.crc)
        metadata = check_metadata(args.image, args.release)
        if args.json:
            print(json.dumps(metadata))
        else:
            identity = metadata["identity"]
            state = "DIRTY" if identity["dirty"] else "CLEAN"
            print(f"Production image PASS: board 24, {identity['mcu']} v{identity['firmware_version']} "
                  f"{identity['commit']} {state}, {metadata['byte_count']} bytes, "
                  f"CRC16 {metadata['crc16']:04X}, SHA-256 verified")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Production image FAIL: {error}\n")


if __name__ == "__main__":
    main()

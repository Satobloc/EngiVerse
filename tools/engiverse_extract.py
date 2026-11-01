#!/usr/bin/env python3
"""Read-only firmware string and Intel HEX extractors. Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

TOOL_NAME = "EngiVerse Extract"
TOOL_VERSION = "0.1.0"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def printable_runs(data: bytes, min_length: int = 4):
    if min_length < 1:
        raise ValueError("min_length must be at least 1")
    start, buf = None, bytearray()
    for offset, value in enumerate(data):
        if 0x20 <= value <= 0x7E:
            if start is None: start = offset
            buf.append(value)
        else:
            if start is not None and len(buf) >= min_length:
                yield {"offset":start,"length":len(buf),"encoding":"ascii","text":buf.decode("ascii")}
            start, buf = None, bytearray()
    if start is not None and len(buf) >= min_length:
        yield {"offset":start,"length":len(buf),"encoding":"ascii","text":buf.decode("ascii")}

def decode_firmware_strings(data: bytes, min_length: int = 4, include_utf16le: bool = True):
    rows = list(printable_runs(data, min_length))
    if include_utf16le:
        start, chars = None, []
        # Try both byte alignments. UTF-16LE strings can begin at odd offsets.
        for alignment in (0, 1):
            start, chars = None, []
            for i in range(alignment, len(data)-1, 2):
                code = data[i] | (data[i+1] << 8)
                if 0x20 <= code <= 0x7E:
                    if start is None: start = i
                    chars.append(chr(code))
                else:
                    if start is not None and len(chars) >= min_length:
                        rows.append({"offset":start,"length":len(chars)*2,"encoding":"utf-16le","text":"".join(chars)})
                    start, chars = None, []
            if start is not None and len(chars) >= min_length:
                rows.append({"offset":start,"length":len(chars)*2,"encoding":"utf-16le","text":"".join(chars)})
    return sorted(rows, key=lambda r:(r["offset"],r["encoding"]))

def parse_intel_hex_line(line: str, line_number: int):
    raw = line.strip()
    if not raw: raise ValueError(f"line {line_number}: blank line")
    if not raw.startswith(":"): raise ValueError(f"line {line_number}: record must begin with ':'")
    payload = raw[1:]
    if len(payload) % 2: raise ValueError(f"line {line_number}: odd number of hex digits")
    try: rec = bytes.fromhex(payload)
    except ValueError as exc: raise ValueError(f"line {line_number}: non-hexadecimal character") from exc
    if len(rec) < 5: raise ValueError(f"line {line_number}: record shorter than 5-byte header")
    count = rec[0]
    if len(rec) != count + 5:
        raise ValueError(f"line {line_number}: byte count says {count}, record contains {len(rec)-5}")
    if sum(rec) & 0xFF:
        raise ValueError(f"line {line_number}: checksum mismatch (sum modulo 256 is 0x{sum(rec)&0xFF:02X})")
    address = (rec[1] << 8) | rec[2]
    kind, data = rec[3], rec[4:-1]
    names = {0:"data",1:"end-of-file",2:"extended-segment-address",3:"start-segment-address",4:"extended-linear-address",5:"start-linear-address"}
    if kind not in names: raise ValueError(f"line {line_number}: unsupported Intel HEX record type 0x{kind:02X}")
    if kind == 1 and (count != 0 or address != 0): raise ValueError(f"line {line_number}: EOF must have zero count and address")
    if kind in (2,4) and count != 2: raise ValueError(f"line {line_number}: address-extension record must contain 2 data bytes")
    if kind in (3,5) and count != 4: raise ValueError(f"line {line_number}: start-address record must contain 4 data bytes")
    if kind in (1,2,3,4,5) and address != 0: raise ValueError(f"line {line_number}: non-data record must have address 0")
    return {"line":line_number,"record_type":kind,"record_type_name":names[kind],"byte_count":count,
            "address":address,"data_hex":data.hex().upper(),"data_bytes":list(data),
            "checksum":rec[-1],"checksum_valid":True,"raw":raw}

def parse_intel_hex(text: str, require_eof: bool = True):
    records, eof = [], False
    for number, line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        if eof: raise ValueError(f"line {number}: content appears after EOF record")
        row = parse_intel_hex_line(line, number)
        records.append(row)
        eof = row["record_type"] == 1
    if not records: raise ValueError("input contains no Intel HEX records")
    if require_eof and not eof: raise ValueError("input is missing the required EOF record")
    return records

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    s = sub.add_parser("strings"); s.add_argument("file",type=Path); s.add_argument("--min-length",type=int,default=4); s.add_argument("--ascii-only",action="store_true")
    h = sub.add_parser("intel-hex"); h.add_argument("file",type=Path); h.add_argument("--allow-missing-eof",action="store_true")
    args = parser.parse_args()
    raw = args.file.read_bytes()
    base = {"schema_version":1,"tool":TOOL_NAME,"tool_version":TOOL_VERSION,"source":str(args.file),"source_size_bytes":len(raw),"source_sha256":sha256_bytes(raw)}
    if args.command == "strings":
        rows = decode_firmware_strings(raw,args.min_length,not args.ascii_only)
        payload = {**base,"extractor":"firmware-strings","extractor_version":"0.1.0","record_count":len(rows),"records":rows,
                   "interpretation_note":"Printable strings are byte sequences, not proof of executable behavior."}
    else:
        rows = parse_intel_hex(raw.decode("ascii"),not args.allow_missing_eof)
        payload = {**base,"extractor":"intel-hex","extractor_version":"0.1.0","record_count":len(rows),"records":rows,
                   "interpretation_note":"Record addresses are file-format fields; mapping and device meaning require separate evidence."}
    print(json.dumps(payload,indent=2,ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError,UnicodeError,ValueError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(2)

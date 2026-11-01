import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from engiverse_extract import decode_firmware_strings, parse_intel_hex, parse_intel_hex_line
SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"engiverse_extract.py"

class StringTests(unittest.TestCase):
    def test_ascii_offsets(self):
        rows=decode_firmware_strings(b"\x00BOOT\x00abc\x00READY",4,False)
        self.assertEqual([(r["offset"],r["text"]) for r in rows],[(1,"BOOT"),(10,"READY")])
    def test_utf16le_offsets(self):
        rows=decode_firmware_strings(b"\x00"+"MENU".encode("utf-16le")+b"\x00\x00",4)
        found=[r for r in rows if r["encoding"]=="utf-16le"]
        self.assertEqual([(r["offset"],r["text"]) for r in found],[(1,"MENU")])
    def test_min_length_positive(self):
        with self.assertRaises(ValueError): decode_firmware_strings(b"x",0)

class IntelHexTests(unittest.TestCase):
    def test_data_and_eof(self):
        rows=parse_intel_hex(":0201000041427A\n:00000001FF\n")
        self.assertEqual((rows[0]["address"],rows[0]["data_hex"]),(0x100,"4142"))
        self.assertTrue(rows[0]["checksum_valid"])
        self.assertEqual(rows[1]["record_type_name"],"end-of-file")
    def test_extended_linear_address(self):
        row=parse_intel_hex(":020000040800F2\n:00000001FF\n")[0]
        self.assertEqual((row["record_type_name"],row["data_hex"]),("extended-linear-address","0800"))
    def test_checksum_rejected(self):
        with self.assertRaisesRegex(ValueError,"checksum mismatch"): parse_intel_hex_line(":02010000414200",1)
    def test_count_rejected(self):
        with self.assertRaisesRegex(ValueError,"byte count"): parse_intel_hex_line(":0301000041427A",1)
    def test_unknown_type_rejected(self):
        with self.assertRaisesRegex(ValueError,"unsupported"): parse_intel_hex_line(":00000006FA",1)
    def test_eof_required(self):
        with self.assertRaisesRegex(ValueError,"missing the required EOF"): parse_intel_hex(":0100000041BE\n")
    def test_data_after_eof_rejected(self):
        with self.assertRaisesRegex(ValueError,"after EOF"): parse_intel_hex(":00000001FF\n:0100000041BE\n")

class CliTests(unittest.TestCase):
    def test_cli_hash_and_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.bin"; original=b"\x00BOOTLOADER\x00"; p.write_bytes(original)
            digest=hashlib.sha256(original).hexdigest()
            result=subprocess.run([sys.executable,str(SCRIPT),"strings",str(p)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(data["source_sha256"],digest); self.assertEqual(data["records"][0]["offset"],1)
            self.assertEqual(p.read_bytes(),original)

if __name__=="__main__": unittest.main()

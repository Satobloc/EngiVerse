# EngiVerse Extract

Version 0.1.0. Experimental, read-only extraction tools. Python 3.10+, standard library only.

## Firmware printable strings

```bash
python tools/engiverse_extract.py strings firmware.bin
python tools/engiverse_extract.py strings firmware.bin --min-length 6
python tools/engiverse_extract.py strings firmware.bin --ascii-only
```

Reports zero-based byte offsets, byte lengths, encoding, source size, and source SHA-256. It recognizes printable ASCII bytes and conservative aligned UTF-16LE printable ASCII code units. It does not infer function boundaries, code references, execution, protocol meaning, or firmware version.

## Intel HEX

```bash
python tools/engiverse_extract.py intel-hex image.hex
python tools/engiverse_extract.py intel-hex partial.hex --allow-missing-eof
```

Validates record syntax, hex encoding, byte count, checksum, record type, and structural constraints for EOF, address-extension, and start-address records. Each record retains line number, type, 16-bit address field, data, checksum, and raw line.

Not yet implemented: constructing a memory image, resolving address-extension state into absolute addresses, overlap checks, or target MCU memory-map interpretation. These must remain separate steps with source provenance.

## Evidence discipline

Fixtures in `tests/test_engiverse_extract.py` are synthetic parser tests, not firmware dumps or measurements from physical hardware. Extraction prints JSON and never modifies inputs. Printable strings are retrieval leads, not proof of executable behavior or device capability.

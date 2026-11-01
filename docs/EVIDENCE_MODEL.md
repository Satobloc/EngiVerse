# Evidence and provenance model

## Evidence classes

Use these broad classes consistently:

- `source-document`: manual, datasheet, specification, standard, publication.
- `source-code`: source repository, source file, release, commit.
- `acquired-binary`: firmware image, executable, library, filesystem image.
- `capture`: packet capture, logic trace, serial log, USB trace, instrument export.
- `image`: photograph, microscope image, radiograph, screenshot.
- `measurement`: electrical, optical, acoustic, mechanical, thermal, or dimensional result.
- `derived-data`: extracted strings, decoded structures, normalized tables, generated indexes.
- `analysis-note`: interpretation, calculation, hypothesis, or conclusion.

## Minimum record

Each evidence item should have:

| Field | Meaning |
|---|---|
| Evidence ID | Stable project-local identifier |
| Class | One of the evidence classes above |
| Description | What the item contains |
| Original path / URI | Where the original resides |
| SHA-256 | Hash of the exact file, when applicable |
| Acquired at | ISO 8601 timestamp with timezone |
| Acquired by | Person or process |
| Method | How it was obtained |
| Tool and version | Acquisition or processing tool |
| Device state | Relevant power, mode, connection, and configuration |
| Limitations | Known gaps, uncertainty, or possible contamination |
| Relations | Inputs, derivatives, corroborating items, or superseded interpretations |

## Identifiers and derivatives

Use project-local IDs such as `EV-0001`, `MEAS-0001`, and `AN-0001`. Do not reuse an ID for a different object. A derivative gets its own ID and a link to its source evidence.

## Hashing

Use SHA-256 unless a documented compatibility requirement calls for an additional digest. A hash identifies file content, not truth, authorship, safety, or correctness.

## Source hierarchy is contextual

A manufacturer document may be authoritative for its published specification but not for observed behavior. A measurement may be authoritative for one tested unit and condition but not for every revision. State what a source can and cannot establish.

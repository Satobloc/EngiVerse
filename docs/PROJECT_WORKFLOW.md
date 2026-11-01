# Project workflow

## Stage A: Define

Create a project directory from `TEMPLATES/PROJECT/`. State the target, question, scope, authorization basis, and boundaries. Identify the minimum evidence needed to answer the question.

## Stage B: Reconnaissance

Collect public documentation, product identifiers, revision markings, external dimensions, host enumeration, and observable behavior. Record exact device state and test conditions. Avoid assuming that similarly named revisions share an architecture.

## Stage C: Acquire

Create an evidence register before or during acquisition. Retain original files. Hash each acquired file. Record equipment, software versions, settings, timestamps, and any transformations.

## Stage D: Analyze

Use the narrowest suitable method. Examples include static inspection, disassembly, file-format identification, strings and symbol analysis, protocol capture, electrical measurement, board tracing, or mechanical measurement. Every derived result should point to its input evidence.

## Stage E: Correlate

Compare independent evidence sources. Separate manufacturer specifications from observed behavior. Where sources disagree, preserve the disagreement and identify possible revision, configuration, or measurement differences.

## Stage F: Conclude

Write findings with supporting evidence references, confidence, alternatives considered, and limitations. Keep unresolved questions visible.

## Stage G: Preserve and publish

Update the project README, evidence register, and decision log. Store reusable methods in `TOOLS/` only after they are separated from project-specific assumptions and tested. Cross-project conclusions belong in `RESEARCH/` and must link back to the originating projects.

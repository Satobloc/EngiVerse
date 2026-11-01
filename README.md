# EngiVerse

**A general-purpose workspace for reverse engineering, technical reconstruction, and evidence-led investigation.**

EngiVerse covers hardware, firmware, software, protocols, mechanical systems, optics, materials, and other engineered systems. Individual projects may focus on consumer devices, industrial equipment, legacy technology, or unfamiliar systems. Vape devices are one possible project domain, not the repository's defining scope.

## Working principles

1. **Evidence before interpretation.** Preserve original observations, acquired files, measurements, and source documents separately from hypotheses and conclusions.
2. **Provenance is part of the result.** Record where evidence came from, when and how it was acquired, its cryptographic hash, and any transformations applied.
3. **Reproducibility.** Prefer scripts, documented procedures, instrument settings, and machine-readable results over undocumented manual steps.
4. **Non-destructive first.** Begin with external observation, public documentation, operating-system enumeration, and non-invasive measurements. Escalate to disassembly or destructive acquisition only when justified and authorized.
5. **Explicit uncertainty.** Distinguish directly observed facts, manufacturer claims, third-party claims, measurements, interpretations, and open hypotheses.
6. **Respect boundaries.** Work only on systems and data the investigator is authorized to examine. Do not bypass access controls, extract third-party secrets, or repurpose findings for harmful access.
7. **Preserve originals.** Derived indexes, normalized data, screenshots, and analysis outputs never replace source evidence.

## Repository map

- `PROJECTS/` - bounded investigations, each with its own evidence and decision log.
- `HARDWARE/` - boards, components, schematics, power, buses, and physical architecture.
- `FIRMWARE/` - firmware images, boot chains, binary analysis, memory maps, and update mechanisms.
- `SOFTWARE/` - applications, drivers, executables, libraries, and runtime behavior.
- `PROTOCOLS/` - wired and wireless interfaces, packet formats, command sets, and state machines.
- `MECHANICAL/` - enclosures, mechanisms, materials, manufacturing, and CAD.
- `OPTICAL/` - displays, imaging, illumination, optical sensors, and related systems.
- `DOCUMENTATION/` - manuals, datasheets, service literature, standards, and reference material.
- `TOOLS/` - reusable acquisition, extraction, indexing, and analysis utilities.
- `RESEARCH/` - cross-project findings, methods, comparative studies, and technical reports.
- `TEMPLATES/` - repeatable project and evidence-record structures.

## Start here

1. Read [the operating principles](docs/OPERATING_PRINCIPLES.md).
2. Read [the project workflow](docs/PROJECT_WORKFLOW.md).
3. Copy [the project template](TEMPLATES/PROJECT/README.md) into a new directory under `PROJECTS/`.
4. Record evidence using [the evidence model](docs/EVIDENCE_MODEL.md).
5. Use [the search/index design](docs/SEARCH_AND_INDEXING.md) as the design target for repository tools.

## Status

This is the initial workspace skeleton. It establishes conventions and a project map; it does **not** yet contain a production search engine, validated acquisition tools, or completed device investigations. Tooling should be added incrementally, tested against real project evidence, and documented with versions and limitations.

## External reference policy

External repositories and documents are references, not EngiVerse-owned work. When reusing code or material, record the upstream URL, exact commit/tag or version, license, retrieval date, and local modifications. Do not imply that an upstream project is affiliated with or endorsed by EngiVerse.

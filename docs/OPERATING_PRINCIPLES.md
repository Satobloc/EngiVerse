# Operating principles

## 1. Investigation is not speculation

Start with a question that can be answered by evidence. Maintain separate fields for:

- **Observation:** what was directly seen, measured, captured, or read.
- **Source claim:** what a manufacturer, author, repository, or third party says.
- **Interpretation:** the investigator's explanation of evidence.
- **Hypothesis:** a plausible explanation that remains unverified.
- **Conclusion:** a finding supported by a stated body of evidence.
- **Unknown:** a material question not yet answered.

Do not silently promote a hypothesis into a fact.

## 2. Preserve chain of custody

Keep acquired originals immutable where practical. Compute cryptographic hashes (SHA-256 by default) at acquisition and after transfers. Record acquisition method, tool/version, timestamp and timezone, operator, device state, and any known limitations.

If a file is transformed, retain the original and record the transformation as a separate derived artifact.

## 3. Use an escalation ladder

Prefer the least invasive method that can answer the question:

1. Public documentation and manufacturer materials.
2. External inspection, labels, dimensions, and visible markings.
3. Host-side enumeration and ordinary application behavior.
4. Non-invasive electrical, optical, acoustic, or mechanical measurements.
5. Interface probing where safe and authorized.
6. Disassembly and component-level investigation.
7. Destructive extraction only when necessary, justified, and explicitly authorized.

Record why an escalation was necessary. A lack of equipment or an unresolved uncertainty is not a reason to invent a result.

## 4. Make negative findings precise

A statement such as "no interface exists" requires a defined test boundary. Prefer: "No USB descriptor was retrieved on host X using cable/interface Y under device states A and B on date Z." State what was not tested.

## 5. Reproducible work

Scripts should accept explicit inputs, emit stable outputs, report errors, and avoid silently altering source evidence. Record environment, dependencies, command line, configuration, and tool version.

## 6. Safety and authorization

Only investigate systems and data for which the investigator has authorization. Do not use this workspace to facilitate unauthorized access, credential theft, persistence, evasion, or harmful deployment. For batteries, mains-powered equipment, high-energy circuits, lasers, pressure systems, and hazardous materials, document relevant hazards and use qualified procedures and equipment.

## 7. Intellectual property and licensing

Track upstream origins and licenses. Keep attribution with copied or adapted code. Do not import large external corpora or proprietary firmware dumps without a lawful basis and clear provenance.

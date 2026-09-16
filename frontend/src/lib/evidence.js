// Ordering mirrors backend/pipeline/config.py IDENTIFIER_FIELDS weights —
// the strongest signal present on an edge is treated as its "type" for styling.
const FIELD_PRIORITY = ["DeviceInfo", "id_31", "P_emaildomain", "R_emaildomain", "addr1"];

export const EVIDENCE_TYPES = {
  DeviceInfo: { label: "Shared device", dash: "0", strokeWidth: 2 },
  id_31: { label: "Shared browser/OS", dash: "0", strokeWidth: 1.4 },
  P_emaildomain: { label: "Shared email domain", dash: "4 3", strokeWidth: 1.2 },
  R_emaildomain: { label: "Shared receiver email", dash: "4 3", strokeWidth: 1.2 },
  addr1: { label: "Shared address", dash: "1 3", strokeWidth: 1.2 },
};

export function primaryEvidenceField(evidence) {
  for (const field of FIELD_PRIORITY) {
    if (evidence[field] !== undefined) return field;
  }
  return Object.keys(evidence)[0];
}

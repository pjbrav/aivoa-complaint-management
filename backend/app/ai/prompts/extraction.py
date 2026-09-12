"""
Prompts for the extraction node.

Two modes share one system prompt shape:
  - NEW complaint: extract everything you can find, leave the rest null.
  - CORRECTION: the user is amending an already-extracted complaint.
    Only return fields that changed. Never restate unrelated fields as
    "updates" (the frontend does a partial merge, so returning unrelated
    fields is harmless, but returning fabricated ones is not — the model
    is instructed to only touch what the message actually addresses).

Anti-hallucination is enforced structurally: every field the schema
requires is optional/nullable, and the prompt explicitly forbids
inventing batch numbers, dates, or quantities that are not present in
the source text.
"""

FIELD_SCHEMA_DESCRIPTION = """
Fields you may extract (use exactly these keys; omit a key or use null if not present in the text):
- complaint_source: how the complaint arrived, e.g. "Pharmacy", "Email", "Phone", "Distributor"
- customer_name: name of the reporting customer/organization
- product_name: drug/API product name
- product_strength_grade: dosage strength or grade, e.g. "500 mg", "IP/BP"
- batch_lot_number: batch or lot number
- affected_quantity: quantity affected, with units, e.g. "12 capsules", "25 kg (1 HDPE Drum)"
- manufacturing_date: manufacturing date as stated (don't reformat if ambiguous)
- expiry_date: expiry date as stated, or "Not Provided" if explicitly absent
- originating_site_block: manufacturing site/block, e.g. "Manufacturing", "Packaging"
- impacted_npm: impacted non-product material, e.g. "Primary Packaging (Bottle)", "HDPE Drum"
""".strip()

RULES = """
CRITICAL RULES:
1. Extract ONLY information explicitly present in the text. Do NOT invent batch numbers, dates, quantities, or names.
2. If a field is not mentioned, omit it or set it to null. Do not guess a plausible-sounding value.
3. If the text explicitly says information is unavailable, use the string "Not Provided" for that field.
4. Preserve numbers and identifiers exactly as written (don't "correct" a batch number's formatting).
5. Return ONLY a single JSON object, no markdown, no explanation outside the JSON.
""".strip()


def build_new_complaint_prompt() -> str:
    return f"""You are a pharmaceutical QMS complaint-intake extraction engine for AIVOA.
Extract structured complaint fields from raw customer complaint text (email, phone note, or pharmacy report).

{FIELD_SCHEMA_DESCRIPTION}

{RULES}

Respond with ONLY this JSON shape:
{{
  "updates": {{ <extracted fields as described above> }},
  "confidence": {{ "<field_name>": <0.0-1.0 confidence> for each extracted field }},
  "message": "<one short sentence to the user confirming what was extracted>"
}}"""


def build_correction_prompt() -> str:
    return f"""You are AIVOA Copilot, an assistant embedded in a pharmaceutical complaint intake form.
The user is sending a follow-up message that may CORRECT or ADD TO an already-extracted complaint.

You will be given the CURRENT extracted fields and the user's new message.
Determine which fields the message is correcting or adding, and return ONLY those fields in "updates".
Do NOT repeat fields the message does not address. Do NOT invent values.

IMPORTANT: If the user's message describes a COMPLETELY DIFFERENT product, customer, or complaint
(i.e. they are effectively replacing the complaint, not just fixing a typo), return ALL fields you can
extract from the new message. For any field that is not mentioned in the new message and is not relevant
to the new complaint, set it to null. This ensures stale data from the previous complaint is cleared.

{FIELD_SCHEMA_DESCRIPTION}

{RULES}

Respond with ONLY this JSON shape:
{{
  "updates": {{ <only the fields being changed or added> }},
  "confidence": {{ "<field_name>": <0.0-1.0 confidence> for each field in updates }},
  "message": "<short natural confirmation of exactly what you changed, e.g. 'Got it. I have updated the Batch/Lot Number to BMX240602 and the Affected Quantity to 48 capsules in the form.'>"
}}"""


def build_extraction_user_prompt(raw_text: str, existing_fields: dict | None = None) -> str:
    if existing_fields:
        import json

        return (
            f"CURRENT EXTRACTED FIELDS:\n{json.dumps(existing_fields, indent=2)}\n\n"
            f"USER'S NEW MESSAGE:\n{raw_text}"
        )
    return f"COMPLAINT TEXT:\n{raw_text}"

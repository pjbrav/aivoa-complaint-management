/**
 * The structured complaint fields, mirroring backend `ComplaintFields`
 * (app/schemas/complaint.py). Keeping one canonical empty-field object
 * here means every place that needs a blank form (initial state, Reset
 * Form) uses the exact same key set as the API contract, so a typo in a
 * field name fails loudly instead of silently dropping data.
 *
 * @typedef {Object} ComplaintFields
 * @property {?string} complaint_source
 * @property {?string} customer_name
 * @property {?string} product_name
 * @property {?string} product_strength_grade
 * @property {?string} batch_lot_number
 * @property {?string} affected_quantity
 * @property {?string} manufacturing_date
 * @property {?string} expiry_date
 * @property {?string} originating_site_block
 * @property {?string} impacted_npm
 * @property {?string} complaint_category
 * @property {?string} complaint_description
 * @property {?string} severity
 * @property {?string} suggested_next_action
 * @property {?string} initial_risk_assessment
 * @property {?string} source_document
 */

export const EMPTY_COMPLAINT_FIELDS = {
  complaint_source: null,
  customer_name: null,
  product_name: null,
  product_strength_grade: null,
  batch_lot_number: null,
  affected_quantity: null,
  manufacturing_date: null,
  expiry_date: null,
  originating_site_block: null,
  impacted_npm: null,
  complaint_category: null,
  complaint_description: null,
  severity: null,
  suggested_next_action: null,
  initial_risk_assessment: null,
  source_document: null,
};

export const FIELD_LABELS = {
  complaint_source: "Complaint Source",
  customer_name: "Customer Name",
  product_name: "Product Name",
  product_strength_grade: "Product Strength / Grade",
  batch_lot_number: "Batch / Lot Number",
  affected_quantity: "Affected Quantity",
  manufacturing_date: "Manufacturing Date",
  expiry_date: "Expiry Date",
  originating_site_block: "Originating Site / Block",
  impacted_npm: "Impacted NPM",
  complaint_category: "Complaint Category",
  complaint_description: "Complaint Description",
};

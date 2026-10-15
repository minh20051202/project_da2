/-!
# Formalization example: clause 2, Article 14, 114/VBHN-VPQH

Scope: document conditions for input-VAT deduction for exported goods.

Source file:
  resources/references/01-vbhn-vpqh-114.pdf

This deliberately does not claim final legal eligibility. Article 14 also
contains substantive conditions in clause 1, exclusions in clause 3, and
delegates detailed rules to the Government in clause 4.

Demo scope excludes Government-defined exceptions to point b, special export
cases in point c, and export services. Evidence authenticity, applicability,
effective dates, and reasons for `notApplicable` require external review.
This file uses Lean 4 directly; it does not import the LegalLean library.
-/

namespace VAT.Article14Clause2

/-- Status assigned after a document has been parsed and reviewed. -/
inductive EvidenceStatus where
  | present
  | absent
  | unknown
  | notApplicable
  deriving DecidableEq, Repr

/-- Normalized evidence fields for one exported-goods transaction. -/
structure ExportGoodsEvidence where
  inputVatInvoiceOrTaxReceipt : EvidenceStatus
  nonCashPaymentForPurchase : EvidenceStatus
  foreignPartyContract : EvidenceStatus
  salesInvoice : EvidenceStatus
  nonCashPaymentForExport : EvidenceStatus
  customsDeclaration : EvidenceStatus
  packingList : EvidenceStatus
  billOfLading : EvidenceStatus
  insuranceCertificate : EvidenceStatus
  deriving Repr

def isPresent (status : EvidenceStatus) : Prop :=
  status = .present

/--
The source says an insurance document is required "if any". Therefore the
normalized field must be either present or explicitly marked not applicable.
`unknown` is not silently treated as `notApplicable`.
-/
def insuranceCondition (status : EvidenceStatus) : Prop :=
  status = .present ∨ status = .notApplicable

/--
Document-condition predicate derived from points a, b and c of clause 2,
Article 14, narrowed to exported goods.
-/
def SatisfiesDocumentConditions (e : ExportGoodsEvidence) : Prop :=
  isPresent e.inputVatInvoiceOrTaxReceipt ∧
  isPresent e.nonCashPaymentForPurchase ∧
  isPresent e.foreignPartyContract ∧
  isPresent e.salesInvoice ∧
  isPresent e.nonCashPaymentForExport ∧
  isPresent e.customsDeclaration ∧
  isPresent e.packingList ∧
  isPresent e.billOfLading ∧
  insuranceCondition e.insuranceCertificate

/-- A synthetic case in which every required document is present. -/
def completeCase : ExportGoodsEvidence where
  inputVatInvoiceOrTaxReceipt := .present
  nonCashPaymentForPurchase := .present
  foreignPartyContract := .present
  salesInvoice := .present
  nonCashPaymentForExport := .present
  customsDeclaration := .present
  packingList := .present
  billOfLading := .present
  insuranceCertificate := .notApplicable

theorem completeCase_is_verified :
    SatisfiesDocumentConditions completeCase := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    completeCase]

/-- A case where the customs declaration has not yet been established. -/
def customsDeclarationUnknown : ExportGoodsEvidence :=
  { completeCase with customsDeclaration := .unknown }

/--
This means "the document-condition check is not verified". It does not mean
that the real transaction has been proven legally ineligible.
-/
theorem unknown_customs_is_not_verified :
    ¬ SatisfiesDocumentConditions customsDeclarationUnknown := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    customsDeclarationUnknown, completeCase]

/-- A confirmed missing mandatory document in the normalized model. -/
def customsDeclarationAbsent : ExportGoodsEvidence :=
  { completeCase with customsDeclaration := .absent }

theorem absent_customs_is_not_verified :
    ¬ SatisfiesDocumentConditions customsDeclarationAbsent := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    customsDeclarationAbsent, completeCase]

/-- Unknown insurance is not silently treated as an exemption. -/
def insuranceUnknown : ExportGoodsEvidence :=
  { completeCase with insuranceCertificate := .unknown }

theorem unknown_insurance_is_not_verified :
    ¬ SatisfiesDocumentConditions insuranceUnknown := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    insuranceUnknown, completeCase]

/-- This demo has no exemption branch for a mandatory customs declaration. -/
def customsDeclarationNotApplicable : ExportGoodsEvidence :=
  { completeCase with customsDeclaration := .notApplicable }

theorem not_applicable_customs_is_not_verified :
    ¬ SatisfiesDocumentConditions customsDeclarationNotApplicable := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    customsDeclarationNotApplicable, completeCase]

/-- Exercise the present branch of the insurance condition as well. -/
def insurancePresent : ExportGoodsEvidence :=
  { completeCase with insuranceCertificate := .present }

theorem present_insurance_is_verified :
    SatisfiesDocumentConditions insurancePresent := by
  simp [SatisfiesDocumentConditions, isPresent, insuranceCondition,
    insurancePresent, completeCase]

end VAT.Article14Clause2

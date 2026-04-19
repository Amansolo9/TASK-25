import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

export function VerificationScreen({
  renderCards,
  verificationComment,
  setVerificationComment,
  verificationRequests,
  statusVariant,
  handleVerificationReview,
  submitVerificationRequest = (event) => event.preventDefault(),
  verificationRequestForm = { attestation: "", is_high_risk: false },
  setVerificationRequestForm = () => {},
  uploadVerificationDocument = (event) => event.preventDefault(),
  documentForm = { verification_id: "", document_type: "government_id", uploaded_file: null },
  setDocumentForm = () => {},
  openVerificationDocument = () => {},
  verificationOpenResult = "",
  operationsError = "",
  canReview = false,
}) {
  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Verification Request + Document Upload</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3" onSubmit={submitVerificationRequest}>
            <textarea
              className="min-h-20 w-full rounded-md border bg-background p-3 text-sm"
              value={verificationRequestForm.attestation}
              onChange={(event) =>
                setVerificationRequestForm((prev) => ({ ...prev, attestation: event.target.value }))
              }
              placeholder="Attestation statement"
              aria-label="Verification attestation"
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(verificationRequestForm.is_high_risk)}
                onChange={(event) =>
                  setVerificationRequestForm((prev) => ({ ...prev, is_high_risk: event.target.checked }))
                }
              />
              Mark as high-risk request (requires two approvals)
            </label>
            <Button>Submit Verification Request</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-2" onSubmit={uploadVerificationDocument}>
            <Input
              value={documentForm.verification_id}
              onChange={(event) =>
                setDocumentForm((prev) => ({ ...prev, verification_id: event.target.value }))
              }
              placeholder="Verification request id"
            />
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={documentForm.document_type}
              onChange={(event) =>
                setDocumentForm((prev) => ({ ...prev, document_type: event.target.value }))
              }
            >
              <option value="government_id">government_id</option>
              <option value="credential">credential</option>
              <option value="other">other</option>
            </select>
            <input
              className="md:col-span-2 text-sm"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              onChange={(event) =>
                setDocumentForm((prev) => ({ ...prev, uploaded_file: event.target.files?.[0] || null }))
              }
              aria-label="Verification document file"
            />
            <Button className="md:col-span-2">Upload Document</Button>
          </form>

          {verificationOpenResult && <p className="text-sm text-emerald-700">{verificationOpenResult}</p>}
          {operationsError && <p className="text-sm text-rose-700">{operationsError}</p>}
        </CardContent>
      </Card>

      {canReview && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Reviewer Console</CardTitle>
          </CardHeader>
          <CardContent>
            <textarea
              className="min-h-20 w-full rounded-md border bg-background p-3 text-sm"
              value={verificationComment}
              onChange={(event) => setVerificationComment(event.target.value)}
              placeholder="Optional comment for approve/reject review"
              aria-label="Verification review comments"
            />
          </CardContent>
        </Card>
      )}

      {renderCards(
        verificationRequests,
        (requestItem) => (
          <Card key={requestItem.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">Request #{requestItem.id}</CardTitle>
                <Badge variant={statusVariant(requestItem.status)}>{requestItem.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>User: {requestItem.username || "current user"}</p>
              <p>Risk: {requestItem.is_high_risk ? "high" : "standard"}</p>
              <p>Approvals: {requestItem.reviewer_approvals || 0} {requestItem.is_high_risk ? "(2 required)" : "(1 required)"}</p>
              <p>Attestation: {requestItem.attestation || "none"}</p>
              {!!requestItem.documents?.length && (
                <div className="rounded-md border p-2">
                  {requestItem.documents.map((doc) => (
                    <div key={doc.id} className="mb-2 flex items-center justify-between gap-2 text-xs">
                      <span>{doc.document_type} - {doc.file_name} ({doc.mime_type})</span>
                      <Button size="sm" variant="ghost" onClick={() => openVerificationDocument(doc.id)}>Open</Button>
                    </div>
                  ))}
                </div>
              )}
              {canReview && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => handleVerificationReview(requestItem.id, true)}>
                    Approve
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => handleVerificationReview(requestItem.id, false)}>
                    Reject
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ),
        "No verification requests available."
      )}
    </>
  );
}

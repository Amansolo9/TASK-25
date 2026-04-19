import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

export function JobsScreen({
  renderCards,
  jobForm,
  setJobForm,
  handleCreateJob,
  jobs,
  handleRetryJob,
  setSelectedJobId,
  selectedJobId,
  rowErrors,
  handleResolveRowError,
  dedupeForm,
  setDedupeForm,
  handleDedupeCheck,
  dedupeResult,
  statusVariant,
}) {
  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Create Job</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={handleCreateJob}>
            <Input value={jobForm.job_type} onChange={(event) => setJobForm((prev) => ({ ...prev, job_type: event.target.value }))} aria-label="Job type" />
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={jobForm.trigger_type} onChange={(event) => setJobForm((prev) => ({ ...prev, trigger_type: event.target.value }))} aria-label="Job trigger type">
              <option value="manual">manual</option>
              <option value="scheduled">scheduled</option>
            </select>
            <Input value={jobForm.source_path} onChange={(event) => setJobForm((prev) => ({ ...prev, source_path: event.target.value }))} aria-label="Source path" placeholder="/dropzone/file.csv" />
            <Input value={jobForm.dedupe_key} onChange={(event) => setJobForm((prev) => ({ ...prev, dedupe_key: event.target.value }))} aria-label="Dedupe key" placeholder="manifest-2026-03-28" />
            <Input type="number" min={1} max={10} value={jobForm.priority} onChange={(event) => setJobForm((prev) => ({ ...prev, priority: Number(event.target.value) || 5 }))} aria-label="Job priority" />
            <Button>Create Job</Button>
          </form>
        </CardContent>
      </Card>

      {renderCards(
        jobs,
        (job) => (
          <Card key={job.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">{job.job_type}</CardTitle>
                <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>{job.source_path || "No source path"}</p>
              <p>Priority {job.priority} | Attempts {job.attempt_count}/{job.max_attempts}</p>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => handleRetryJob(job.id)}>Retry</Button>
                <Button size="sm" variant="ghost" onClick={() => setSelectedJobId(String(job.id))}>Row errors</Button>
              </div>
            </CardContent>
          </Card>
        ),
        "No jobs currently queued."
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Ingestion Row Errors</CardTitle>
          <CardDescription>Selected job: {selectedJobId || "None"}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {rowErrors.length === 0 && <p className="text-sm text-muted-foreground">No row errors for this job.</p>}
          {rowErrors.map((item) => (
            <div key={item.id} className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{item.source_file} row {item.row_number}</p>
                <Badge variant={item.resolved ? "success" : "warning"}>{item.resolved ? "resolved" : "pending"}</Badge>
              </div>
              <p className="mt-1 text-muted-foreground">{item.error_message}</p>
              {!item.resolved && (
                <Button size="sm" variant="secondary" className="mt-2" onClick={() => handleResolveRowError(item.id)}>
                  Resolve
                </Button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Attachment Dedupe Check</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={handleDedupeCheck}>
            <Input value={dedupeForm.source_signature} onChange={(event) => setDedupeForm((prev) => ({ ...prev, source_signature: event.target.value }))} placeholder="manifest.csv:sheet1" aria-label="Source signature" />
            <Input value={dedupeForm.content_hash} onChange={(event) => setDedupeForm((prev) => ({ ...prev, content_hash: event.target.value }))} placeholder="sha256 hash" aria-label="Attachment content hash" />
            <Input value={dedupeForm.first_seen_job} onChange={(event) => setDedupeForm((prev) => ({ ...prev, first_seen_job: event.target.value }))} placeholder="Optional job id" aria-label="First seen job id" />
            <Button>Check Duplicate</Button>
          </form>
          {dedupeResult && (
            <p className="mt-3 text-sm text-muted-foreground">
              Duplicate: {dedupeResult.duplicate ? "Yes" : "No"} | Fingerprint #{dedupeResult.fingerprint?.id}
            </p>
          )}
        </CardContent>
      </Card>
    </>
  );
}

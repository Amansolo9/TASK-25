import { useCallback, useEffect, useState } from "react";

const initialJobForm = {
  job_type: "ingest.manifest",
  trigger_type: "manual",
  source_path: "",
  dedupe_key: "",
  priority: 5,
};

const initialDedupeForm = {
  source_signature: "",
  content_hash: "",
  first_seen_job: "",
};

export function useJobsController({ api, setStatus }) {
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [rowErrors, setRowErrors] = useState([]);
  const [jobForm, setJobForm] = useState(initialJobForm);
  const [dedupeForm, setDedupeForm] = useState(initialDedupeForm);
  const [dedupeResult, setDedupeResult] = useState(null);

  const loadRowErrors = useCallback(
    async (jobId) => {
      if (!jobId) {
        setRowErrors([]);
        return;
      }
      try {
        const data = await api(`/api/jobs/${jobId}/row-errors/`);
        setRowErrors(data || []);
      } catch {
        setRowErrors([]);
      }
    },
    [api]
  );

  const loadJobs = useCallback(async () => {
    try {
      const data = await api("/api/jobs/");
      setJobs(data || []);
      if (!selectedJobId && data?.length) {
        setSelectedJobId(String(data[0].id));
      }
    } catch {
      setJobs([]);
    }
  }, [api, selectedJobId]);

  useEffect(() => {
    loadRowErrors(selectedJobId);
  }, [selectedJobId, loadRowErrors]);

  const handleCreateJob = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/jobs/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...jobForm, priority: Number(jobForm.priority) }),
          },
          true
        );
        await loadJobs();
        setStatus({ loading: false, message: "Job created", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, jobForm, loadJobs, setStatus]
  );

  const handleRetryJob = useCallback(
    async (jobId) => {
      try {
        await api(`/api/jobs/${jobId}/retry/`, { method: "POST" }, true);
        await loadJobs();
        setStatus({ loading: false, message: "Job re-queued", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadJobs, setStatus]
  );

  const handleResolveRowError = useCallback(
    async (errorId) => {
      try {
        await api(
          `/api/jobs/row-errors/${errorId}/resolve/`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resolution_note: "Resolved from dashboard" }),
          },
          true
        );
        await loadRowErrors(selectedJobId);
        setStatus({ loading: false, message: "Row error resolved", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadRowErrors, selectedJobId, setStatus]
  );

  const handleDedupeCheck = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        const payload = {
          source_signature: dedupeForm.source_signature,
          content_hash: dedupeForm.content_hash,
        };
        if (dedupeForm.first_seen_job) {
          payload.first_seen_job = Number(dedupeForm.first_seen_job);
        }
        const data = await api(
          "/api/jobs/attachments/dedupe-check/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          },
          true
        );
        setDedupeResult(data);
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, dedupeForm.content_hash, dedupeForm.first_seen_job, dedupeForm.source_signature, setStatus]
  );

  const resetJobs = useCallback(() => {
    setJobs([]);
    setSelectedJobId("");
    setRowErrors([]);
    setJobForm(initialJobForm);
    setDedupeForm(initialDedupeForm);
    setDedupeResult(null);
  }, []);

  return {
    jobs,
    selectedJobId,
    setSelectedJobId,
    rowErrors,
    jobForm,
    setJobForm,
    dedupeForm,
    setDedupeForm,
    dedupeResult,
    loadJobs,
    handleCreateJob,
    handleRetryJob,
    handleResolveRowError,
    handleDedupeCheck,
    resetJobs,
  };
}

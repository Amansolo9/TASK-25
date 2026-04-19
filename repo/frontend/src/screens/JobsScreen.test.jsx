import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JobsScreen } from "./JobsScreen";

describe("JobsScreen", () => {
  it("invokes retry callback for a listed job", async () => {
    const handleRetryJob = vi.fn();

    render(
      <JobsScreen
        renderCards={(_items, renderer) => <div>{renderer({ id: 1, job_type: "ingest", source_path: "a.csv", status: "pending", priority: 5, attempt_count: 0, max_attempts: 3 })}</div>}
        jobForm={{ job_type: "ingest", trigger_type: "manual", source_path: "", dedupe_key: "", priority: 5 }}
        setJobForm={vi.fn()}
        handleCreateJob={vi.fn((e) => e.preventDefault())}
        jobs={[{ id: 1, job_type: "ingest", source_path: "a.csv", status: "pending", priority: 5, attempt_count: 0, max_attempts: 3 }]}
        handleRetryJob={handleRetryJob}
        setSelectedJobId={vi.fn()}
        selectedJobId="1"
        rowErrors={[]}
        handleResolveRowError={vi.fn()}
        dedupeForm={{ source_signature: "", content_hash: "", first_seen_job: "" }}
        setDedupeForm={vi.fn()}
        handleDedupeCheck={vi.fn((e) => e.preventDefault())}
        dedupeResult={null}
        statusVariant={() => "default"}
      />
    );

    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    expect(handleRetryJob).toHaveBeenCalledWith(1);
  });
});

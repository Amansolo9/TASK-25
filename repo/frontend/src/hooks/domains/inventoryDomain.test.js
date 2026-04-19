import { describe, expect, it } from "vitest";

import { computeInventoryMetrics } from "./inventoryDomain";

describe("inventoryDomain", () => {
  it("computes aggregate dashboard metrics", () => {
    const result = computeInventoryMetrics({
      plans: [{ id: 1 }],
      tasks: [{ status: "completed" }, { status: "review" }],
      lines: [
        { requires_review: true, closed: false, variance_type: "missing" },
        { requires_review: true, closed: true, variance_type: "extra" },
        { requires_review: false, closed: true, variance_type: "data_mismatch" },
      ],
    });

    expect(result.totals.plans).toBe(1);
    expect(result.totals.completedTasks).toBe(1);
    expect(result.totals.reviewRequiredLines).toBe(2);
    expect(result.varianceCounts.data_mismatch).toBe(1);
  });
});

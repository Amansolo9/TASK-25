import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InventoryScreen } from "./InventoryScreen";

describe("InventoryScreen", () => {
  it("renders progress metrics and variance hotspots", () => {
    render(
      <InventoryScreen
        renderCards={(items, renderer) => <div>{items.map((item) => renderer(item))}</div>}
        plans={[{ id: 1, title: "Plan A", region: "North", asset_type: "Medical", mode: "full", status: "open" }]}
        tasks={[
          { id: 1, status: "completed" },
          { id: 2, status: "review" },
        ]}
        lines={[
          { id: 1, requires_review: true, closed: false, variance_type: "missing" },
          { id: 2, requires_review: true, closed: true, variance_type: "extra" },
          { id: 3, requires_review: false, closed: true, variance_type: "data_mismatch" },
        ]}
        statusVariant={() => "default"}
      />
    );

    expect(screen.getByText("Plans")).toBeInTheDocument();
    expect(screen.getByText("1/2 complete")).toBeInTheDocument();
    expect(screen.getByText("Review required")).toBeInTheDocument();
    expect(screen.getByText(/Missing: 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Extra: 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Data mismatch: 1/i)).toBeInTheDocument();
  });
});

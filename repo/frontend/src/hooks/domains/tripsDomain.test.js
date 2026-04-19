import { describe, expect, it } from "vitest";

import { bookingActionEndpoints } from "./tripsDomain";

describe("tripsDomain", () => {
  it("builds booking endpoint map", () => {
    const endpoints = bookingActionEndpoints(44);
    expect(endpoints.acknowledge).toBe("/api/trips/bookings/44/ack/");
    expect(endpoints.timeline).toBe("/api/trips/bookings/44/timeline/");
  });
});

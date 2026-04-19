import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import * as accessDomain from "./hooks/domains/accessDomain";

function jsonResponse(payload, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );
}

function mockApi(options = {}) {
  const {
    failLogin = false,
    failDedupe = false,
    roles,
    reackRequired = false,
    requireCaptcha = false,
    lockout = false,
  } = options;
  let loginAttempts = 0;
  const state = {
    booking: {
      id: 301,
      trip: 11,
      status: "confirmed",
      reack_required: reackRequired,
      acknowledged_version: 1,
    },
    rowErrors: [
      {
        id: 701,
        source_file: "manifest.csv",
        row_number: 14,
        error_message: "Missing rider id",
        resolved: false,
      },
    ],
    verificationRequests: [
      {
        id: 601,
        username: "senior1",
        is_high_risk: true,
        status: "pending",
        reviewer_approvals: 1,
      },
    ],
    favorites: [],
    comparisons: [],
    alerts: [],
    zones: [],
    locations: [],
    partners: [],
    preference: {
      locale: "en",
      timezone: "UTC",
      large_text_mode: false,
      high_contrast_mode: false,
      updated_at: "2026-03-28T12:00:00Z",
    },
    travelerProfiles: [],
    exportRequests: [],
  };

  const fetchMock = vi.fn(async (input, init = {}) => {
    const url = String(input);
    const method = (init.method || "GET").toUpperCase();

    if (url.endsWith("/api/health/")) return jsonResponse({ ok: true });
    if (url.endsWith("/api/auth/csrf/")) return jsonResponse({ csrfToken: "csrf-token" });
    if (url.endsWith("/api/auth/register/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      if (!payload.password || payload.password.length < 12) {
        return jsonResponse({ detail: "This password is too short." }, 400);
      }
      return jsonResponse({ id: 77, username: payload.username }, 201);
    }
    if (url.endsWith("/api/auth/change-password/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      if (!payload.current_password) return jsonResponse({ detail: "Invalid current password." }, 400);
      if (String(payload.new_password || "").includes("old")) {
        return jsonResponse({ detail: "Password was used recently. Choose a different password." }, 400);
      }
      return jsonResponse({ detail: "Password updated." });
    }
    if (url.endsWith("/api/auth/captcha/challenge/") && method === "POST") {
      return jsonResponse({ challenge_id: "challenge-1", prompt: "Type 3 + 4", expires_at: "2026-03-28T13:00:00Z" });
    }
    if (url.endsWith("/api/auth/login/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      loginAttempts += 1;
      if (lockout) {
        return jsonResponse({ detail: "Account is locked.", locked_until: "2026-03-29T00:00:00Z" }, 423);
      }
      if (requireCaptcha && loginAttempts === 1) {
        return jsonResponse({ detail: "CAPTCHA required or invalid.", requires_captcha: true }, 400);
      }
      if (requireCaptcha && !payload.captcha_response) {
        return jsonResponse({ detail: "CAPTCHA required or invalid.", requires_captcha: true }, 400);
      }
      if (failLogin) return jsonResponse({ detail: "Invalid credentials" }, 400);
      return jsonResponse({ id: 1, username: "orgadmin", real_name: "Org Admin" });
    }
    if (url.endsWith("/api/access/me/roles/")) {
      return jsonResponse(roles || [{ code: "org_admin", name: "Organization Admin" }]);
    }
    if (url.endsWith("/api/trips/")) {
      return jsonResponse([
        {
          id: 11,
          title: "Clinic Route",
          origin: "North Center",
          destination: "Clinic",
          status: "draft",
          current_version: 1,
          capacity_limit: 3,
        },
      ]);
    }
    if (url.includes("/api/trips/11/bookings/")) {
      return jsonResponse([state.booking]);
    }
    if (url.endsWith("/api/trips/bookings/mine/")) {
      return jsonResponse([state.booking]);
    }
    if (url.endsWith("/api/trips/bookings/301/ack/") && method === "POST") {
      state.booking = { ...state.booking, reack_required: false, acknowledged_version: 2 };
      return jsonResponse(state.booking);
    }
    if (url.endsWith("/api/trips/bookings/301/cancel/") && method === "POST") {
      if (state.booking.reack_required) {
        return jsonResponse({ detail: "Trip update acknowledgment is required before this action." }, 409);
      }
      state.booking = { ...state.booking, status: "cancelled" };
      return jsonResponse(state.booking);
    }
    if (url.endsWith("/api/warehouses/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.warehouses?.length ? state.warehouses.length + 1 : 1, ...payload };
      state.warehouses = [next, ...(state.warehouses || [])];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/warehouses/")) return jsonResponse(state.warehouses || []);
    if (url.endsWith("/api/warehouses/zones/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.zones.length + 1, ...payload };
      state.zones = [next, ...state.zones];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/warehouses/zones/")) return jsonResponse(state.zones);
    if (url.endsWith("/api/warehouses/locations/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.locations.length + 1, ...payload };
      state.locations = [next, ...state.locations];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/warehouses/locations/")) return jsonResponse(state.locations);
    if (url.endsWith("/api/warehouses/partners/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const hasOverlap = state.partners.some(
        (item) =>
          item.external_code === payload.external_code &&
          item.partner_type === payload.partner_type &&
          item.effective_start <= (payload.effective_end || "9999-12-31") &&
          payload.effective_start <= (item.effective_end || "9999-12-31")
      );
      if (hasOverlap) return jsonResponse({ detail: "Overlapping effective date ranges are not allowed" }, 400);
      const next = { id: state.partners.length + 1, ...payload };
      state.partners = [next, ...state.partners];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/warehouses/partners/")) return jsonResponse(state.partners);
    if (url.endsWith("/api/inventory/plans/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.plans?.length ? state.plans.length + 1 : 1, status: "draft", ...payload };
      state.plans = [next, ...(state.plans || [])];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/inventory/plans/")) return jsonResponse(state.plans || []);
    if (url.endsWith("/api/inventory/tasks/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: (state.inventoryTasks || []).length + 1, ...payload };
      state.inventoryTasks = [next, ...(state.inventoryTasks || [])];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/inventory/tasks/")) return jsonResponse(state.inventoryTasks || []);
    if (url.endsWith("/api/inventory/lines/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = {
        id: (state.inventoryLines || []).length + 1,
        variance_type: Number(payload.physical_quantity) < Number(payload.book_quantity) ? "missing" : "extra",
        requires_review: true,
        closed: false,
        ...payload,
      };
      state.inventoryLines = [next, ...(state.inventoryLines || [])];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/inventory/lines/")) return jsonResponse(state.inventoryLines || []);
    if (url.includes("/api/inventory/lines/") && url.includes("/corrective-action/")) return jsonResponse({ id: 1 }, 201);
    if (url.includes("/api/inventory/lines/") && url.includes("/approve-action/")) return jsonResponse({ id: 1, accountability_acknowledged: true });
    if (url.includes("/api/inventory/lines/") && url.includes("/acknowledge-action/")) return jsonResponse({ id: 1, accountability_acknowledged: true });
    if (url.includes("/api/inventory/lines/") && url.includes("/close/")) {
      return jsonResponse({ detail: "Variance closed", closure_id: 1001 });
    }
    if (url.endsWith("/api/jobs/")) {
      if (method === "POST") {
        return jsonResponse({ id: 88, job_type: "ingest.manifest", status: "pending" }, 201);
      }
      return jsonResponse([
        {
          id: 88,
          job_type: "ingest.manifest",
          source_path: "/dropzone/manifest.csv",
          status: "pending",
          priority: 5,
          attempt_count: 0,
          max_attempts: 4,
        },
      ]);
    }
    if (url.includes("/api/jobs/88/row-errors/")) return jsonResponse(state.rowErrors);
    if (url.includes("/api/jobs/row-errors/701/resolve/") && method === "POST") {
      state.rowErrors = state.rowErrors.map((item) => (item.id === 701 ? { ...item, resolved: true } : item));
      return jsonResponse(state.rowErrors.find((item) => item.id === 701));
    }
    if (url.endsWith("/api/jobs/attachments/dedupe-check/") && method === "POST") {
      if (failDedupe) return jsonResponse({ detail: "Checksum mismatch" }, 400);
      return jsonResponse({ duplicate: true, fingerprint: { id: 9001 } });
    }
    if (url.endsWith("/api/auth/favorites/") && method === "GET") return jsonResponse(state.favorites);
    if (url.endsWith("/api/auth/favorites/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.favorites.length + 1, ...payload };
      state.favorites = [next, ...state.favorites];
      return jsonResponse(next, 201);
    }
    if (url.includes("/api/auth/favorites/") && method === "DELETE") {
      const id = Number(url.split("/api/auth/favorites/")[1].replace("/", ""));
      state.favorites = state.favorites.filter((item) => item.id !== id);
      return jsonResponse(null, 204);
    }
    if (url.endsWith("/api/auth/comparisons/") && method === "GET") return jsonResponse(state.comparisons);
    if (url.endsWith("/api/auth/comparisons/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.comparisons.length + 1, ...payload };
      state.comparisons = [next, ...state.comparisons];
      return jsonResponse(next, 201);
    }
    if (url.includes("/api/auth/comparisons/") && method === "DELETE") {
      const id = Number(url.split("/api/auth/comparisons/")[1].replace("/", ""));
      state.comparisons = state.comparisons.filter((item) => item.id !== id);
      return jsonResponse(null, 204);
    }
    if (url.endsWith("/api/auth/alerts/") && method === "GET") return jsonResponse(state.alerts);
    if (url.endsWith("/api/auth/alerts/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = { id: state.alerts.length + 1, acknowledged: false, ...payload };
      state.alerts = [next, ...state.alerts];
      return jsonResponse(next, 201);
    }
    if (url.includes("/api/auth/alerts/") && url.includes("/acknowledge/") && method === "POST") {
      const id = Number(url.split("/api/auth/alerts/")[1].split("/")[0]);
      state.alerts = state.alerts.map((item) => (item.id === id ? { ...item, acknowledged: true } : item));
      return jsonResponse(state.alerts.find((item) => item.id === id));
    }
    if (url.endsWith("/api/auth/preferences/") && method === "GET") return jsonResponse(state.preference);
    if (url.endsWith("/api/auth/preferences/") && method === "PUT") {
      const payload = JSON.parse(init.body || "{}");
      state.preference = { ...state.preference, ...payload, updated_at: "2026-03-28T13:00:00Z" };
      return jsonResponse(state.preference);
    }
    if (url.endsWith("/api/auth/traveler-profiles/") && method === "GET") return jsonResponse(state.travelerProfiles);
    if (url.endsWith("/api/auth/traveler-profiles/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = {
        id: state.travelerProfiles.length + 1,
        display_name: payload.display_name,
        masked_identifier: "*******6789",
        masked_government_id: "*******4321",
        masked_credential_number: "*******9988",
      };
      state.travelerProfiles = [next, ...state.travelerProfiles];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/security/unmask-sessions/") && method === "POST") return jsonResponse({ id: 1 }, 201);
    if (url.includes("/api/security/traveler-profiles/") && url.includes("/reveal/")) {
      if (url.includes("government-id")) return jsonResponse({ government_id: "GOV-12344321" });
      if (url.includes("credential-number")) return jsonResponse({ credential_number: "CRED-00009988" });
      return jsonResponse({ identifier: "TRAVELER-56786789" });
    }
    if (url.endsWith("/api/auth/exports/") && method === "GET") return jsonResponse(state.exportRequests);
    if (url.endsWith("/api/auth/exports/request/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      if (payload.include_unmasked && !roles?.some((role) => ["org_admin", "platform_admin"].includes(role.code))) {
        return jsonResponse({ detail: "Missing permission: sensitive.unmask for unmasked export." }, 403);
      }
      const next = { id: state.exportRequests.length + 1, status: "pending", file_path: "", ...payload };
      state.exportRequests = [next, ...state.exportRequests];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/auth/deletion-request/") && method === "POST") {
      return jsonResponse({ id: 1, status: "pending" }, 201);
    }

    if (url.endsWith("/api/auth/verification-requests/") && method === "POST") {
      const payload = JSON.parse(init.body || "{}");
      const next = {
        id: state.verificationRequests.length + 1,
        status: "pending",
        username: "senior1",
        reviewer_approvals: 0,
        documents: [],
        ...payload,
      };
      state.verificationRequests = [next, ...state.verificationRequests];
      return jsonResponse(next, 201);
    }
    if (url.endsWith("/api/auth/verification-requests/")) return jsonResponse(state.verificationRequests);
    if (url.includes("/documents/upload/") && method === "POST") {
      return jsonResponse({ detail: "uploaded" }, 201);
    }
    if (url.includes("/api/auth/verification-documents/") && url.endsWith("/open/")) {
      return jsonResponse({ detail: "opened" });
    }
    if (url.endsWith("/api/auth/verification-requests/601/review/") && method === "POST") {
      state.verificationRequests = state.verificationRequests.map((item) =>
        item.id === 601 ? { ...item, status: "approved", reviewer_approvals: 2 } : item
      );
      return jsonResponse({ id: 10, verification_request: 601, approved: true }, 201);
    }
    if (url.endsWith("/api/monitoring/alerts/")) return jsonResponse(state.alerts);
    if (url.endsWith("/api/trips/bookings/301/timeline/")) {
      return jsonResponse([
        {
          id: 1,
          from_status: "new",
          to_status: "confirmed",
          reason: "Booking created",
        },
      ]);
    }
    if (url.includes("/fare-estimate/")) return jsonResponse({ total_cents: 4461 });

    return jsonResponse({ detail: `Unhandled ${method} ${url}` }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("App integration", () => {
  beforeEach(() => {
    mockApi();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("logs in and renders trip workflows", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await screen.findAllByText("Operator Context");
    expect(screen.getAllByText("Clinic Route").length).toBeGreaterThan(0);
    expect(screen.getByText("Fare Estimator")).toBeInTheDocument();
    expect(screen.getByText("Booking Actions")).toBeInTheDocument();
  });

  it("runs attachment dedupe check from jobs screen", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Jobs/i }));
    await screen.findByText("Attachment Dedupe Check");

    const signature = screen.getByRole("textbox", { name: "Source signature" });
    const hash = screen.getByRole("textbox", { name: "Attachment content hash" });
    await userEvent.type(signature, "manifest.csv:sheet1");
    await userEvent.type(hash, "abc123");
    await userEvent.click(screen.getByRole("button", { name: "Check Duplicate" }));

    await waitFor(() => {
      expect(screen.getByText(/Duplicate: Yes/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Fingerprint #9001/i)).toBeInTheDocument();
  });

  it("resolves an ingestion row error from jobs screen", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Jobs/i }));
    await screen.findByText("Ingestion Row Errors");
    expect(screen.getByText(/Missing rider id/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Resolve" }));
    await waitFor(() => {
      expect(screen.getByText("resolved")).toBeInTheDocument();
    });
  });

  it("renders booking timeline events", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: "Timeline" }));
    await waitFor(() => {
      expect(screen.getByText("Latest Timeline")).toBeInTheDocument();
    });
    expect(screen.getByText(/new -> confirmed/i)).toBeInTheDocument();
  });

  it("submits verification approval review", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Verification/i }));
    await screen.findByText("Reviewer Console");
    await userEvent.type(screen.getByRole("textbox", { name: "Verification review comments" }), "All checks pass");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(screen.getByText("Verification review submitted")).toBeInTheDocument();
    });
    expect(screen.getByText(/Approvals: 2/i)).toBeInTheDocument();
  });

  it("shows login error message on auth failure", async () => {
    vi.unstubAllGlobals();
    mockApi({ failLogin: true });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("shows error state when dedupe check fails", async () => {
    vi.unstubAllGlobals();
    mockApi({ failDedupe: true });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Jobs/i }));
    await screen.findByText("Attachment Dedupe Check");

    await userEvent.type(screen.getByRole("textbox", { name: "Source signature" }), "manifest.csv:sheet1");
    await userEvent.type(screen.getByRole("textbox", { name: "Attachment content hash" }), "bad-hash");
    await userEvent.click(screen.getByRole("button", { name: "Check Duplicate" }));

    await waitFor(() => {
      expect(screen.getAllByText("Checksum mismatch").length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("button", { name: "Retry load" })).toBeInTheDocument();
  });

  it("runs profile favorites and reminders workflows", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "senior", name: "Senior" }] });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Profile/i }));
    await screen.findByText("Favorites");

    const referenceInputs = screen.getAllByPlaceholderText("reference id");
    await userEvent.type(referenceInputs[0], "trip-123");
    await userEvent.click(screen.getByRole("button", { name: "Add Favorite" }));
    await waitFor(() => {
      expect(screen.getByText(/trip: trip-123/i)).toBeInTheDocument();
    });

    await userEvent.type(screen.getByPlaceholderText("Reminder title"), "Medication Card");
    await userEvent.type(screen.getByPlaceholderText("Reminder details"), "Bring card to clinic");
    await userEvent.click(screen.getByRole("button", { name: "Create Reminder" }));
    await waitFor(() => {
      expect(screen.getByText(/Medication Card/i)).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => {
      expect(screen.getByText("Acknowledged")).toBeInTheDocument();
    });
  });

  it("enforces re-ack flow before cancellation", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "senior", name: "Senior" }], reackRequired: true });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    expect(cancelButton).toBeDisabled();
    expect(screen.getByText(/New version available/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Acknowledge Update" }));
    await waitFor(() => {
      expect(screen.getByText(/Re-ack required: no/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Cancel" })).not.toBeDisabled();
  });

  it("runs profile privacy and export workflows", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "org_admin", name: "Organization Admin" }] });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Profile/i }));
    await screen.findByText("Preferences");

    await userEvent.clear(screen.getByPlaceholderText("Locale"));
    await userEvent.type(screen.getByPlaceholderText("Locale"), "en-US");
    await userEvent.click(screen.getByRole("button", { name: "Save Preferences" }));

    await userEvent.type(screen.getByPlaceholderText("Display name"), "Parent Profile");
    await userEvent.type(screen.getByPlaceholderText("Traveler identifier"), "TRAVELER-56786789");
    await userEvent.type(screen.getByPlaceholderText("Government ID"), "GOV-12344321");
    await userEvent.type(screen.getByPlaceholderText("Credential number"), "CRED-00009988");
    await userEvent.click(screen.getByRole("button", { name: "Save Traveler Profile" }));
    await waitFor(() => {
      expect(screen.getByText("Parent Profile")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Reveal Government ID" }));
    await userEvent.type(screen.getByPlaceholderText("Reason for revealing this field"), "identity check");
    await userEvent.click(screen.getByRole("button", { name: "Confirm Reveal" }));
    await waitFor(() => {
      expect(screen.getByText(/GOV-12344321/i)).toBeInTheDocument();
    });

    await userEvent.click(screen.getByLabelText("Include unmasked data"));
    await userEvent.type(screen.getByPlaceholderText("Justification for unmasked export"), "Audit handoff");
    await userEvent.click(screen.getByRole("button", { name: "Request Export" }));
    await waitFor(() => {
      expect(screen.getByText(/Mode: unmasked/i)).toBeInTheDocument();
    });

    await userEvent.type(screen.getByPlaceholderText("Acknowledge retention notice"), "I understand retention windows");
    await userEvent.click(screen.getByLabelText("I acknowledge retention and legal hold notices."));
    await userEvent.click(screen.getByRole("button", { name: "Request Account Deletion" }));
    await waitFor(() => {
      expect(screen.getByText("Account deletion requested")).toBeInTheDocument();
    });
  });

  it("supports registration and captcha login challenge UX", async () => {
    vi.unstubAllGlobals();
    mockApi({ requireCaptcha: true });

    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    await userEvent.type(screen.getByLabelText("Organization code"), "HARBOR_TEST");
    await userEvent.type(screen.getByLabelText("Real name"), "Test User");
    await userEvent.type(screen.getByLabelText("Registration username"), "new-user");
    await userEvent.type(screen.getByLabelText("Registration password"), "StrongPassword123");
    await userEvent.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByText(/Registration complete/i)).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText("Username"), "new-user");
    await userEvent.type(screen.getByLabelText("Password"), "StrongPassword123");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() => {
      expect(screen.getByText(/CAPTCHA challenge/i)).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText("CAPTCHA answer"), "7");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");
  });

  it("shows lockout message when account is locked", async () => {
    vi.unstubAllGlobals();
    mockApi({ lockout: true });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() => {
      expect(screen.getByText(/Account locked until/i)).toBeInTheDocument();
    });
  });

  it("runs verification upload and document open workflows", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "org_admin", name: "Organization Admin" }] });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");
    await userEvent.click(screen.getByRole("button", { name: /Verification/i }));

    await userEvent.type(screen.getByLabelText("Verification attestation"), "I attest this identity is accurate.");
    await userEvent.click(screen.getByRole("button", { name: "Submit Verification Request" }));
    await waitFor(() => {
      expect(screen.getByText("Verification request submitted")).toBeInTheDocument();
    });

    const file = new File(["doc"], "id-proof.pdf", { type: "application/pdf" });
    await userEvent.type(screen.getByPlaceholderText("Verification request id"), "601");
    await userEvent.upload(screen.getByLabelText("Verification document file"), file);
    await userEvent.click(screen.getByRole("button", { name: "Upload Document" }));
    await waitFor(() => {
      expect(screen.getByText("Verification document uploaded")).toBeInTheDocument();
    });
  });

  it("runs warehouse and inventory execution workflows", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "org_admin", name: "Organization Admin" }] });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Warehouse/i }));
    await userEvent.type(screen.getByPlaceholderText("Warehouse name"), "Main DC");
    await userEvent.type(screen.getByPlaceholderText("Region"), "North");
    await userEvent.click(screen.getByRole("button", { name: "Add Warehouse" }));
    await waitFor(() => {
      expect(screen.getAllByText("Main DC").length).toBeGreaterThan(0);
    });

    await userEvent.click(screen.getByRole("button", { name: /Inventory/i }));
    await userEvent.type(screen.getByPlaceholderText("Plan title"), "Cycle Plan");
    await userEvent.type(screen.getByPlaceholderText("Asset type"), "Medical");
    await userEvent.click(screen.getByRole("button", { name: "Create Plan" }));
    await waitFor(() => {
      expect(screen.getAllByText(/Cycle Plan/i).length).toBeGreaterThan(0);
    });
  });

  it("enforces role matrix UI visibility", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "family_member", name: "Family Member" }] });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    expect(screen.queryByRole("button", { name: /Warehouse/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Inventory/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trips/i })).toBeInTheDocument();
  });

  it("blocks jobs UI when active screen is forced without access", async () => {
    vi.unstubAllGlobals();
    mockApi({ roles: [{ code: "org_admin", name: "Organization Admin" }] });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await screen.findAllByText("Operator Context");

    await userEvent.click(screen.getByRole("button", { name: /Jobs/i }));
    await screen.findByText("Attachment Dedupe Check");

    const originalCanAccess = accessDomain.canAccessScreen;
    const accessSpy = vi.spyOn(accessDomain, "canAccessScreen").mockImplementation((capabilities, screenName) => {
      if (screenName === "Jobs") return false;
      return originalCanAccess(capabilities, screenName);
    });

    await userEvent.click(screen.getByRole("button", { name: /Refresh/i }));

    await waitFor(() => {
      expect(screen.getByText(/Not authorized for this module/i)).toBeInTheDocument();
    });
    expect(screen.queryByText("Attachment Dedupe Check")).not.toBeInTheDocument();

    accessSpy.mockRestore();
  });
});

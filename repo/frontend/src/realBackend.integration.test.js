// @vitest-environment node
/**
 * Real-network integration tests: every request in this file goes through the
 * live Caddy proxy to the live Django backend running in the Docker network.
 * No fetch mocks, no `vi.stubGlobal`, no canned responses.
 *
 * Running surface:
 *   - inside the `frontend` container, proxy is reachable at https://proxy:8443
 *   - self-signed cert → we attach an undici dispatcher that skips verification
 *   - cookies (csrftoken + sessionid) are tracked in a manual jar so the
 *     session mutation contract is exercised end-to-end
 */

import { createHmac } from "node:crypto";
import { beforeAll, describe, expect, it } from "vitest";

// Caddy uses tls internal (self-signed). Disable verification for this test
// process so Node's fetch can dial the live proxy over HTTPS.
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const BASE_URL = process.env.REAL_BACKEND_URL || "https://proxy:8443";
const USERNAME = process.env.SMOKE_USERNAME || "orgadmin";
const PASSWORD = process.env.SMOKE_PASSWORD || "SecurePass1234";
const TRUSTED_ORIGIN = process.env.CSRF_TRUSTED_ORIGIN || "https://localhost:8443";

const cookies = new Map();

function parseSetCookie(headerValue) {
  // "name=value; Path=/; HttpOnly; Secure"
  const [pair] = headerValue.split(";");
  const idx = pair.indexOf("=");
  if (idx === -1) return null;
  return [pair.slice(0, idx).trim(), pair.slice(idx + 1).trim()];
}

function cookieHeader() {
  return [...cookies.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
}

async function realFetch(path, init = {}) {
  const headers = {
    Referer: `${TRUSTED_ORIGIN}/`,
    Origin: TRUSTED_ORIGIN,
    ...(init.headers || {}),
  };
  const cookieValue = cookieHeader();
  if (cookieValue) headers.Cookie = cookieValue;

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const setCookieHeaders = response.headers.getSetCookie
    ? response.headers.getSetCookie()
    : [];
  for (const raw of setCookieHeaders) {
    const parsed = parseSetCookie(raw);
    if (parsed) cookies.set(parsed[0], parsed[1]);
  }
  return response;
}

function hmacHex(secret, payload) {
  return createHmac("sha256", secret).update(payload).digest("hex");
}

function nonce() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

async function waitForHealth() {
  const deadline = Date.now() + 60_000;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const res = await realFetch("/api/health/");
      if (res.ok) return;
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`Backend health never became ready: ${lastErr || "timeout"}`);
}

async function fetchCsrfToken() {
  const res = await realFetch("/api/auth/csrf/");
  expect(res.status).toBe(200);
  const body = await res.json();
  return body.csrfToken;
}

async function signedMutation(method, path, bodyObj) {
  const csrfToken = cookies.get("csrftoken") || (await fetchCsrfToken());
  const ts = new Date().toISOString();
  const nonceValue = nonce();
  const signingPayload = [method, path, ts, nonceValue].join("\n");
  const signature = hmacHex(csrfToken, signingPayload);

  return realFetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
      "X-Request-Timestamp": ts,
      "X-Request-Nonce": nonceValue,
      "X-Session-Signature": signature,
    },
    body: bodyObj === undefined ? undefined : JSON.stringify(bodyObj),
  });
}

describe("real backend integration (no mocks, real HTTPS through Caddy)", () => {
  beforeAll(async () => {
    await waitForHealth();
  }, 75_000);

  it("health endpoint responds without auth", async () => {
    const res = await realFetch("/api/health/");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.service).toBe("harborops-backend");
  });

  it("csrf endpoint sets csrftoken cookie and returns token value", async () => {
    const token = await fetchCsrfToken();
    expect(typeof token).toBe("string");
    expect(token.length).toBeGreaterThan(10);
    // Django returns a per-request masked token; the cookie stores the
    // underlying secret. Assert the cookie was set, not string equality.
    expect(cookies.get("csrftoken")).toBeTruthy();
  });

  it("login, me, and roles flow against real backend", async () => {
    const csrfToken = await fetchCsrfToken();
    const loginRes = await realFetch("/api/auth/login/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
    });
    expect(loginRes.status).toBe(200);

    const meRes = await realFetch("/api/auth/me/");
    expect(meRes.status).toBe(200);
    const me = await meRes.json();
    expect(me.username).toBe(USERNAME);

    const rolesRes = await realFetch("/api/access/me/roles/");
    expect(rolesRes.status).toBe(200);
    const roles = await rolesRes.json();
    expect(Array.isArray(roles)).toBe(true);
    expect(roles.length).toBeGreaterThan(0);
  });

  it("trips listing reflects org admin access through real RBAC", async () => {
    const res = await realFetch("/api/trips/");
    expect(res.status).toBe(200);
    const trips = await res.json();
    expect(Array.isArray(trips)).toBe(true);
  });

  it("signed favorite create + delete round-trip through session signing middleware", async () => {
    const favoritePayload = {
      kind: "trip",
      reference_id: `vitest-${Date.now()}`,
    };
    const createRes = await signedMutation(
      "POST",
      "/api/auth/favorites/",
      favoritePayload
    );
    expect([201, 409]).toContain(createRes.status);

    // If we got 409 (already favorited), find the existing row; else use created id.
    let favoriteId;
    if (createRes.status === 201) {
      const created = await createRes.json();
      favoriteId = created.id;
    } else {
      const listRes = await realFetch("/api/auth/favorites/");
      const list = await listRes.json();
      const match = list.find(
        (item) =>
          item.kind === favoritePayload.kind &&
          item.reference_id === favoritePayload.reference_id
      );
      favoriteId = match?.id;
    }
    expect(favoriteId).toBeTruthy();

    const deleteRes = await signedMutation(
      "DELETE",
      `/api/auth/favorites/${favoriteId}/`
    );
    expect(deleteRes.status).toBe(204);
  });

  it("unsigned session mutation is rejected by signing middleware", async () => {
    // Intentionally omit X-Request-Timestamp/Nonce/Signature on a mutating call.
    const csrfToken = cookies.get("csrftoken") || (await fetchCsrfToken());
    const res = await realFetch("/api/auth/favorites/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ kind: "trip", reference_id: "unsigned-attempt" }),
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.code).toMatch(/session/);
  });
});

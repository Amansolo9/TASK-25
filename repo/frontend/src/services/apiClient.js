export function createApiClient(baseUrl) {
  function getCookieValue(name) {
    if (typeof document === "undefined") return "";
    const needle = `${name}=`;
    const parts = document.cookie.split(";").map((part) => part.trim());
    for (const part of parts) {
      if (part.startsWith(needle)) {
        return decodeURIComponent(part.slice(needle.length));
      }
    }
    return "";
  }

  function createReplayNonce() {
    if (globalThis.crypto?.randomUUID) {
      return globalThis.crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  }

  function buildApiError(response, payload) {
    let message = payload?.detail;
    if (!message && payload && typeof payload === "object") {
      const entries = Object.entries(payload)
        .map(([field, value]) => {
          if (Array.isArray(value)) {
            return `${field}: ${value.join(", ")}`;
          }
          if (typeof value === "string") {
            return `${field}: ${value}`;
          }
          return null;
        })
        .filter(Boolean);
      if (entries.length) {
        message = entries.join(" | ");
      }
    }
    if (!message) {
      message = `Request failed (${response.status})`;
    }
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  async function fetchCsrfToken() {
    const response = await fetch(`${baseUrl}/api/auth/csrf/`, { credentials: "include" });
    const data = await response.json();
    return data.csrfToken;
  }

  async function hmacSha256Hex(secret, payload) {
    if (!globalThis.crypto?.subtle) {
      throw new Error("Web Crypto API unavailable for request signing");
    }
    const encoder = new TextEncoder();
    const key = await globalThis.crypto.subtle.importKey(
      "raw",
      encoder.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const digest = await globalThis.crypto.subtle.sign("HMAC", key, encoder.encode(payload));
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  async function request(path, options = {}, includeCsrf = false) {
    const headers = { ...(options.headers || {}) };
    const method = (options.method || "GET").toUpperCase();
    const isMutating = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    let csrfToken = headers["X-CSRFToken"] || getCookieValue("csrftoken");
    if (includeCsrf) {
      csrfToken = await fetchCsrfToken();
      headers["X-CSRFToken"] = csrfToken;
    }
    if (isMutating) {
      if (!csrfToken) {
        csrfToken = await fetchCsrfToken();
        headers["X-CSRFToken"] = csrfToken;
      }
      const requestTimestamp = new Date().toISOString();
      const requestNonce = createReplayNonce();
      headers["X-Request-Timestamp"] = requestTimestamp;
      headers["X-Request-Nonce"] = requestNonce;

      const signaturePayload = [method, path, requestTimestamp, requestNonce].join("\n");
      headers["X-Session-Signature"] = await hmacSha256Hex(csrfToken, signaturePayload);
    }

    const response = await fetch(`${baseUrl}${path}`, {
      credentials: "include",
      ...options,
      headers,
    });

    let payload = null;
    if (response.status !== 204) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      throw buildApiError(response, payload);
    }

    return payload;
  }

  return {
    fetchCsrfToken,
    request,
  };
}

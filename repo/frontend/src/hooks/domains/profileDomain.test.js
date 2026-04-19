import { describe, expect, it } from "vitest";

import { canRequestUnmaskedByRoles, initialProfileForms } from "./profileDomain";

describe("profileDomain", () => {
  it("provides initialized profile form shape", () => {
    expect(initialProfileForms.prefLocale).toBe("en");
    expect(initialProfileForms.exportFormat).toBe("json");
  });

  it("detects unmasked export permission by role", () => {
    expect(canRequestUnmaskedByRoles([{ code: "senior" }])).toBe(false);
    expect(canRequestUnmaskedByRoles([{ code: "org_admin" }])).toBe(true);
  });
});

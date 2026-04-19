import { expect, test } from "@playwright/test";

const STEP_PAUSE_MS = 5500;

async function pause(page) {
  await page.waitForTimeout(STEP_PAUSE_MS);
}

async function fillSlow(locator, value) {
  await locator.click();
  await locator.fill("");
  await locator.type(value, { delay: 65 });
}

test("recorded major flows walkthrough (3-5 min)", async ({ page }) => {
  const suffix = Date.now().toString().slice(-6);
  const warehouseName = `PW Warehouse ${suffix}`;
  const zoneName = `PW Zone ${suffix}`;
  const locationCode = `PW-${suffix}`;
  const partnerCode = `PW-PARTNER-${suffix}`;
  const tripTitle = `PW Trip ${suffix}`;
  const jobKey = `pw-job-${suffix}`;

  await page.goto("/");
  await expect(page.getByText("HarborOps Offline Transit & Logistics")).toBeVisible();
  await pause(page);

  await fillSlow(page.locator("#username"), "orgadmin");
  await fillSlow(page.locator("#password"), "SecurePass1234");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("orgadmin")).toBeVisible();
  await pause(page);

  await page.getByRole("button", { name: "Warehouse" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Warehouse name"), warehouseName);
  await fillSlow(page.getByPlaceholder("Region"), "North");
  await page.getByRole("button", { name: "Add Warehouse" }).click();
  await expect(page.getByRole("heading", { name: warehouseName })).toBeVisible();
  await pause(page);

  await page.locator("form").nth(1).locator("select").first().selectOption({ label: warehouseName });
  await fillSlow(page.getByPlaceholder("Zone name"), zoneName);
  await fillSlow(page.getByPlaceholder("Temperature zone"), "cold");
  await fillSlow(page.getByPlaceholder("Hazmat class"), "none");
  await page.getByRole("button", { name: "Add Zone" }).click();
  await pause(page);

  await page.locator("form").nth(2).locator("select").first().selectOption({ label: zoneName });
  await fillSlow(page.getByPlaceholder("Location code"), locationCode);
  await fillSlow(page.getByPlaceholder("Capacity", { exact: true }), "120");
  await fillSlow(page.getByPlaceholder("Capacity unit"), "units");
  await fillSlow(page.getByPlaceholder('Location attributes JSON, e.g. {"aisle":"A"}'), '{"aisle":"A","rack":"1"}');
  await page.getByRole("button", { name: "Add Location" }).click();
  await expect(page.getByText(locationCode)).toBeVisible();
  await pause(page);

  await page.locator("form").nth(3).locator("select").first().selectOption("owner");
  await fillSlow(page.getByPlaceholder("External code"), partnerCode);
  await fillSlow(page.getByPlaceholder("Display name"), "Playwright Partner");
  await fillSlow(page.getByPlaceholder("Effective start (YYYY-MM-DD)"), "2026-05-01");
  await fillSlow(page.getByPlaceholder("Effective end (optional)"), "2026-12-31");
  await fillSlow(page.getByPlaceholder('Partner metadata JSON, e.g. {"contract":"v1"}'), '{"contract":"v1"}');
  await page.getByRole("button", { name: "Add Partner Record" }).click();
  await expect(page.getByText(partnerCode)).toBeVisible();
  await pause(page);

  await page.getByRole("button", { name: "Trips" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Trip title"), tripTitle);
  await fillSlow(page.getByPlaceholder("Service date (YYYY-MM-DD)"), "2026-06-01");
  await fillSlow(page.getByPlaceholder("Origin"), "North Hub");
  await fillSlow(page.getByPlaceholder("Destination"), "City Clinic");
  await fillSlow(page.getByPlaceholder("Pickup window start (ISO)"), "2026-06-01T10:00");
  await fillSlow(page.getByPlaceholder("Pickup window end (ISO)"), "2026-06-01T11:00");
  await fillSlow(page.getByPlaceholder("Signup deadline (ISO)"), "2026-06-01T07:30");
  await page
    .locator("textarea[placeholder='Waypoints (one per line: name|address)']")
    .fill("North Gate|100 Harbor St\nClinic Entrance|10 Health Ave");
  await page.getByRole("button", { name: "Save Trip" }).click();
  await expect(page.getByRole("heading", { name: tripTitle })).toBeVisible();
  await pause(page);

  const tripCard = page.locator("div").filter({ has: page.getByRole("heading", { name: tripTitle }) }).first();
  await tripCard.getByRole("button", { name: "Publish", exact: true }).click();
  await pause(page);

  await page.getByLabel("Trip for fare estimate").selectOption({ label: tripTitle });
  await page.getByLabel("Seats for fare estimate").fill("2");
  await page.getByRole("button", { name: "Estimate" }).click();
  await expect(page.getByText("Estimated total:")).toBeVisible();
  await pause(page);

  await page.getByRole("button", { name: "Inventory" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Plan title"), `PW Plan ${suffix}`);
  await fillSlow(page.getByPlaceholder("Asset type"), "wheelchair");
  await page.getByRole("button", { name: "Create Plan" }).click();
  await pause(page);

  await page.getByRole("button", { name: "Jobs" }).click();
  await pause(page);

  await fillSlow(page.getByLabel("Job type"), "ingest.folder_scan");
  await fillSlow(page.getByLabel("Source path"), "/app/offline_dropzone");
  await fillSlow(page.getByLabel("Dedupe key"), jobKey);
  await page.getByRole("button", { name: "Create Job" }).click();
  await expect(page.getByRole("heading", { name: "ingest.folder_scan" }).first()).toBeVisible();
  await pause(page);

  await fillSlow(page.getByLabel("Source signature"), `manifest-${suffix}`);
  await fillSlow(page.getByLabel("Attachment content hash"), `hash-${suffix}`);
  await page.getByRole("button", { name: "Check Duplicate" }).click();
  await expect(page.getByText("Duplicate:")).toBeVisible();
  await pause(page);

  await page.getByRole("button", { name: "Profile" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Display name"), `Traveler ${suffix}`);
  await fillSlow(page.getByPlaceholder("Traveler identifier"), `TR-${suffix}`);
  await fillSlow(page.getByPlaceholder("Government ID"), `GOV-${suffix}`);
  await fillSlow(page.getByPlaceholder("Credential number"), `CR-${suffix}`);
  await page.getByRole("button", { name: "Save Traveler Profile" }).click();
  await expect(page.getByText(`Traveler ${suffix}`)).toBeVisible();
  await pause(page);

  await page.locator("select").filter({ has: page.locator("option[value='trip']") }).first().selectOption("trip");
  await fillSlow(page.getByPlaceholder("reference id").first(), `trip-${suffix}`);
  await page.getByRole("button", { name: "Add Favorite" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("reference id").nth(1), `plan-${suffix}`);
  await page.getByRole("button", { name: "Add Comparison" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Reminder title"), `Reminder ${suffix}`);
  await fillSlow(page.getByPlaceholder("Reminder details"), "Take meds at 8 PM.");
  await page.getByRole("button", { name: "Create Reminder" }).click();
  await pause(page);

  await fillSlow(page.getByPlaceholder("Export format"), "json");
  await page.getByRole("button", { name: "Request Export" }).click();
  await expect(page.getByText("Status:")).toBeVisible();
  await pause(page);

  await page.waitForTimeout(30000);

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await pause(page);
});

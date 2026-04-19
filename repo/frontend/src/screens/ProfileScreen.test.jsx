import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProfileScreen } from "./ProfileScreen";

describe("ProfileScreen", () => {
  it("invokes reminder acknowledge action", async () => {
    const acknowledgeReminder = vi.fn();

    render(
      <ProfileScreen
        profileForms={{
          favoriteKind: "trip",
          favoriteRef: "",
          comparisonKind: "plan",
          comparisonRef: "",
          reminderTitle: "",
          reminderMessage: "",
          prefLocale: "en",
          prefTimezone: "UTC",
          prefLargeText: false,
          prefHighContrast: false,
          travelerDisplayName: "",
          travelerIdentifier: "",
          travelerGovernmentId: "",
          travelerCredentialNumber: "",
          exportIncludeUnmasked: false,
          exportJustification: "",
          exportFormat: "json",
          deletionRetentionNotice: "",
        }}
        setProfileForms={vi.fn()}
        preference={null}
        updatePreference={vi.fn((e) => e.preventDefault())}
        createFavorite={vi.fn((e) => e.preventDefault())}
        favorites={[]}
        deleteFavorite={vi.fn()}
        createComparison={vi.fn((e) => e.preventDefault())}
        comparisons={[]}
        deleteComparison={vi.fn()}
        createReminder={vi.fn((e) => e.preventDefault())}
        alerts={[{ id: 10, title: "Med check", message: "Bring card", acknowledged: false }]}
        acknowledgeReminder={acknowledgeReminder}
        travelerProfiles={[]}
        saveTravelerProfile={vi.fn((e) => e.preventDefault())}
        revealTravelerField={vi.fn()}
        travelerReveal={{}}
        canRequestUnmasked={false}
        exportRequests={[]}
        requestExport={vi.fn((e) => e.preventDefault())}
        submitDeletionRequest={vi.fn((e) => e.preventDefault())}
        profileError=""
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    expect(acknowledgeReminder).toHaveBeenCalledWith(10);
  });
});

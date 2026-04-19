import { useMemo } from "react";

export function useWorkspaceScreens({ sessionRoles, roleScreens, statsByScreen }) {
  const allScreens = useMemo(() => {
    const screens = new Set();
    sessionRoles.forEach((role) => {
      (roleScreens[role.code] || []).forEach((screen) => screens.add(screen));
    });
    return Array.from(screens);
  }, [sessionRoles, roleScreens]);

  const roleLabel = useMemo(() => {
    if (!sessionRoles.length) return "No role assigned";
    return sessionRoles.map((role) => role.name).join(", ");
  }, [sessionRoles]);

  const quickStats = useMemo(
    () =>
      Object.entries(statsByScreen).map(([screen, value]) => ({
        screen,
        value,
      })),
    [statsByScreen]
  );

  return {
    allScreens,
    roleLabel,
    quickStats,
  };
}

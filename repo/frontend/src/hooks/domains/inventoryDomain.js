export function computeInventoryMetrics({ plans = [], tasks = [], lines = [] }) {
  const completedTasks = tasks.filter((task) => task.status === "completed").length;
  const reviewTasks = tasks.filter((task) => task.status === "review").length;
  const reviewRequiredLines = lines.filter((line) => line.requires_review).length;
  const closedLines = lines.filter((line) => line.closed).length;
  return {
    totals: {
      plans: plans.length,
      tasks: tasks.length,
      completedTasks,
      reviewTasks,
      reviewRequiredLines,
      closedLines,
    },
    varianceCounts: {
      missing: lines.filter((line) => line.variance_type === "missing").length,
      extra: lines.filter((line) => line.variance_type === "extra").length,
      data_mismatch: lines.filter((line) => line.variance_type === "data_mismatch").length,
    },
  };
}

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { computeInventoryMetrics } from "../hooks/domains/inventoryDomain";

export function InventoryScreen({
  renderCards,
  plans,
  tasks,
  lines,
  statusVariant,
  planForm = { title: "", region: "", asset_type: "", mode: "full" },
  setPlanForm = () => {},
  taskForm = { plan: "", location: "", assignee: "", status: "pending" },
  setTaskForm = () => {},
  lineForm = {
    task: "",
    asset_code: "",
    observed_asset_code: "",
    observed_location_code: "",
    attribute_mismatch: false,
    book_quantity: 0,
    physical_quantity: 0,
  },
  setLineForm = () => {},
  correctiveForm = { cause: "", action: "", owner: "", due_date: "", evidence: "", review_notes: "" },
  setCorrectiveForm = () => {},
  variancePreview = "none",
  createInventoryPlan = (event) => event.preventDefault(),
  createInventoryTask = (event) => event.preventDefault(),
  createCountLine = (event) => event.preventDefault(),
  createCorrectiveAction = () => {},
  approveCorrectiveAction = () => {},
  acknowledgeCorrectiveAction = () => {},
  closeVariance = () => {},
  locations = [],
  operationsError = "",
}) {
  const { totals, varianceCounts } = computeInventoryMetrics({ plans, tasks, lines });

  const metrics = [
    { label: "Plans", value: totals.plans },
    { label: "Tasks", value: `${totals.completedTasks}/${totals.tasks} complete` },
    { label: "In review", value: totals.reviewTasks },
    { label: "Review required", value: totals.reviewRequiredLines },
    { label: "Closures", value: `${totals.closedLines}/${lines.length}` },
  ];

  return (
    <>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Inventory Operations</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={createInventoryPlan}>
            <Input value={planForm.title} onChange={(e) => setPlanForm((p) => ({ ...p, title: e.target.value }))} placeholder="Plan title" />
            <Input value={planForm.region} onChange={(e) => setPlanForm((p) => ({ ...p, region: e.target.value }))} placeholder="Region" />
            <Input value={planForm.asset_type} onChange={(e) => setPlanForm((p) => ({ ...p, asset_type: e.target.value }))} placeholder="Asset type" />
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={planForm.mode} onChange={(e) => setPlanForm((p) => ({ ...p, mode: e.target.value }))}>
              <option value="full">full</option>
              <option value="spot">spot</option>
            </select>
            <Button className="md:col-span-2">Create Plan</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-3" onSubmit={createInventoryTask}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={taskForm.plan} onChange={(e) => setTaskForm((p) => ({ ...p, plan: e.target.value }))}>
              <option value="">Select plan</option>
              {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.title}</option>)}
            </select>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={taskForm.location} onChange={(e) => setTaskForm((p) => ({ ...p, location: e.target.value }))}>
              <option value="">Select location</option>
              {locations.map((location) => <option key={location.id} value={location.id}>{location.code}</option>)}
            </select>
            <Input value={taskForm.assignee} onChange={(e) => setTaskForm((p) => ({ ...p, assignee: e.target.value }))} placeholder="Assignee user id" />
            <Button className="md:col-span-3">Distribute Task</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-3" onSubmit={createCountLine}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={lineForm.task} onChange={(e) => setLineForm((p) => ({ ...p, task: e.target.value }))}>
              <option value="">Select task</option>
              {tasks.map((task) => <option key={task.id} value={task.id}>Task #{task.id}</option>)}
            </select>
            <Input value={lineForm.asset_code} onChange={(e) => setLineForm((p) => ({ ...p, asset_code: e.target.value }))} placeholder="Expected asset code" />
            <Input value={lineForm.observed_asset_code} onChange={(e) => setLineForm((p) => ({ ...p, observed_asset_code: e.target.value }))} placeholder="Observed asset code" />
            <Input value={lineForm.observed_location_code} onChange={(e) => setLineForm((p) => ({ ...p, observed_location_code: e.target.value }))} placeholder="Observed location" />
            <Input type="number" value={lineForm.book_quantity} onChange={(e) => setLineForm((p) => ({ ...p, book_quantity: e.target.value }))} placeholder="Book qty" />
            <Input type="number" value={lineForm.physical_quantity} onChange={(e) => setLineForm((p) => ({ ...p, physical_quantity: e.target.value }))} placeholder="Physical qty" />
            <label className="md:col-span-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={Boolean(lineForm.attribute_mismatch)} onChange={(e) => setLineForm((p) => ({ ...p, attribute_mismatch: e.target.checked }))} />
              Attribute mismatch detected
            </label>
            <p className="md:col-span-3 text-xs text-muted-foreground">Variance preview: {variancePreview}</p>
            <Button className="md:col-span-3">Submit Count Line</Button>
          </form>

          <div className="grid gap-3 md:grid-cols-2">
            <Input value={correctiveForm.cause} onChange={(e) => setCorrectiveForm((p) => ({ ...p, cause: e.target.value }))} placeholder="Corrective cause" />
            <Input value={correctiveForm.owner} onChange={(e) => setCorrectiveForm((p) => ({ ...p, owner: e.target.value }))} placeholder="Corrective owner user id" />
            <Input value={correctiveForm.due_date} onChange={(e) => setCorrectiveForm((p) => ({ ...p, due_date: e.target.value }))} placeholder="Due date (YYYY-MM-DD)" />
            <Input value={correctiveForm.evidence} onChange={(e) => setCorrectiveForm((p) => ({ ...p, evidence: e.target.value }))} placeholder="Evidence" />
            <Input className="md:col-span-2" value={correctiveForm.action} onChange={(e) => setCorrectiveForm((p) => ({ ...p, action: e.target.value }))} placeholder="Corrective action" />
            <Input className="md:col-span-2" value={correctiveForm.review_notes} onChange={(e) => setCorrectiveForm((p) => ({ ...p, review_notes: e.target.value }))} placeholder="Closure review notes" />
          </div>

          {operationsError && <p className="text-sm text-rose-700">{operationsError}</p>}
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent className="text-lg font-semibold">{metric.value}</CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Variance Hotspots</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm sm:grid-cols-3">
          <div className="rounded-md border p-3">Missing: {varianceCounts.missing}</div>
          <div className="rounded-md border p-3">Extra: {varianceCounts.extra}</div>
          <div className="rounded-md border p-3">Data mismatch: {varianceCounts.data_mismatch}</div>
        </CardContent>
      </Card>

      {renderCards(
        plans,
        (plan) => (
          <Card key={plan.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">{plan.title}</CardTitle>
                <Badge variant={statusVariant(plan.status)}>{plan.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>{plan.region} | {plan.asset_type}</p>
              <p>Mode: {plan.mode}</p>
            </CardContent>
          </Card>
        ),
        "No inventory plans available."
      )}

      {!!lines.length && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Variance Closure Workflow</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {lines.map((line) => (
              <div key={line.id} className="rounded-md border p-3 text-sm">
                <p>Line #{line.id} | {line.variance_type || "none"} | review {line.requires_review ? "yes" : "no"}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => createCorrectiveAction(line.id)}>Create Action</Button>
                  <Button size="sm" variant="secondary" onClick={() => approveCorrectiveAction(line.id)}>Approve Action</Button>
                  <Button size="sm" variant="secondary" onClick={() => acknowledgeCorrectiveAction(line.id)}>Acknowledge</Button>
                  <Button size="sm" variant="secondary" onClick={() => closeVariance(line.id)}>Close Variance</Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </>
  );
}

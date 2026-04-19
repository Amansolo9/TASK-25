import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

export function WarehouseScreen({
  renderCards,
  warehouses,
  zones = [],
  locations = [],
  partners = [],
  warehouseForm = { name: "", region: "", is_active: true },
  setWarehouseForm = () => {},
  zoneForm = { warehouse: "", name: "", temperature_zone: "", hazmat_class: "", is_active: true },
  setZoneForm = () => {},
  locationForm = { zone: "", code: "", capacity_limit: 0, capacity_unit: "units", attributes_json: "{}", is_active: true },
  setLocationForm = () => {},
  partnerForm = { partner_type: "owner", external_code: "", display_name: "", effective_start: "", effective_end: "", data_json: "{}" },
  setPartnerForm = () => {},
  createWarehouse = (event) => event.preventDefault(),
  createZone = (event) => event.preventDefault(),
  createLocation = (event) => event.preventDefault(),
  createPartner = (event) => event.preventDefault(),
  operationsError = "",
}) {
  return (
    <>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Warehouse Master Data</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={createWarehouse}>
            <Input value={warehouseForm.name} onChange={(e) => setWarehouseForm((p) => ({ ...p, name: e.target.value }))} placeholder="Warehouse name" />
            <Input value={warehouseForm.region} onChange={(e) => setWarehouseForm((p) => ({ ...p, region: e.target.value }))} placeholder="Region" />
            <Button>Add Warehouse</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-4" onSubmit={createZone}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={zoneForm.warehouse} onChange={(e) => setZoneForm((p) => ({ ...p, warehouse: e.target.value }))}>
              <option value="">Select warehouse</option>
              {warehouses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <Input value={zoneForm.name} onChange={(e) => setZoneForm((p) => ({ ...p, name: e.target.value }))} placeholder="Zone name" />
            <Input value={zoneForm.temperature_zone} onChange={(e) => setZoneForm((p) => ({ ...p, temperature_zone: e.target.value }))} placeholder="Temperature zone" />
            <Input value={zoneForm.hazmat_class} onChange={(e) => setZoneForm((p) => ({ ...p, hazmat_class: e.target.value }))} placeholder="Hazmat class" />
            <Button className="md:col-span-4">Add Zone</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-3" onSubmit={createLocation}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={locationForm.zone} onChange={(e) => setLocationForm((p) => ({ ...p, zone: e.target.value }))}>
              <option value="">Select zone</option>
              {zones.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <Input value={locationForm.code} onChange={(e) => setLocationForm((p) => ({ ...p, code: e.target.value }))} placeholder="Location code" />
            <Input type="number" value={locationForm.capacity_limit} onChange={(e) => setLocationForm((p) => ({ ...p, capacity_limit: e.target.value }))} placeholder="Capacity" />
            <Input value={locationForm.capacity_unit} onChange={(e) => setLocationForm((p) => ({ ...p, capacity_unit: e.target.value }))} placeholder="Capacity unit" />
            <Input className="md:col-span-2" value={locationForm.attributes_json} onChange={(e) => setLocationForm((p) => ({ ...p, attributes_json: e.target.value }))} placeholder='Location attributes JSON, e.g. {"aisle":"A"}' />
            <Button className="md:col-span-3">Add Location</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-3" onSubmit={createPartner}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={partnerForm.partner_type} onChange={(e) => setPartnerForm((p) => ({ ...p, partner_type: e.target.value }))}>
              <option value="owner">owner</option>
              <option value="supplier">supplier</option>
              <option value="carrier">carrier</option>
            </select>
            <Input value={partnerForm.external_code} onChange={(e) => setPartnerForm((p) => ({ ...p, external_code: e.target.value }))} placeholder="External code" />
            <Input value={partnerForm.display_name} onChange={(e) => setPartnerForm((p) => ({ ...p, display_name: e.target.value }))} placeholder="Display name" />
            <Input value={partnerForm.effective_start} onChange={(e) => setPartnerForm((p) => ({ ...p, effective_start: e.target.value }))} placeholder="Effective start (YYYY-MM-DD)" />
            <Input value={partnerForm.effective_end} onChange={(e) => setPartnerForm((p) => ({ ...p, effective_end: e.target.value }))} placeholder="Effective end (optional)" />
            <Input className="md:col-span-3" value={partnerForm.data_json} onChange={(e) => setPartnerForm((p) => ({ ...p, data_json: e.target.value }))} placeholder='Partner metadata JSON, e.g. {"contract":"v1"}' />
            <Button className="md:col-span-3">Add Partner Record</Button>
          </form>

          {operationsError && <p className="text-sm text-rose-700">{operationsError}</p>}
        </CardContent>
      </Card>

      {renderCards(
        warehouses,
        (item) => (
          <Card key={item.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">{item.name}</CardTitle>
                <Badge variant={item.is_active ? "success" : "danger"}>{item.is_active ? "active" : "inactive"}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>Region: {item.region}</p>
              <p>Warehouse ID: {item.id}</p>
            </CardContent>
          </Card>
        ),
        "No warehouses configured."
      )}

      {!!locations.length && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Locations</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {locations.map((location) => (
              <p key={location.id}>#{location.id} {location.code} capacity {location.capacity_limit} {location.capacity_unit}</p>
            ))}
          </CardContent>
        </Card>
      )}

      {!!partners.length && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Partner Records</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {partners.map((partner) => (
              <p key={partner.id}>{partner.partner_type} {partner.external_code} ({partner.effective_start} to {partner.effective_end || "open"})</p>
            ))}
          </CardContent>
        </Card>
      )}
    </>
  );
}

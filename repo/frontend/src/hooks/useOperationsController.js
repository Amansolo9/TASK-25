import { useCallback, useMemo, useState } from "react";

const initialWarehouseForm = { name: "", region: "", is_active: true };
const initialZoneForm = { warehouse: "", name: "", temperature_zone: "", hazmat_class: "", is_active: true };
const initialLocationForm = {
  zone: "",
  code: "",
  capacity_limit: 0,
  capacity_unit: "units",
  attributes_json: "{}",
  is_active: true,
};
const initialPartnerForm = {
  partner_type: "owner",
  external_code: "",
  display_name: "",
  effective_start: "",
  effective_end: "",
  data_json: "{}",
};
const initialPlanForm = { title: "", region: "", asset_type: "", mode: "full" };
const initialTaskForm = { plan: "", location: "", assignee: "", status: "pending" };
const initialLineForm = {
  task: "",
  asset_code: "",
  observed_asset_code: "",
  observed_location_code: "",
  attribute_mismatch: false,
  book_quantity: 0,
  physical_quantity: 0,
};
const initialCorrectiveForm = {
  cause: "",
  action: "",
  owner: "",
  due_date: "",
  evidence: "",
  review_notes: "",
};
const initialVerificationRequestForm = { attestation: "", is_high_risk: false };
const initialDocumentForm = {
  verification_id: "",
  document_type: "government_id",
  uploaded_file: null,
};

function safeParseJson(value) {
  try {
    return JSON.parse(value || "{}");
  } catch {
    return null;
  }
}

export function useOperationsController({ api, setStatus }) {
  const [warehouses, setWarehouses] = useState([]);
  const [zones, setZones] = useState([]);
  const [locations, setLocations] = useState([]);
  const [partners, setPartners] = useState([]);
  const [plans, setPlans] = useState([]);
  const [inventoryTasks, setInventoryTasks] = useState([]);
  const [inventoryLines, setInventoryLines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [verificationRequests, setVerificationRequests] = useState([]);
  const [verificationComment, setVerificationComment] = useState("");
  const [warehouseForm, setWarehouseForm] = useState(initialWarehouseForm);
  const [zoneForm, setZoneForm] = useState(initialZoneForm);
  const [locationForm, setLocationForm] = useState(initialLocationForm);
  const [partnerForm, setPartnerForm] = useState(initialPartnerForm);
  const [planForm, setPlanForm] = useState(initialPlanForm);
  const [taskForm, setTaskForm] = useState(initialTaskForm);
  const [lineForm, setLineForm] = useState(initialLineForm);
  const [correctiveForm, setCorrectiveForm] = useState(initialCorrectiveForm);
  const [verificationRequestForm, setVerificationRequestForm] = useState(initialVerificationRequestForm);
  const [documentForm, setDocumentForm] = useState(initialDocumentForm);
  const [verificationOpenResult, setVerificationOpenResult] = useState("");
  const [operationsError, setOperationsError] = useState("");

  const variancePreview = useMemo(() => {
    const book = Number(lineForm.book_quantity || 0);
    const physical = Number(lineForm.physical_quantity || 0);
    if (lineForm.attribute_mismatch || (lineForm.observed_asset_code && lineForm.observed_asset_code !== lineForm.asset_code)) {
      return "data_mismatch";
    }
    if (physical < book) return "missing";
    if (physical > book) return "extra";
    return "none";
  }, [lineForm]);

  const loadWarehouses = useCallback(async () => {
    try {
      const data = await api("/api/warehouses/");
      setWarehouses(data || []);
    } catch {
      setWarehouses([]);
    }
  }, [api]);

  const loadZones = useCallback(async () => {
    try {
      const data = await api("/api/warehouses/zones/");
      setZones(data || []);
    } catch {
      setZones([]);
    }
  }, [api]);

  const loadLocations = useCallback(async () => {
    try {
      const data = await api("/api/warehouses/locations/");
      setLocations(data || []);
    } catch {
      setLocations([]);
    }
  }, [api]);

  const loadPartners = useCallback(async () => {
    try {
      const data = await api("/api/warehouses/partners/");
      setPartners(data || []);
    } catch {
      setPartners([]);
    }
  }, [api]);

  const loadPlans = useCallback(async () => {
    try {
      const data = await api("/api/inventory/plans/");
      setPlans(data || []);
    } catch {
      setPlans([]);
    }
  }, [api]);

  const loadInventoryTasks = useCallback(async () => {
    try {
      const data = await api("/api/inventory/tasks/");
      setInventoryTasks(data || []);
    } catch {
      setInventoryTasks([]);
    }
  }, [api]);

  const loadInventoryLines = useCallback(async () => {
    try {
      const data = await api("/api/inventory/lines/");
      setInventoryLines(data || []);
    } catch {
      setInventoryLines([]);
    }
  }, [api]);

  const loadAlerts = useCallback(async () => {
    try {
      const data = await api("/api/monitoring/alerts/");
      setAlerts(data || []);
    } catch {
      setAlerts([]);
    }
  }, [api]);

  const loadVerificationRequests = useCallback(async () => {
    try {
      const data = await api("/api/auth/verification-requests/");
      setVerificationRequests(data || []);
    } catch {
      setVerificationRequests([]);
    }
  }, [api]);

  const handleVerificationReview = useCallback(
    async (verificationId, approved) => {
      try {
        await api(
          `/api/auth/verification-requests/${verificationId}/review/`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              verification_request: verificationId,
              approved,
              comments: verificationComment,
            }),
          },
          true
        );
        setVerificationComment("");
        await loadVerificationRequests();
        setStatus({ loading: false, message: "Verification review submitted", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadVerificationRequests, setStatus, verificationComment]
  );

  const submitVerificationRequest = useCallback(
    async (event) => {
      event.preventDefault();
      setOperationsError("");
      try {
        await api(
          "/api/auth/verification-requests/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(verificationRequestForm),
          },
          true
        );
        setVerificationRequestForm(initialVerificationRequestForm);
        await loadVerificationRequests();
        setStatus({ loading: false, message: "Verification request submitted", tone: "success" });
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadVerificationRequests, setStatus, verificationRequestForm]
  );

  const uploadVerificationDocument = useCallback(
    async (event) => {
      event.preventDefault();
      setOperationsError("");
      const file = documentForm.uploaded_file;
      if (!file) {
        setOperationsError("Select a document file first.");
        return;
      }
      const allowed = ["image/jpeg", "image/png", "application/pdf"];
      if (!allowed.includes(file.type)) {
        setOperationsError("Allowed file types: jpeg, png, pdf.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setOperationsError("Maximum file size is 10 MB.");
        return;
      }
      try {
        const formData = new FormData();
        formData.append("document_type", documentForm.document_type);
        formData.append("uploaded_file", file);
        formData.append("file_name", file.name);
        formData.append("mime_type", file.type);
        formData.append("file_size_bytes", String(file.size));
        await api(
          `/api/auth/verification-requests/${documentForm.verification_id}/documents/upload/`,
          { method: "POST", body: formData },
          true
        );
        setDocumentForm((prev) => ({ ...prev, uploaded_file: null }));
        await loadVerificationRequests();
        setStatus({ loading: false, message: "Verification document uploaded", tone: "success" });
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, documentForm, loadVerificationRequests, setStatus]
  );

  const openVerificationDocument = useCallback(
    async (documentId) => {
      setOperationsError("");
      try {
        await api(`/api/auth/verification-documents/${documentId}/open/`);
        setVerificationOpenResult(`Document ${documentId} opened`);
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api]
  );

  const createWarehouse = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/warehouses/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(warehouseForm),
          },
          true
        );
        setWarehouseForm(initialWarehouseForm);
        await loadWarehouses();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadWarehouses, warehouseForm]
  );

  const createZone = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/warehouses/zones/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...zoneForm, warehouse: Number(zoneForm.warehouse) }),
          },
          true
        );
        setZoneForm(initialZoneForm);
        await loadZones();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadZones, zoneForm]
  );

  const createLocation = useCallback(
    async (event) => {
      event.preventDefault();
      const attributes = safeParseJson(locationForm.attributes_json);
      if (attributes === null) {
        setOperationsError("Location attributes must be valid JSON.");
        return;
      }
      try {
        await api(
          "/api/warehouses/locations/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...locationForm,
              zone: Number(locationForm.zone),
              capacity_limit: Number(locationForm.capacity_limit),
              attributes_json: attributes,
            }),
          },
          true
        );
        setLocationForm(initialLocationForm);
        await loadLocations();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadLocations, locationForm]
  );

  const createPartner = useCallback(
    async (event) => {
      event.preventDefault();
      const meta = safeParseJson(partnerForm.data_json);
      if (meta === null) {
        setOperationsError("Partner metadata must be valid JSON.");
        return;
      }
      if (partnerForm.effective_end && partnerForm.effective_end < partnerForm.effective_start) {
        setOperationsError("effective_end must be on or after effective_start.");
        return;
      }
      try {
        await api(
          "/api/warehouses/partners/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...partnerForm, data_json: meta }),
          },
          true
        );
        setPartnerForm(initialPartnerForm);
        await loadPartners();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadPartners, partnerForm]
  );

  const createInventoryPlan = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/inventory/plans/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(planForm),
          },
          true
        );
        setPlanForm(initialPlanForm);
        await loadPlans();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadPlans, planForm]
  );

  const createInventoryTask = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/inventory/tasks/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...taskForm,
              plan: Number(taskForm.plan),
              location: Number(taskForm.location),
              assignee: taskForm.assignee ? Number(taskForm.assignee) : null,
            }),
          },
          true
        );
        setTaskForm(initialTaskForm);
        await loadInventoryTasks();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadInventoryTasks, taskForm]
  );

  const createCountLine = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await api(
          "/api/inventory/lines/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...lineForm,
              task: Number(lineForm.task),
              book_quantity: Number(lineForm.book_quantity),
              physical_quantity: Number(lineForm.physical_quantity),
            }),
          },
          true
        );
        setLineForm(initialLineForm);
        await loadInventoryLines();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, lineForm, loadInventoryLines]
  );

  const createCorrectiveAction = useCallback(
    async (lineId) => {
      try {
        await api(
          `/api/inventory/lines/${lineId}/corrective-action/`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              cause: correctiveForm.cause,
              action: correctiveForm.action,
              owner: Number(correctiveForm.owner),
              due_date: correctiveForm.due_date,
              evidence: correctiveForm.evidence,
            }),
          },
          true
        );
        await loadInventoryLines();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, correctiveForm, loadInventoryLines]
  );

  const approveCorrectiveAction = useCallback(
    async (lineId) => {
      try {
        await api(
          `/api/inventory/lines/${lineId}/approve-action/`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ accountability_acknowledged: true }),
          },
          true
        );
        await loadInventoryLines();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadInventoryLines]
  );

  const acknowledgeCorrectiveAction = useCallback(
    async (lineId) => {
      try {
        await api(`/api/inventory/lines/${lineId}/acknowledge-action/`, { method: "POST" }, true);
        await loadInventoryLines();
      } catch (error) {
        setOperationsError(error.message);
      }
    },
    [api, loadInventoryLines]
  );

  const closeVariance = useCallback(
    async (lineId) => {
      try {
        await api(
          `/api/inventory/lines/${lineId}/close/`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review_notes: correctiveForm.review_notes }),
          },
          true
        );
        await loadInventoryLines();
        setStatus({ loading: false, message: "Variance closure complete", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, correctiveForm.review_notes, loadInventoryLines, setStatus]
  );

  const resetOperations = useCallback(() => {
    setWarehouses([]);
    setZones([]);
    setLocations([]);
    setPartners([]);
    setPlans([]);
    setInventoryTasks([]);
    setInventoryLines([]);
    setAlerts([]);
    setVerificationRequests([]);
    setVerificationComment("");
    setWarehouseForm(initialWarehouseForm);
    setZoneForm(initialZoneForm);
    setLocationForm(initialLocationForm);
    setPartnerForm(initialPartnerForm);
    setPlanForm(initialPlanForm);
    setTaskForm(initialTaskForm);
    setLineForm(initialLineForm);
    setCorrectiveForm(initialCorrectiveForm);
    setVerificationRequestForm(initialVerificationRequestForm);
    setDocumentForm(initialDocumentForm);
    setVerificationOpenResult("");
    setOperationsError("");
  }, []);

  return {
    warehouses,
    zones,
    locations,
    partners,
    plans,
    inventoryTasks,
    inventoryLines,
    alerts,
    verificationRequests,
    verificationComment,
    setVerificationComment,
    warehouseForm,
    setWarehouseForm,
    zoneForm,
    setZoneForm,
    locationForm,
    setLocationForm,
    partnerForm,
    setPartnerForm,
    planForm,
    setPlanForm,
    taskForm,
    setTaskForm,
    lineForm,
    setLineForm,
    correctiveForm,
    setCorrectiveForm,
    variancePreview,
    verificationRequestForm,
    setVerificationRequestForm,
    documentForm,
    setDocumentForm,
    verificationOpenResult,
    operationsError,
    setOperationsError,
    loadWarehouses,
    loadZones,
    loadLocations,
    loadPartners,
    loadPlans,
    loadInventoryTasks,
    loadInventoryLines,
    loadAlerts,
    loadVerificationRequests,
    handleVerificationReview,
    submitVerificationRequest,
    uploadVerificationDocument,
    openVerificationDocument,
    createWarehouse,
    createZone,
    createLocation,
    createPartner,
    createInventoryPlan,
    createInventoryTask,
    createCountLine,
    createCorrectiveAction,
    approveCorrectiveAction,
    acknowledgeCorrectiveAction,
    closeVariance,
    resetOperations,
  };
}

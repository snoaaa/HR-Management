import React, { useState, useEffect } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import Select from "@/components/form/Select";
import type { Department } from "./DepartmentsTable";
import type { Site } from "./SitesTable";
import type { CostCentre } from "./CostCentresTable";
import { useToast } from "@/context/ToastContext";

interface DepartmentModalProps {
  department: Department | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function DepartmentModal({ department, onClose, onSuccess }: DepartmentModalProps) {
  const [formData, setFormData] = useState({
    name: department?.name || "",
    code: department?.code || "",
    unit_type: department?.unit_type || "DEPARTMENT",
    parent: department?.parent || "",
    site: department?.site || "",
    cost_centre: department?.cost_centre || "",
    manager: department?.manager || "",
  });

  const [departments, setDepartments] = useState<Department[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [costCentres, setCostCentres] = useState<CostCentre[]>([]);
  const [users, setUsers] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    // Fetch dependencies
    api.get("organisation/departments/").then((res) => setDepartments(res.data));
    api.get("organisation/sites/").then((res) => setSites(res.data));
    api.get("organisation/cost-centres/").then((res) => setCostCentres(res.data));
    api.get("users/management/").then((res) => setUsers(res.data));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    let value = e.target.value;
    if (e.target.name === "code") {
      value = value.toUpperCase().replace(/\s+/g, ""); // Auto-format codes
    }
    setFormData({ ...formData, [e.target.name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Prepare data (convert empty strings to null for FKs)
    const payload = {
      ...formData,
      parent: formData.parent || null,
      site: formData.site || null,
      cost_centre: formData.cost_centre || null,
      manager: formData.manager || null,
    };

    try {
      if (department) {
        await api.put(`organisation/departments/${department.id}/`, payload);
        toast.success("Organisational Unit updated successfully");
      } else {
        await api.post("organisation/departments/", payload);
        toast.success("Organisational Unit created successfully");
      }
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "An error occurred while saving.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 transition-all duration-300 animate-in fade-in zoom-in-95">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-7 shadow-2xl ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-white/10">
        <div className="mb-6 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700/50">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {department ? "Edit Organisational Unit" : "Add Organisational Unit"}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label>Unit Name *</Label>
              <Input
                type="text"
                name="name"
                required
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Finance Department"
              />
            </div>

            <div>
              <Label>Unit Code *</Label>
              <Input
                type="text"
                name="code"
                required
                value={formData.code}
                onChange={handleChange}
                placeholder="e.g. FIN-01"
              />
            </div>

            <div>
              <Label>Unit Type *</Label>
              <Select
                name="unit_type"
                value={formData.unit_type}
                onChange={handleChange}
                options={[
                  { value: "COMPANY", label: "Company" },
                  { value: "SITE", label: "Site/Establishment" },
                  { value: "DIVISION", label: "Division" },
                  { value: "DEPARTMENT", label: "Department" },
                  { value: "SERVICE", label: "Service" },
                  { value: "TEAM", label: "Team" },
                ]}
              />
            </div>

            <div>
              <Label>Parent Unit</Label>
              <select
                name="parent"
                value={formData.parent}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- None (Top Level) --</option>
                {departments
                  .filter((d) => d.id !== department?.id) // Prevent self-referencing
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <Label>Site / Location</Label>
              <select
                name="site"
                value={formData.site}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Select Site --</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label>Cost Centre</Label>
              <select
                name="cost_centre"
                value={formData.cost_centre}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Select Cost Centre --</option>
                {costCentres.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <Label>Manager / Unit Head</Label>
              <select
                name="manager"
                value={formData.manager}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Select Manager --</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.first_name} {u.last_name} ({u.username})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button size="sm" variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save Unit"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

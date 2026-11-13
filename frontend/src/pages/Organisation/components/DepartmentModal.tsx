import React, { useState } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import Select from "@/components/form/Select";
import type { Department } from "./DepartmentsTable";
import { useToast } from "@/context/ToastContext";
import SearchSelect from "@/components/kit/SearchSelect";

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


  const [loading, setLoading] = useState(false);
  const toast = useToast();


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
                // @ts-expect-error select component typing mismatch
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
              <SearchSelect
                url="organisation/departments/"
                value={formData.parent || null}
                label={(d) => `${d.name} (${d.code})`}
                placeholder="None (top level) – search a unit…"
                onChange={(v) => setFormData((prev) => ({ ...prev, parent: v ?? "" }))}
              />
            </div>

            <div>
              <Label>Site / Location</Label>
              <SearchSelect
                url="organisation/sites/"
                value={formData.site || null}
                label={(s) => `${s.name} (${s.code})`}
                placeholder="Search a site…"
                onChange={(v) => setFormData((prev) => ({ ...prev, site: v ?? "" }))}
              />
            </div>

            <div>
              <Label>Cost Centre</Label>
              <SearchSelect
                url="organisation/cost-centres/"
                value={formData.cost_centre || null}
                label={(c) => `${c.name} (${c.code})`}
                placeholder="Search a cost centre…"
                onChange={(v) => setFormData((prev) => ({ ...prev, cost_centre: v ?? "" }))}
              />
            </div>

            <div className="sm:col-span-2">
              <Label>Manager / Unit Head</Label>
              <SearchSelect
                url="users/management/"
                value={formData.manager || null}
                label={(u) => `${u.first_name} ${u.last_name} (${u.username})`}
                placeholder="Search a manager…"
                onChange={(v) => setFormData((prev) => ({ ...prev, manager: v ?? "" }))}
              />
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

import React, { useState, useEffect } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import type { Position } from "./PositionsTable";
import type { Classification } from "./ClassificationsTable";
import type { Department } from "./DepartmentsTable";
import { useToast } from "@/context/ToastContext";

interface PositionModalProps {
  position: Position | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function PositionModal({ position, onClose, onSuccess }: PositionModalProps) {
  const [formData, setFormData] = useState({
    title: position?.title || "",
    code: position?.code || "",
    mission: position?.mission || "",
    required_skills: position?.required_skills || "",
    classification: position?.classification || "",
    reporting_position: position?.reporting_position || "",
    department: position?.department || "",
  });

  const [classifications, setClassifications] = useState<Classification[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);

  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    // Fetch dependencies
    api.get("organisation/classifications/").then((res) => setClassifications(res.data));
    api.get("organisation/departments/").then((res) => setDepartments(res.data));
    api.get("organisation/positions/").then((res) => setPositions(res.data));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    let value = e.target.value;
    if (e.target.name === "code") {
      value = value.toUpperCase().replace(/\s+/g, ""); // Intelligent: auto uppercase, no spaces
    }
    setFormData({ ...formData, [e.target.name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Prepare data (convert empty strings to null for FKs)
    const payload = {
      ...formData,
      classification: formData.classification || null,
      reporting_position: formData.reporting_position || null,
      department: formData.department || null,
    };

    try {
      if (position) {
        await api.put(`organisation/positions/${position.id}/`, payload);
        toast.success("Position updated successfully");
      } else {
        await api.post("organisation/positions/", payload);
        toast.success("Position created successfully");
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
            {position ? "Edit Position" : "Add Position"}
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
              <Label>Position Title *</Label>
              <Input
                type="text"
                name="title"
                required
                value={formData.title}
                onChange={handleChange}
                placeholder="e.g. Senior Developer"
              />
            </div>

            <div>
              <Label>Position Code *</Label>
              <Input
                type="text"
                name="code"
                required
                value={formData.code}
                onChange={handleChange}
                placeholder="e.g. POS-DEV-01"
              />
            </div>

            <div>
              <Label>Department / Unit</Label>
              <select
                name="department"
                value={formData.department}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Select Department --</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label>Reporting To</Label>
              <select
                name="reporting_position"
                value={formData.reporting_position}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Top Level --</option>
                {positions
                  .filter((p) => p.id !== position?.id)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} ({p.code})
                    </option>
                  ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <Label>Classification Grid</Label>
              <select
                name="classification"
                value={formData.classification}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              >
                <option value="">-- Select Classification --</option>
                {classifications.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.category} - Grade {c.grade} {c.echelon ? `(Echelon ${c.echelon})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <Label>Mission / Description</Label>
              <textarea
                name="mission"
                rows={2}
                value={formData.mission}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
                placeholder="Primary objective of this position"
              ></textarea>
            </div>

            <div className="sm:col-span-2">
              <Label>Required Skills</Label>
              <textarea
                name="required_skills"
                rows={2}
                value={formData.required_skills}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
                placeholder="Skills necessary for this position"
              ></textarea>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button size="sm" variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save Position"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

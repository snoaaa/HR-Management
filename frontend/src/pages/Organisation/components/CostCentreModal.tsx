import React, { useState } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import type { CostCentre } from "./CostCentresTable";
import { useToast } from "@/context/ToastContext";

interface CostCentreModalProps {
  costCentre: CostCentre | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CostCentreModal({ costCentre, onClose, onSuccess }: CostCentreModalProps) {
  const [formData, setFormData] = useState({
    name: costCentre?.name || "",
    code: costCentre?.code || "",
    description: costCentre?.description || "",
  });
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    let value = e.target.value;
    if (e.target.name === "code") {
      value = value.toUpperCase().replace(/\s+/g, ""); // Intelligent: auto uppercase, no spaces
    }
    setFormData({ ...formData, [e.target.name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (costCentre) {
        await api.put(`organisation/cost-centres/${costCentre.id}/`, formData);
        toast.success("Cost Centre updated successfully");
      } else {
        await api.post("organisation/cost-centres/", formData);
        toast.success("Cost Centre created successfully");
      }
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "An error occurred while saving the cost centre.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 transition-all duration-300 animate-in fade-in zoom-in-95">
      <div className="w-full max-w-md rounded-2xl bg-white p-7 shadow-2xl ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-white/10">
        <div className="mb-6 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700/50">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {costCentre ? "Edit Cost Centre" : "Add Cost Centre"}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Cost Centre Name *</Label>
            <Input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Marketing Budget"
            />
          </div>

          <div>
            <Label>Cost Centre Code *</Label>
            <Input
              type="text"
              name="code"
              required
              value={formData.code}
              onChange={handleChange}
              placeholder="e.g. CC-MKT-01"
            />
          </div>

          <div>
            <Label>Description</Label>
            <textarea
              name="description"
              rows={3}
              value={formData.description}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              placeholder="Details about this cost centre..."
            ></textarea>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button size="sm" variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={loading} className="relative transition-all duration-300 flex items-center justify-center gap-2">
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                "Save Cost Centre"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

import React, { useState } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import type { Classification } from "./ClassificationsTable";
import { useToast } from "@/context/ToastContext";

interface ClassificationModalProps {
  classification: Classification | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ClassificationModal({ classification, onClose, onSuccess }: ClassificationModalProps) {
  const [formData, setFormData] = useState({
    category: classification?.category || "",
    grade: classification?.grade || "",
    echelon: classification?.echelon || "",
    coefficient: classification?.coefficient || "",
  });
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value;
    if (e.target.name === "grade") {
      value = value.toUpperCase();
    } else if (e.target.name === "echelon") {
      value = value.replace(/[^0-9]/g, ""); // Only numbers
    } else if (e.target.name === "coefficient") {
      value = value.replace(/[^0-9.]/g, ""); // Only numbers and dots
      // Prevent multiple dots
      const parts = value.split('.');
      if (parts.length > 2) value = parts[0] + '.' + parts.slice(1).join('');
    }
    setFormData({ ...formData, [e.target.name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (classification) {
        await api.put(`organisation/classifications/${classification.id}/`, formData);
        toast.success("Classification Grid updated successfully");
      } else {
        await api.post("organisation/classifications/", formData);
        toast.success("Classification Grid created successfully");
      }
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "An error occurred while saving. Make sure Category+Grade+Echelon is unique.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 transition-all duration-300 animate-in fade-in zoom-in-95">
      <div className="w-full max-w-md rounded-2xl bg-white p-7 shadow-2xl ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-white/10">
        <div className="mb-6 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700/50">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {classification ? "Edit Classification" : "Add Classification"}
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
            <Label>Category *</Label>
            <Input
              type="text"
              name="category"
              required
              value={formData.category}
              onChange={handleChange}
              placeholder="e.g. Executive, Employee, Worker"
            />
          </div>

          <div>
            <Label>Grade *</Label>
            <Input
              type="text"
              name="grade"
              required
              value={formData.grade}
              onChange={handleChange}
              placeholder="e.g. A, B, 1, 2"
            />
          </div>

          <div>
            <Label>Echelon</Label>
            <Input
              type="text"
              name="echelon"
              value={formData.echelon}
              onChange={handleChange}
              placeholder="e.g. 1, 2, 3 (Optional)"
            />
          </div>

          <div>
            <Label>Coefficient</Label>
            <Input
              type="number"
              step="0.01"
              name="coefficient"
              value={formData.coefficient}
              onChange={handleChange}
              placeholder="e.g. 200.50"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button size="sm" variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

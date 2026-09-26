import React, { useState } from "react";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import type { Site } from "./SitesTable";
import { useToast } from "@/context/ToastContext";

interface SiteModalProps {
  site: Site | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function SiteModal({ site, onClose, onSuccess }: SiteModalProps) {
  const [formData, setFormData] = useState({
    name: site?.name || "",
    code: site?.code || "",
    address: site?.address || "",
  });
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (site) {
        await api.put(`organisation/sites/${site.id}/`, formData);
        toast.success("Site updated successfully");
      } else {
        await api.post("organisation/sites/", formData);
        toast.success("Site created successfully");
      }
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "An error occurred while saving the site.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 transition-all duration-300 animate-in fade-in zoom-in-95">
      <div className="w-full max-w-md rounded-2xl bg-white p-7 shadow-2xl ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-white/10">
        <div className="mb-6 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700/50">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {site ? "Edit Site" : "Add New Site"}
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
            <Label>Site Name *</Label>
            <Input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Paris Headquarters"
            />
          </div>

          <div>
            <Label>Site Code *</Label>
            <Input
              type="text"
              name="code"
              required
              value={formData.code}
              onChange={handleChange}
              placeholder="e.g. HQ-PARIS"
            />
          </div>

          <div>
            <Label>Address</Label>
            <textarea
              name="address"
              rows={3}
              value={formData.address}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
              placeholder="Full physical address"
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
                "Save Site"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

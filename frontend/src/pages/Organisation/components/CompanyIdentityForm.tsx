import React, { useState, useEffect } from "react";
import Button from "@/components/ui/button/Button";
import api from "@/api/axiosConfig";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import { useToast } from "@/context/ToastContext";

interface CompanyIdentity {
  id?: number;
  corporate_name: string;
  legal_form: string;
  registration_number: string;
  tax_id: string;
  social_insurance_number: string;
  address: string;
  legal_representative: string;
  logo?: string;
}

export default function CompanyIdentityForm() {
  const [formData, setFormData] = useState<CompanyIdentity>({
    corporate_name: "",
    legal_form: "",
    registration_number: "",
    tax_id: "",
    social_insurance_number: "",
    address: "",
    legal_representative: "",
  });
  const [loading, setLoading] = useState(false);
  const [initialFetch, setInitialFetch] = useState(true);
  const toast = useToast();

  useEffect(() => {
    fetchIdentity();
  }, []);

  const fetchIdentity = async () => {
    try {
      const response = await api.get("organisation/company-identity/");
      if (response.data && response.data.length > 0) {
        setFormData(response.data[0]);
      }
    } catch (error) {
      console.error("Failed to fetch company identity", error);
    } finally {
      setInitialFetch(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (formData.id) {
        await api.patch(`organisation/company-identity/${formData.id}/`, formData);
        toast.success("Company identity updated successfully.");
      } else {
        const response = await api.post("organisation/company-identity/", formData);
        setFormData(response.data);
        toast.success("Company identity created successfully.");
      }
    } catch (error) {
      toast.error("Failed to save company identity.");
    } finally {
      setLoading(false);
    }
  };

  if (initialFetch) return <div className="p-5 text-gray-500">Loading company data...</div>;

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-4xl">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label>Corporate Name *</Label>
          <Input 
            type="text" 
            name="corporate_name" 
            required 
            value={formData.corporate_name} 
            onChange={handleChange} 
            placeholder="E.g. Acme Corporation" 
          />
        </div>

        <div>
          <Label>Legal Form *</Label>
          <Input 
            type="text" 
            name="legal_form" 
            required 
            value={formData.legal_form} 
            onChange={handleChange} 
            placeholder="E.g. LLC, PLC, SA" 
          />
        </div>

        <div>
          <Label>Legal Representative *</Label>
          <Input 
            type="text" 
            name="legal_representative" 
            required 
            value={formData.legal_representative} 
            onChange={handleChange} 
            placeholder="Name of the CEO/Director" 
          />
        </div>

        <div>
          <Label>Registration Number</Label>
          <Input 
            type="text" 
            name="registration_number" 
            value={formData.registration_number || ""} 
            onChange={handleChange} 
            placeholder="Business Registration No." 
          />
        </div>

        <div>
          <Label>Tax Identification Number</Label>
          <Input 
            type="text" 
            name="tax_id" 
            value={formData.tax_id || ""} 
            onChange={handleChange} 
            placeholder="Tax ID" 
          />
        </div>

        <div>
          <Label>Social Insurance Employer Number</Label>
          <Input 
            type="text" 
            name="social_insurance_number" 
            value={formData.social_insurance_number || ""} 
            onChange={handleChange} 
            placeholder="e.g. CNPS Number" 
          />
        </div>

        <div className="sm:col-span-2">
          <Label>Headquarters Address *</Label>
          <textarea
            name="address"
            required
            rows={3}
            value={formData.address}
            onChange={handleChange}
            className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
            placeholder="Full physical address"
          ></textarea>
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <Button type="submit" disabled={loading} className="relative transition-all duration-300 flex items-center justify-center gap-2">
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Saving...
            </>
          ) : (
            "Save Identity Settings"
          )}
        </Button>
      </div>
    </form>
  );
}

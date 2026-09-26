import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import ComponentCard from "@/components/common/ComponentCard";
import Button from "@/components/ui/button/Button";
import { useEmployees } from "@/hooks/useEmployees";
import { Employee } from "@/types/employee";
import { CheckCircleIcon, ArrowRightIcon, ChevronLeftIcon } from "@/icons";

const STEPS = [
  "Identity & Contact",
  "Administrative",
  "Financial Details",
  "Review"
];

export default function EmployeeForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { createEmployee, updateEmployee, getEmployee } = useEmployees();
  
  const isEdit = Boolean(id);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<Partial<Employee>>({
    surname: "",
    given_names: "",
    date_of_birth: "",
    place_of_birth: "",
    sex: "M",
    nationality: "Cameroonian",
    marital_status: "SINGLE",
    identity_document_type: "National ID",
    identity_document_number: "",
    address: "",
    phone_number: "",
    emergency_contact_name: "",
    emergency_contact_number: "",
    status: "ACTIVE",
    contract_type: "PERMANENT",
    date_of_hire: new Date().toISOString().split('T')[0],
    method_of_payment: "TRANSFER",
  });

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      getEmployee(parseInt(id)).then(data => {
        setFormData(data);
        setLoading(false);
      }).catch(err => {
        setError("Failed to load employee data.");
        setLoading(false);
      });
    }
  }, [id, isEdit]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) setCurrentStep(prev => prev + 1);
  };

  const handlePrev = () => {
    if (currentStep > 0) setCurrentStep(prev => prev - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isEdit && id) {
        await updateEmployee(parseInt(id), formData);
      } else {
        await createEmployee(formData);
      }
      navigate("/employees");
    } catch (err: any) {
      setError("An error occurred while saving the employee.");
    } finally {
      setLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <div className="flex flex-col sm:flex-row items-center justify-between mb-8 relative">
      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 dark:bg-gray-800 z-0 hidden sm:block"></div>
      <div 
        className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-brand-500 z-0 hidden sm:block transition-all duration-500" 
        style={{ width: `${(currentStep / (STEPS.length - 1)) * 100}%` }}
      ></div>
      
      {STEPS.map((step, index) => {
        const isActive = index === currentStep;
        const isCompleted = index < currentStep;
        
        return (
          <div key={step} className="relative z-10 flex flex-col items-center gap-2 mb-4 sm:mb-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold shadow-md transition-all duration-300 ${
              isActive ? "bg-brand-500 text-white scale-110 ring-4 ring-brand-500/20" : 
              isCompleted ? "bg-success-500 text-white" : 
              "bg-white dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-700 text-gray-500"
            }`}>
              {isCompleted ? <CheckCircleIcon className="w-6 h-6 fill-current" /> : index + 1}
            </div>
            <span className={`text-xs font-semibold uppercase tracking-wider ${
              isActive ? "text-brand-500" : isCompleted ? "text-success-500" : "text-gray-400"
            }`}>
              {step}
            </span>
          </div>
        );
      })}
    </div>
  );

  return (
    <>
      <PageMeta title={`${isEdit ? 'Edit' : 'Add'} Employee | HRMS`} description="Employee creation wizard" />
      <PageBreadcrumb pageTitle={`${isEdit ? 'Edit' : 'Add New'} Employee`} />
      
      <div className="max-w-4xl mx-auto">
        <ComponentCard title="Employee Onboarding" desc="Follow the steps to complete the employee record.">
          {renderStepIndicator()}

          {error && (
            <div className="mb-6 p-4 bg-error-50 text-error-600 rounded-lg border border-error-200">
              {error}
            </div>
          )}

          <div className="min-h-[400px]">
            {/* Step 1: Identity & Contact */}
            {currentStep === 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-right-4 duration-500">
                <h3 className="col-span-1 md:col-span-2 text-lg font-semibold text-gray-800 dark:text-white border-b pb-2 mb-2">Civil Identity</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Surname</label>
                  <input required name="surname" value={formData.surname} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Given Names</label>
                  <input required name="given_names" value={formData.given_names} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date of Birth</label>
                  <input type="date" required name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sex</label>
                  <select name="sex" value={formData.sex} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all">
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                  </select>
                </div>
                
                <h3 className="col-span-1 md:col-span-2 text-lg font-semibold text-gray-800 dark:text-white border-b pb-2 mb-2 mt-4">Contact Details</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Phone Number</label>
                  <input required name="phone_number" value={formData.phone_number} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Personal Email</label>
                  <input type="email" name="personal_email" value={formData.personal_email || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div className="col-span-1 md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Address</label>
                  <textarea name="address" value={formData.address} onChange={handleChange} rows={2} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
              </div>
            )}

            {/* Step 2: Administrative */}
            {currentStep === 1 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-right-4 duration-500">
                <h3 className="col-span-1 md:col-span-2 text-lg font-semibold text-gray-800 dark:text-white border-b pb-2 mb-2">Administrative Situation</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date of Hire</label>
                  <input type="date" required name="date_of_hire" value={formData.date_of_hire} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Contract Type</label>
                  <select name="contract_type" value={formData.contract_type} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all">
                    <option value="PERMANENT">Permanent Contract</option>
                    <option value="FIXED_TERM">Fixed-Term Contract</option>
                    <option value="INTERNSHIP">Internship</option>
                    <option value="SERVICE">Service</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Department ID</label>
                  <input type="number" name="department" value={formData.department || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Position ID</label>
                  <input type="number" name="position" value={formData.position || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
              </div>
            )}

            {/* Step 3: Financial Details */}
            {currentStep === 2 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-right-4 duration-500">
                <h3 className="col-span-1 md:col-span-2 text-lg font-semibold text-gray-800 dark:text-white border-b pb-2 mb-2">Bank Details</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Payment Method</label>
                  <select name="method_of_payment" value={formData.method_of_payment} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all">
                    <option value="TRANSFER">Bank Transfer</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="CASH">Cash</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bank Name</label>
                  <input name="bank_name" value={formData.bank_name || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Account Number</label>
                  <input name="account_number" value={formData.account_number || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                
                <h3 className="col-span-1 md:col-span-2 text-lg font-semibold text-gray-800 dark:text-white border-b pb-2 mb-2 mt-4">Social & Tax Identifiers</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Social Insurance Number</label>
                  <input name="social_insurance_number" value={formData.social_insurance_number || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tax ID Number</label>
                  <input name="tax_identification_number" value={formData.tax_identification_number || ""} onChange={handleChange} className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-brand-500 outline-none transition-all" />
                </div>
              </div>
            )}

            {/* Step 4: Review */}
            {currentStep === 3 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                <div className="p-6 bg-brand-50 dark:bg-brand-900/20 rounded-xl border border-brand-100 dark:border-brand-800/30">
                  <h3 className="text-xl font-bold text-brand-800 dark:text-brand-300 mb-4">Review Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div><span className="text-sm text-gray-500">Full Name:</span> <p className="font-medium text-gray-900 dark:text-white">{formData.surname} {formData.given_names}</p></div>
                    <div><span className="text-sm text-gray-500">Hire Date:</span> <p className="font-medium text-gray-900 dark:text-white">{formData.date_of_hire}</p></div>
                    <div><span className="text-sm text-gray-500">Contract Type:</span> <p className="font-medium text-gray-900 dark:text-white">{formData.contract_type}</p></div>
                    <div><span className="text-sm text-gray-500">Payment Method:</span> <p className="font-medium text-gray-900 dark:text-white">{formData.method_of_payment}</p></div>
                  </div>
                </div>
                <p className="text-sm text-gray-500 text-center">Click Submit to finalize the employee creation. An auto-generated matriculation number will be assigned.</p>
              </div>
            )}
          </div>

          <div className="flex justify-between items-center mt-10 pt-6 border-t border-gray-100 dark:border-gray-800">
            <Button variant="outline" onClick={handlePrev} disabled={currentStep === 0 || loading} className="flex items-center gap-2 rounded-full px-6">
              <ChevronLeftIcon className="w-4 h-4 fill-current" /> Back
            </Button>
            
            {currentStep < STEPS.length - 1 ? (
              <Button onClick={handleNext} className="flex items-center gap-2 rounded-full px-6 shadow-md shadow-brand-500/20 hover:scale-105 transition-transform">
                Next <ArrowRightIcon className="w-4 h-4 fill-current" />
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={loading} className="flex items-center gap-2 rounded-full px-8 shadow-lg shadow-brand-500/30 hover:scale-105 transition-transform">
                {loading ? "Saving..." : "Submit"} <CheckCircleIcon className="w-4 h-4 fill-current" />
              </Button>
            )}
          </div>
        </ComponentCard>
      </div>
    </>
  );
}

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import ComponentCard from "@/components/common/ComponentCard";
import Button from "@/components/ui/button/Button";
import Badge from "@/components/ui/badge/Badge";
import { useEmployees } from "@/hooks/useEmployees";
import type { Employee, EmployeeHistory } from "@/types/employee";
import { UserIcon, EditIcon, CheckCircleIcon, TimeIcon, DocsIcon, GroupIcon, DollarIcon } from "@/icons";

export default function EmployeeProfile() {
  const { id } = useParams();
  const { getEmployee } = useEmployees();
  
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [history, setHistory] = useState<EmployeeHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    if (id) {
      setLoading(true);
      getEmployee(parseInt(id)).then(data => {
        setEmployee(data);
        if (data.history) setHistory(data.history);
        setLoading(false);
      });
    }
  }, [id]);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-500"></div></div>;
  }

  if (!employee) return <div>Employee not found</div>;

  const TABS = [
    { id: "overview", label: "Overview", icon: <UserIcon className="w-5 h-5 fill-current" /> },
    { id: "financial", label: "Financial & Tax", icon: <DollarIcon className="w-5 h-5 fill-current" /> },
    { id: "dependents", label: "Dependents", icon: <GroupIcon className="w-5 h-5 fill-current" /> },
    { id: "documents", label: "Documents", icon: <DocsIcon className="w-5 h-5 fill-current" /> },
    { id: "audit", label: "Audit Trail", icon: <TimeIcon className="w-5 h-5 fill-current" /> }
  ];

  return (
    <>
      <PageMeta title="Employee Profile | HRMS" description="Detailed employee record" />
      <PageBreadcrumb pageTitle="Employee Profile" />
      
      {/* Profile Header */}
      <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-3xl shadow-sm border border-gray-200 dark:border-gray-800 p-8 mb-6 overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-r from-brand-500 to-blue-500 z-0"></div>
        <div className="relative z-10 flex flex-col md:flex-row gap-8 items-end pt-12">
          <div className="w-32 h-32 rounded-2xl bg-white dark:bg-gray-800 p-2 shadow-xl shrink-0">
            <div className="w-full h-full rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-4xl font-bold text-brand-500">
              {employee.surname.charAt(0)}{employee.given_names.charAt(0)}
            </div>
          </div>
          
          <div className="flex-1 pb-2">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{employee.surname} {employee.given_names}</h1>
              <Badge color={employee.status === 'ACTIVE' ? 'success' : 'warning'} size="sm">{employee.status}</Badge>
            </div>
            <p className="text-gray-500 dark:text-gray-400 font-medium mb-1">
              ID: <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-gray-700 dark:text-gray-300">{employee.matriculation_number}</span>
            </p>
            <p className="text-gray-500 dark:text-gray-400">{employee.contract_type.replace('_', ' ')} • Hired on {new Date(employee.date_of_hire).toLocaleDateString()}</p>
          </div>
          
          <div className="pb-2">
            <Link to={`/employees/edit/${employee.id}`}>
              <Button size="sm" variant="outline" className="flex items-center gap-2">
                <EditIcon className="w-4 h-4 fill-current" />
                Edit Profile
              </Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Navigation Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-200 dark:border-gray-800 sticky top-24">
            <nav className="flex flex-col gap-2">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 w-full text-left px-4 py-3 rounded-xl transition-all font-medium text-sm ${
                    activeTab === tab.id 
                      ? "bg-brand-500 text-white shadow-md shadow-brand-500/20 translate-x-1" 
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white"
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="lg:col-span-3 space-y-6">
          {activeTab === "overview" && (
            <ComponentCard title="Civil Identity & Contact" desc="Basic employee details">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Date of Birth</h4>
                  <p className="font-medium text-gray-900 dark:text-white">{employee.date_of_birth} ({employee.place_of_birth})</p>
                </div>
                <div>
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Nationality</h4>
                  <p className="font-medium text-gray-900 dark:text-white">{employee.nationality}</p>
                </div>
                <div>
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Contact</h4>
                  <p className="font-medium text-gray-900 dark:text-white">{employee.phone_number}</p>
                  {employee.phone_number_2 && <p className="font-medium text-gray-900 dark:text-white">{employee.phone_number_2}</p>}
                  {employee.phone_number_3 && <p className="font-medium text-gray-900 dark:text-white">{employee.phone_number_3}</p>}
                  <p className="text-sm text-gray-500 mt-1">{employee.personal_email}</p>
                </div>
                <div>
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Address</h4>
                  <p className="font-medium text-gray-900 dark:text-white">{employee.address}</p>
                </div>
                <div className="md:col-span-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-3">Emergency Contacts</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      <p className="text-xs text-brand-500 font-semibold mb-1">Primary</p>
                      <p className="font-medium text-gray-900 dark:text-white">{employee.emergency_contact_name}</p>
                      {employee.emergency_contact_relationship && <p className="text-xs text-gray-500 mb-1">{employee.emergency_contact_relationship}</p>}
                      <p className="text-sm text-gray-600 dark:text-gray-400">{employee.emergency_contact_number}</p>
                    </div>
                    {employee.emergency_contact_name_2 && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <p className="text-xs text-gray-500 font-semibold mb-1">Secondary</p>
                        <p className="font-medium text-gray-900 dark:text-white">{employee.emergency_contact_name_2}</p>
                        {employee.emergency_contact_relationship_2 && <p className="text-xs text-gray-500 mb-1">{employee.emergency_contact_relationship_2}</p>}
                        <p className="text-sm text-gray-600 dark:text-gray-400">{employee.emergency_contact_number_2}</p>
                      </div>
                    )}
                    {employee.emergency_contact_name_3 && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <p className="text-xs text-gray-500 font-semibold mb-1">Tertiary</p>
                        <p className="font-medium text-gray-900 dark:text-white">{employee.emergency_contact_name_3}</p>
                        {employee.emergency_contact_relationship_3 && <p className="text-xs text-gray-500 mb-1">{employee.emergency_contact_relationship_3}</p>}
                        <p className="text-sm text-gray-600 dark:text-gray-400">{employee.emergency_contact_number_3}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </ComponentCard>
          )}

          {activeTab === "financial" && (
            <ComponentCard title="Financial & Tax Details" desc="Restricted access bank and tax information">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-2">Payment Method</h4>
                  <div className="flex items-center gap-2">
                    <CheckCircleIcon className="w-5 h-5 text-success-500 fill-current" />
                    <span className="font-semibold text-gray-900 dark:text-white">{employee.method_of_payment}</span>
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Bank Name</h4>
                  <p className="font-medium text-gray-900 dark:text-white">{employee.bank_name || 'N/A'}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Account Number</h4>
                  <p className="font-mono font-medium text-gray-900 dark:text-white">{employee.account_number || 'N/A'}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-1">Social Insurance / Tax ID</h4>
                  <p className="font-mono text-sm text-gray-900 dark:text-white mb-1">NISS: {employee.social_insurance_number || 'N/A'}</p>
                  <p className="font-mono text-sm text-gray-900 dark:text-white">TIN: {employee.tax_identification_number || 'N/A'}</p>
                </div>
              </div>
            </ComponentCard>
          )}

          {activeTab === "audit" && (
            <ComponentCard title="Audit Trail" desc="Chronological history of all modifications (BN-21)">
              {history.length === 0 ? (
                <p className="text-gray-500">No modifications recorded yet.</p>
              ) : (
                <div className="relative border-l border-gray-200 dark:border-gray-800 ml-3 space-y-6 pb-4">
                  {history.map((record, index) => (
                    <div key={index} className="relative pl-6">
                      <span className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full bg-brand-500 ring-4 ring-brand-50 dark:ring-gray-900"></span>
                      <div className="text-sm text-gray-500 mb-1">
                        {new Date(record.modification_date).toLocaleString()} • by User ID {record.author}
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-100 dark:border-gray-800 inline-block">
                        <span className="font-medium text-gray-900 dark:text-white">{record.field_name}:</span> 
                        <span className="text-error-500 line-through mx-2">{record.previous_value}</span>
                        <span className="text-success-500 font-medium">{record.new_value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ComponentCard>
          )}
          
          {(activeTab === "dependents" || activeTab === "documents") && (
            <ComponentCard title="Coming Soon" desc="This section is currently under development.">
              <div className="flex flex-col items-center justify-center py-12">
                <TimeIcon className="w-16 h-16 text-gray-300 mb-4 fill-current" />
                <p className="text-gray-500">These lists will be fully implemented in the next sprint.</p>
              </div>
            </ComponentCard>
          )}
        </div>
      </div>
    </>
  );
}

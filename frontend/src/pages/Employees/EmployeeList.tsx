import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import Button from "@/components/ui/button/Button";
import { PlusIcon, SearchIcon, DownloadIcon, UserIcon, EyeIcon, EditIcon, TrashBinIcon } from "@/icons";
import { useEmployees } from "@/hooks/useEmployees";

import Badge from "@/components/ui/badge/Badge";

export default function EmployeeList() {
  const navigate = useNavigate();
  const { employees, loading, fetchEmployees, archiveEmployee } = useEmployees();
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterStatus(e.target.value);
  };

  const filteredEmployees = employees.filter((emp) => {
    const matchesSearch = 
      emp.surname.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.given_names.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.matriculation_number?.toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesStatus = filterStatus ? emp.status === filterStatus : true;
    
    return matchesSearch && matchesStatus;
  });

  const exportCSV = () => {
    if (filteredEmployees.length === 0) return;
    
    const headers = ["Matriculation", "Surname", "Given Names", "Status", "Contract Type", "Date of Hire"];
    const csvData = filteredEmployees.map(emp => [
      emp.matriculation_number || "",
      emp.surname,
      emp.given_names,
      emp.status,
      emp.contract_type,
      emp.date_of_hire
    ].join(","));
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...csvData].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "employees_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "ACTIVE": return "success";
      case "INACTIVE": return "warning";
      case "ARCHIVED": return "error";
      default: return "primary";
    }
  };

  return (
    <>
      <PageMeta title="Employee Directory | HRMS" description="Manage all employee records" />
      <PageBreadcrumb pageTitle="Employee Directory" />
      
      <div className="space-y-6">
        {/* Header and Actions */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-white/50 dark:bg-white/5 backdrop-blur-md p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 transition-all duration-300">
          <div className="flex-1 w-full flex flex-col sm:flex-row gap-4 items-center">
            <div className="relative w-full sm:w-80">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                <SearchIcon className="w-5 h-5 fill-current" />
              </span>
              <input
                type="text"
                placeholder="Search by name, ID..."
                value={searchTerm}
                onChange={handleSearch}
                className="w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full pl-12 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition-shadow shadow-sm"
              />
            </div>
            
            <select
              value={filterStatus}
              onChange={handleFilter}
              className="w-full sm:w-48 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 shadow-sm"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>
          
          <div className="flex gap-3 w-full sm:w-auto">
            <Button size="sm" variant="outline" onClick={exportCSV} className="flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-full px-6 transition-transform hover:scale-105">
              <DownloadIcon className="w-4 h-4 fill-current" />
              Export
            </Button>
            <Button size="sm" onClick={() => navigate('/employees/new')} className="flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-full px-6 transition-transform hover:scale-105 shadow-brand-500/30 shadow-lg">
              <PlusIcon className="w-4 h-4 fill-current" />
              Add Employee
            </Button>
          </div>
        </div>

        {/* Directory Grid/Table */}
        <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden transition-all duration-300">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-500 dark:text-gray-400">
              <thead className="bg-gray-50/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 font-semibold uppercase text-xs">
                <tr>
                  <th className="px-6 py-4 rounded-tl-2xl">Employee</th>
                  <th className="px-6 py-4">ID</th>
                  <th className="px-6 py-4">Contact</th>
                  <th className="px-6 py-4">Hire Date</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right rounded-tr-2xl">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800/50">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-brand-500 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
                      <p className="mt-4 text-gray-500">Loading employees...</p>
                    </td>
                  </tr>
                ) : filteredEmployees.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <div className="h-16 w-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                          <UserIcon className="w-8 h-8 text-gray-400" />
                        </div>
                        <p className="text-gray-500 dark:text-gray-400">No employees found matching your criteria.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredEmployees.map((emp) => (
                    <tr key={emp.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-brand-500 to-blue-400 flex items-center justify-center text-white font-bold shadow-md shadow-brand-500/20 group-hover:scale-110 transition-transform">
                            {emp.surname.charAt(0)}{emp.given_names.charAt(0)}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-gray-900 dark:text-white">{emp.surname} {emp.given_names}</p>
                            <p className="text-xs text-gray-500">{emp.contract_type.replace('_', ' ')}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="font-mono text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-gray-600 dark:text-gray-300">
                          {emp.matriculation_number}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="text-xs text-gray-900 dark:text-white">{emp.phone_number}</p>
                        <p className="text-xs text-gray-500">{emp.professional_email || emp.personal_email || "N/A"}</p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {new Date(emp.date_of_hire).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge color={getStatusBadgeColor(emp.status)} size="sm">
                          {emp.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => navigate(`/employees/${emp.id}`)} className="p-2 text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-full transition-colors">
                            <EyeIcon className="w-4 h-4 fill-current" />
                          </button>
                          <button onClick={() => navigate(`/employees/edit/${emp.id}`)} className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-full transition-colors">
                            <EditIcon className="w-4 h-4 fill-current" />
                          </button>
                          {emp.status !== 'ARCHIVED' && (
                            <button 
                              onClick={() => {
                                if (window.confirm("Are you sure you want to archive this employee?")) {
                                  archiveEmployee(emp.id!);
                                }
                              }}
                              className="p-2 text-gray-400 hover:text-error-500 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-full transition-colors"
                            >
                              <TrashBinIcon className="w-4 h-4 fill-current" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

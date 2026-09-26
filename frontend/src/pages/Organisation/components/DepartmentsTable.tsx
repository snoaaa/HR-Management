import React, { useState, useEffect } from "react";
import api from "@/api/axiosConfig";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Button from "@/components/ui/button/Button";
import DepartmentModal from "./DepartmentModal";
import { useToast } from "@/context/ToastContext";

export interface Department {
  id: number;
  name: string;
  code: string;
  unit_type: string;
  parent: number | null;
  parent_name?: string;
  site: number | null;
  site_name?: string;
  cost_centre: number | null;
  cost_centre_name?: string;
  manager: number | null;
  manager_name?: string;
}

export default function DepartmentsTable() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null);
  const toast = useToast();

  const fetchDepartments = async () => {
    try {
      setLoading(true);
      const response = await api.get("organisation/departments/");
      setDepartments(response.data);
    } catch (error) {
      console.error("Failed to fetch departments:", error);
      toast.error("Failed to fetch departments");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDepartments();
  }, []);

  const openAddModal = () => {
    setSelectedDepartment(null);
    setIsModalOpen(true);
  };

  const openEditModal = (dept: Department) => {
    setSelectedDepartment(dept);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this unit? All child units must be re-assigned or deleted first.")) {
      try {
        await api.delete(`organisation/departments/${id}/`);
        toast.success("Organisational Unit deleted successfully");
        fetchDepartments();
      } catch (error) {
        console.error("Failed to delete unit:", error);
        toast.error("Could not delete. It may have child units or attached employees.");
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openAddModal}>+ Add Organisational Unit</Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Unit Name / Code
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Type
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Parent Unit
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Manager
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-end text-theme-xs dark:text-gray-400">
                  Actions
                </TableCell>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-4 text-center text-sm text-gray-500">
                    Loading structure...
                  </TableCell>
                </TableRow>
              ) : departments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-4 text-center text-sm text-gray-500">
                    No organisational units found. Start by adding the Company root node.
                  </TableCell>
                </TableRow>
              ) : (
                departments.map((dept) => (
                  <TableRow key={dept.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                    <TableCell className="px-5 py-4 sm:px-6 text-start">
                      <div className="text-sm font-semibold text-gray-800 dark:text-white/90">
                        {dept.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {dept.code} {dept.site_name ? `• ${dept.site_name}` : ""}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-start">
                      <span className="inline-flex items-center rounded-full bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700 dark:bg-brand-500/15 dark:text-brand-400">
                        {dept.unit_type}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-800 text-start text-theme-sm dark:text-white/90">
                      {dept.parent_name || <span className="text-gray-400 italic">None (Root)</span>}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-800 text-start text-theme-sm dark:text-white/90">
                      {dept.manager_name || "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-end text-theme-sm dark:text-gray-400">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(dept)}
                          className="text-brand-500 hover:text-brand-600"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(dept.id)}
                          className="text-error-500 hover:text-error-600"
                        >
                          Delete
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {isModalOpen && (
        <DepartmentModal
          department={selectedDepartment}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchDepartments();
          }}
        />
      )}
    </div>
  );
}

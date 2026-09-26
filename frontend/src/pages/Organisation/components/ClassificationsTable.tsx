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
import ClassificationModal from "./ClassificationModal";
import { useToast } from "@/context/ToastContext";

export interface Classification {
  id: number;
  category: string;
  grade: string;
  echelon: string;
  coefficient: string;
}

export default function ClassificationsTable() {
  const [classifications, setClassifications] = useState<Classification[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedClassification, setSelectedClassification] = useState<Classification | null>(null);
  const toast = useToast();

  const fetchClassifications = async () => {
    try {
      setLoading(true);
      const response = await api.get("organisation/classifications/");
      setClassifications(response.data);
    } catch (error) {
      console.error("Failed to fetch classifications:", error);
      toast.error("Failed to fetch classifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClassifications();
  }, []);

  const openAddModal = () => {
    setSelectedClassification(null);
    setIsModalOpen(true);
  };

  const openEditModal = (c: Classification) => {
    setSelectedClassification(c);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this classification?")) {
      try {
        await api.delete(`organisation/classifications/${id}/`);
        toast.success("Classification Grid deleted successfully");
        fetchClassifications();
      } catch (error) {
        console.error("Failed to delete classification:", error);
        toast.error("Could not delete. It may be attached to positions.");
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openAddModal}>+ Add Classification Grid</Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Category
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Grade
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Echelon
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Coefficient
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
                    Loading classification grid...
                  </TableCell>
                </TableRow>
              ) : classifications.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-4 text-center text-sm text-gray-500">
                    No classification rows found.
                  </TableCell>
                </TableRow>
              ) : (
                classifications.map((c) => (
                  <TableRow key={c.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                    <TableCell className="px-5 py-4 sm:px-6 text-start">
                      <div className="text-sm font-semibold text-gray-800 dark:text-white/90">
                        {c.category}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-800 text-start text-theme-sm dark:text-white/90">
                      {c.grade}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-800 text-start text-theme-sm dark:text-white/90">
                      {c.echelon || "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      {c.coefficient || "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-end text-theme-sm dark:text-gray-400">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(c)}
                          className="text-brand-500 hover:text-brand-600"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(c.id)}
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
        <ClassificationModal
          classification={selectedClassification}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchClassifications();
          }}
        />
      )}
    </div>
  );
}

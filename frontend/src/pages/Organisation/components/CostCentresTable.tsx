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
import CostCentreModal from "./CostCentreModal";
import { useToast } from "@/context/ToastContext";

export interface CostCentre {
  id: number;
  name: string;
  code: string;
  description: string;
}

export default function CostCentresTable() {
  const [costCentres, setCostCentres] = useState<CostCentre[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCostCentre, setSelectedCostCentre] = useState<CostCentre | null>(null);
  const toast = useToast();

  const fetchCostCentres = async () => {
    try {
      setLoading(true);
      const response = await api.get("organisation/cost-centres/");
      setCostCentres(response.data);
    } catch (error) {
      console.error("Failed to fetch cost centres:", error);
      toast.error("Failed to fetch cost centres");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCostCentres();
  }, []);

  const openAddModal = () => {
    setSelectedCostCentre(null);
    setIsModalOpen(true);
  };

  const openEditModal = (cc: CostCentre) => {
    setSelectedCostCentre(cc);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this cost centre?")) {
      try {
        await api.delete(`organisation/cost-centres/${id}/`);
        toast.success("Cost Centre deleted successfully");
        fetchCostCentres();
      } catch (error) {
        console.error("Failed to delete cost centre:", error);
        toast.error("Could not delete cost centre. It may be attached to departments.");
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openAddModal}>+ Add Cost Centre</Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Code
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Name
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Description
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-end text-theme-xs dark:text-gray-400">
                  Actions
                </TableCell>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-4 text-center text-sm text-gray-500">
                    Loading cost centres...
                  </TableCell>
                </TableRow>
              ) : costCentres.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-4 text-center text-sm text-gray-500">
                    No cost centres found.
                  </TableCell>
                </TableRow>
              ) : (
                costCentres.map((cc) => (
                  <TableRow key={cc.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                    <TableCell className="px-5 py-4 sm:px-6 text-start">
                      <div className="text-sm font-semibold text-gray-800 dark:text-white/90">
                        {cc.code}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-800 text-start text-theme-sm dark:text-white/90">
                      {cc.name}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400 max-w-[200px] truncate">
                      {cc.description || "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-end text-theme-sm dark:text-gray-400">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(cc)}
                          className="text-brand-500 hover:text-brand-600"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(cc.id)}
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
        <CostCentreModal
          costCentre={selectedCostCentre}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchCostCentres();
          }}
        />
      )}
    </div>
  );
}

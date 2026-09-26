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
import SiteModal from "./SiteModal";
import { useToast } from "@/context/ToastContext";

export interface Site {
  id: number;
  name: string;
  code: string;
  address: string;
}

export default function SitesTable() {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const toast = useToast();

  const fetchSites = async () => {
    try {
      setLoading(true);
      const response = await api.get("organisation/sites/");
      setSites(response.data);
    } catch (error) {
      console.error("Failed to fetch sites:", error);
      toast.error("Failed to fetch sites");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSites();
  }, []);

  const openAddModal = () => {
    setSelectedSite(null);
    setIsModalOpen(true);
  };

  const openEditModal = (site: Site) => {
    setSelectedSite(site);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this site?")) {
      try {
        await api.delete(`organisation/sites/${id}/`);
        toast.success("Site deleted successfully");
        fetchSites();
      } catch (error) {
        console.error("Failed to delete site:", error);
        toast.error("Could not delete site. It may be in use.");
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openAddModal}>+ Add New Site</Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Site Name
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Site Code
                </TableCell>
                <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">
                  Address
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
                    Loading sites...
                  </TableCell>
                </TableRow>
              ) : sites.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-4 text-center text-sm text-gray-500">
                    No sites found. Add one to get started.
                  </TableCell>
                </TableRow>
              ) : (
                sites.map((site) => (
                  <TableRow key={site.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                    <TableCell className="px-5 py-4 sm:px-6 text-start">
                      <div className="text-sm font-medium text-gray-800 dark:text-white/90">
                        {site.name}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      {site.code}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      {site.address || "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-end text-theme-sm dark:text-gray-400">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(site)}
                          className="text-brand-500 hover:text-brand-600"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(site.id)}
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
        <SiteModal
          site={selectedSite}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchSites();
          }}
        />
      )}
    </div>
  );
}

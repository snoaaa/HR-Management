import { useEffect, useState } from "react";
import ComponentCard from "@/components/common/ComponentCard";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api from "@/api/axiosConfig";
import Button from "@/components/ui/button/Button";

interface AuditLog {
  id: number;
  username: string;
  action: string;
  module: string;
  ip_address: string;
  timestamp: string;
}

export default function AuditTrail() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await api.get("audit-logs/");
      setLogs(response.data);
      setError(null);
    } catch (err) {
      setError("Failed to load audit logs. Check your permissions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleExport = () => {
    // Generate CSV
    const csvRows = [];
    const headers = ["Timestamp", "User", "Action", "Module", "IP Address"];
    csvRows.push(headers.join(","));

    for (const row of logs) {
      const values = [
        new Date(row.timestamp).toLocaleString().replace(/,/g, ''),
        row.username || 'System',
        `"${row.action}"`,
        row.module,
        row.ip_address || 'N/A'
      ];
      csvRows.push(values.join(","));
    }

    const csvData = csvRows.join("\n");
    const blob = new Blob([csvData], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.setAttribute("hidden", "");
    a.setAttribute("href", url);
    a.setAttribute("download", `audit_logs_${new Date().toISOString()}.csv`);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <>
      <PageMeta
        title="Audit Trail | HRMS Dashboard"
        description="Consult and export the unalterable system audit trail."
      />
      <PageBreadcrumb pageTitle="System Audit Trail" />

      <div className="space-y-6">
        <ComponentCard title="Audit Logs" desc="Unalterable record of all sensitive operations in the system.">
          <div className="mb-4 flex justify-end">
            <Button size="sm" onClick={handleExport} disabled={logs.length === 0}>
              Export to CSV
            </Button>
          </div>

          {loading ? (
            <div className="p-5 text-center text-gray-500">Loading audit trail...</div>
          ) : error ? (
            <div className="p-5 text-center text-error-500">{error}</div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/5 dark:bg-white/3">
              <div className="max-w-full overflow-x-auto max-h-[600px] overflow-y-auto">
                <Table>
                  <TableHeader className="border-b border-gray-100 dark:border-white/5 sticky top-0 bg-white dark:bg-gray-900 z-10">
                    <TableRow>
                      <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                        Date & Time
                      </TableCell>
                      <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                        User
                      </TableCell>
                      <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                        Module
                      </TableCell>
                      <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                        Action
                      </TableCell>
                      <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                        IP Address
                      </TableCell>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                    {logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="px-5 py-4 text-start whitespace-nowrap text-theme-sm text-gray-500 dark:text-gray-400">
                          {new Date(log.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-start whitespace-nowrap text-theme-sm text-gray-800 dark:text-white/90 font-medium">
                          {log.username || "System/Anonymous"}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-start whitespace-nowrap text-theme-sm text-gray-500 dark:text-gray-400">
                          {log.module}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-start text-theme-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                          {log.action}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-start whitespace-nowrap text-theme-sm text-gray-500 dark:text-gray-400">
                          {log.ip_address || "N/A"}
                        </TableCell>
                      </TableRow>
                    ))}
                    {logs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="px-5 py-4 text-center text-gray-500">
                          No audit logs found.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </ComponentCard>
      </div>
    </>
  );
}

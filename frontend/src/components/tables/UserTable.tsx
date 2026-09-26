import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import api from "@/api/axiosConfig";
import { useAuth } from "@/context/AuthContext";

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role: string;
  requires_password_change: boolean;
}

interface UserTableProps {
  refreshTrigger?: number;
  onEditUser?: (user: User) => void;
}

export default function UserTable({ refreshTrigger = 0, onEditUser }: UserTableProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user: currentUser } = useAuth();

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get("users/management/");
      setUsers(response.data);
      setError(null);
    } catch (err: any) {
      setError("Failed to load users. Are you an administrator?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [refreshTrigger]);

  const toggleStatus = async (userId: number, currentStatus: boolean) => {
    try {
      await api.patch(`users/management/${userId}/`, {
        is_active: !currentStatus
      });
      // Optimistic update
      setUsers(users.map(u => u.id === userId ? { ...u, is_active: !currentStatus } : u));
    } catch (err) {
      alert("Failed to update user status.");
    }
  };

  if (loading) {
    return <div className="p-5 text-center text-gray-500">Loading users...</div>;
  }

  if (error) {
    return <div className="p-5 text-center text-error-500">{error}</div>;
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/5 dark:bg-white/3">
      <div className="max-w-full overflow-x-auto">
        <Table>
          <TableHeader className="border-b border-gray-100 dark:border-white/5">
            <TableRow>
              <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                User
              </TableCell>
              <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                Role
              </TableCell>
              <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                Status
              </TableCell>
              <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                Security
              </TableCell>
              <TableCell isHeader className="px-5 py-3 text-start text-theme-xs font-medium whitespace-nowrap text-gray-500 dark:text-gray-400">
                Actions
              </TableCell>
            </TableRow>
          </TableHeader>

          <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="px-5 py-4 text-start whitespace-nowrap sm:px-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-brand-100 text-brand-600 font-bold dark:bg-brand-900 dark:text-brand-300">
                      {u.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <span className="block text-theme-sm font-medium text-gray-800 dark:text-white/90">
                        {u.first_name} {u.last_name} ({u.username})
                      </span>
                      <span className="block text-theme-xs text-gray-500 dark:text-gray-400">
                        {u.email}
                      </span>
                    </div>
                  </div>
                </TableCell>

                <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                  {u.role.replace(/_/g, ' ')}
                </TableCell>

                <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                  <Badge
                    size="sm"
                    color={u.is_active ? "success" : "error"}
                  >
                    {u.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>

                <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                  {u.requires_password_change ? (
                    <Badge size="sm" color="warning">Must Change Pwd</Badge>
                  ) : (
                    <Badge size="sm" color="success">Secure</Badge>
                  )}
                </TableCell>

                <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                  <div className="flex gap-2">
                    {onEditUser && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onEditUser(u)}
                      >
                        Edit
                      </Button>
                    )}
                    {currentUser?.username !== u.username && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggleStatus(u.id, u.is_active)}
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from "react";
import Button from "@/components/ui/button/Button";
import { CloseIcon } from "@/icons";

interface UserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  user?: any;
}

export default function UserModal({ isOpen, onClose, onSubmit, user }: UserModalProps) {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    role: "EMPLOYEE",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username,
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        role: user.role,
      });
    } else {
      setFormData({
        username: "",
        email: "",
        first_name: "",
        last_name: "",
        role: "EMPLOYEE",
      });
    }
  }, [user, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-99999 flex items-center justify-center bg-gray-900/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            {user ? "Edit User Role" : "Create New User"}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <CloseIcon className="h-5 w-5 fill-current" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!user && (
            <>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
                <input
                  type="text"
                  name="username"
                  required
                  value={formData.username}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
                <input
                  type="email"
                  name="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">First Name</label>
                  <input
                    type="text"
                    name="first_name"
                    required
                    value={formData.first_name}
                    onChange={handleChange}
                    className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:text-white"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Last Name</label>
                  <input
                    type="text"
                    name="last_name"
                    required
                    value={formData.last_name}
                    onChange={handleChange}
                    className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:text-white"
                  />
                </div>
              </div>
            </>
          )}

          {user && (
            <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-800 dark:text-white">{user.first_name} {user.last_name}</p>
              <p className="text-xs text-gray-500">{user.email}</p>
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">System Role</label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:text-white"
            >
              <option value="EMPLOYEE">Employee</option>
              <option value="HEAD_OF_DEPARTMENT">Head of Department</option>
              <option value="ACCOUNTANT">Accountant</option>
              <option value="PAYROLL_OFFICER">Payroll Officer</option>
              <option value="HR_OFFICER">HR Officer</option>
              <option value="HR_MANAGER">HR Manager</option>
              <option value="SYSTEM_ADMINISTRATOR">System Administrator</option>
            </select>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save User"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

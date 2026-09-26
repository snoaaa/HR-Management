import { useState } from "react";
import ComponentCard from "@/components/common/ComponentCard";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import UserTable from "@/components/tables/UserTable";
import Button from "@/components/ui/button/Button";
import { PlusIcon } from "@/icons";
import UserModal from "@/components/users/UserModal";
import api from "@/api/axiosConfig";

export default function UserManagement() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleCreateUser = () => {
    setSelectedUser(null);
    setIsModalOpen(true);
  };

  const handleEditUser = (user: any) => {
    setSelectedUser(user);
    setIsModalOpen(true);
  };

  const handleSubmit = async (formData: any) => {
    if (selectedUser) {
      await api.patch(`users/management/${selectedUser.id}/`, formData);
    } else {
      await api.post("users/management/", formData);
    }
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <>
      <PageMeta
        title="User Management | HRMS Dashboard"
        description="Manage system users, roles, and access"
      />
      <PageBreadcrumb pageTitle="User Management" />
      <div className="space-y-6">
        <ComponentCard 
          title="System Users" 
          desc="Manage system access, assign roles, and deactivate accounts."
        >
          {/* Header Actions */}
          <div className="mb-4 flex justify-end">
            <Button size="sm" className="flex items-center gap-2" onClick={handleCreateUser}>
              <PlusIcon className="w-4 h-4 fill-current" />
              Add New User
            </Button>
          </div>
          
          <UserTable refreshTrigger={refreshTrigger} onEditUser={handleEditUser} />
        </ComponentCard>
      </div>

      <UserModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onSubmit={handleSubmit}
        user={selectedUser}
      />
    </>
  );
}

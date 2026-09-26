import ChangePasswordForm from "@/components/auth/ChangePasswordForm";
import PageMeta from "@/components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function ChangePassword() {
  return (
    <>
      <PageMeta
        title="Change Password | HRMS Dashboard"
        description="Change your password for HRMS"
      />
      <AuthLayout>
        <ChangePasswordForm />
      </AuthLayout>
    </>
  );
}

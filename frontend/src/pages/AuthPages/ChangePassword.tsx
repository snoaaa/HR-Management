import ChangePasswordForm from "@/components/auth/ChangePasswordForm";
import PageMeta from "@/components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function ChangePassword() {
  return (
    <>
      <PageMeta
        title="Change your password | Saint Jean HRMS"
        description="Saint Jean HRMS – human resources management"
      />
      <AuthLayout>
        <ChangePasswordForm />
      </AuthLayout>
    </>
  );
}

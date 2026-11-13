import SignUpForm from "@/components/auth/SignUpForm";
import PageMeta from "@/components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function SignUp() {
  return (
    <>
      <PageMeta
        title="Create an account | Saint Jean HRMS"
        description="Saint Jean HRMS – human resources management"
      />
      <AuthLayout>
        <SignUpForm />
      </AuthLayout>
    </>
  );
}

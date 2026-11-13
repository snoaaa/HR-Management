import SignInForm from "@/components/auth/SignInForm";
import PageMeta from "@/components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function SignIn() {
  return (
    <>
      <PageMeta
        title="Sign in | Saint Jean HRMS"
        description="Saint Jean HRMS – human resources management"
      />
      <AuthLayout>
        <SignInForm />
      </AuthLayout>
    </>
  );
}

import { Route, BrowserRouter as Router, Routes } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import AppLayout from "./layout/AppLayout";
import SignIn from "./pages/AuthPages/SignIn";
import SignUp from "./pages/AuthPages/SignUp";
import ChangePassword from "./pages/AuthPages/ChangePassword";
import Calendar from "./pages/Calendar";
import Home from "./pages/Dashboard/Home";
import NotFound from "./pages/OtherPage/NotFound";
import UserManagement from "./pages/Users/UserManagement";
import AuditTrail from "./pages/Users/AuditTrail";
import UserProfiles from "./pages/UserProfiles";
import EmployeeList from "./pages/Employees/EmployeeList";
import EmployeeForm from "./pages/Employees/EmployeeForm";
import EmployeeProfile from "./pages/Employees/EmployeeProfile";

import OrganisationSettings from "./pages/Organisation/OrganisationSettings";
import { ToastProvider } from "./context/ToastContext";
import { ConfirmHost } from "./components/kit/confirm";
import { PermissionsProvider } from "./context/PermissionsContext";
import ContractList from "./pages/Contracts/ContractList";
import ContractDetail from "./pages/Contracts/ContractDetail";
import Attendance from "./pages/Attendance/Attendance";
import LeaveAdmin from "./pages/Leave/LeaveAdmin";
import MyLeave from "./pages/Leave/MyLeave";
import Approvals from "./pages/Notifications/Approvals";
import Notifications from "./pages/Notifications/Notifications";
import PermissionMatrix from "./pages/Admin/PermissionMatrix";
import AdminSettings from "./pages/Admin/AdminSettings";
import Planning from "./pages/Planning/Planning";
import TimetableEditor from "./pages/Planning/TimetableEditor";
import PayrollCycle from "./pages/Payroll/PayrollCycle";
import PeriodCockpit from "./pages/Payroll/PeriodCockpit";
import { PayslipDetail, PayslipList } from "./pages/Payroll/Payslips";
import Simulation from "./pages/Payroll/Simulation";
import PayrollSettings from "./pages/Payroll/PayrollSettings";
import Accounting from "./pages/Accounting/Accounting";
import Careers from "./pages/Careers/Careers";
import Reports from "./pages/Reports/Reports";
import Evaluation from "./pages/Evaluation/Evaluation";
import EvaluationForm from "./pages/Evaluation/EvaluationForm";
import Recruitment from "./pages/Recruitment/Recruitment";
import CareersPage from "./pages/Recruitment/CareersPage";
import Training from "./pages/Training/Training";
import Documents from "./pages/Documents/Documents";
import DataAdmin from "./pages/Admin/DataAdmin";
import { MyDocuments, MyEvaluations, MyPayslips, MyTime, MyTraining } from "./pages/MySpace/MySpace";

export default function App() {
  return (
    <ToastProvider>
      <Router>
        <AuthProvider>
        <PermissionsProvider>
          <ScrollToTop />
          <ConfirmHost />
          <Routes>
            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
            <Route path="/change-password" element={<ChangePassword />} />
            
            {/* Dashboard Layout */}
            <Route element={<AppLayout />}>
              <Route index path="/" element={<Home />} />

              {/* Management */}
              <Route path="/users" element={<UserManagement />} />
              <Route path="/audit-trail" element={<AuditTrail />} />
              <Route path="/organisation" element={<OrganisationSettings />} />
              <Route path="/employees" element={<EmployeeList />} />
              <Route path="/employees/new" element={<EmployeeForm />} />
              <Route path="/employees/edit/:id" element={<EmployeeForm />} />
              <Route path="/employees/:id" element={<EmployeeProfile />} />
              <Route path="/contracts" element={<ContractList />} />
              <Route path="/contracts/:id" element={<ContractDetail />} />
              <Route path="/attendance" element={<Attendance />} />
              <Route path="/leave" element={<LeaveAdmin />} />
              <Route path="/my/leave" element={<MyLeave />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/admin/permissions" element={<PermissionMatrix />} />
              <Route path="/admin/settings" element={<AdminSettings />} />

              <Route path="/planning" element={<Planning />} />
              <Route path="/planning/:id" element={<TimetableEditor />} />
              <Route path="/payroll" element={<PayrollCycle />} />
              <Route path="/payroll/periods/:id" element={<PeriodCockpit />} />
              <Route path="/payroll/payslips" element={<PayslipList />} />
              <Route path="/payroll/payslips/:id" element={<PayslipDetail />} />
              <Route path="/payroll/simulation" element={<Simulation />} />
              <Route path="/payroll/settings" element={<PayrollSettings />} />
              <Route path="/accounting" element={<Accounting />} />
              <Route path="/careers-management" element={<Careers />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/evaluation" element={<Evaluation />} />
              <Route path="/evaluation/:id" element={<EvaluationForm />} />
              <Route path="/recruitment" element={<Recruitment />} />
              <Route path="/training" element={<Training />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/admin/data" element={<DataAdmin />} />
              <Route path="/my/time" element={<MyTime />} />
              <Route path="/my/payslips" element={<MyPayslips />} />
              <Route path="/my/documents" element={<MyDocuments />} />
              <Route path="/my/evaluations" element={<MyEvaluations />} />
              <Route path="/my/training" element={<MyTraining />} />

              {/* Others Page */}
              <Route path="/profile" element={<UserProfiles />} />
              <Route path="/calendar" element={<Calendar />} />
            </Route>
          </Route>

          {/* Auth Layout */}
          <Route path="/signin" element={<SignIn />} />
          <Route path="/careers" element={<CareersPage />} />
          <Route path="/signup" element={<SignUp />} />

          {/* Fallback Route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </PermissionsProvider>
      </AuthProvider>
    </Router>
    </ToastProvider>
  );
}

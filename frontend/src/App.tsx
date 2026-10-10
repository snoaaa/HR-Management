import { Route, BrowserRouter as Router, Routes } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import AppLayout from "./layout/AppLayout";
import SignIn from "./pages/AuthPages/SignIn";
import SignUp from "./pages/AuthPages/SignUp";
import ChangePassword from "./pages/AuthPages/ChangePassword";
import Calendar from "./pages/Calendar";
import BarChart from "./pages/Charts/BarChart";
import LineChart from "./pages/Charts/LineChart";
import Home from "./pages/Dashboard/Home";
import FormElements from "./pages/Forms/FormElements";
import Blank from "./pages/OtherPage/Blank";
import NotFound from "./pages/OtherPage/NotFound";
import BasicTables from "./pages/Tables/BasicTables";
import UserManagement from "./pages/Users/UserManagement";
import AuditTrail from "./pages/Users/AuditTrail";
import Alerts from "./pages/UiElements/Alerts";
import Avatars from "./pages/UiElements/Avatars";
import Badges from "./pages/UiElements/Badges";
import Buttons from "./pages/UiElements/Buttons";
import Images from "./pages/UiElements/Images";
import Videos from "./pages/UiElements/Videos";
import UserProfiles from "./pages/UserProfiles";
import EmployeeList from "./pages/Employees/EmployeeList";
import EmployeeForm from "./pages/Employees/EmployeeForm";
import EmployeeProfile from "./pages/Employees/EmployeeProfile";

import OrganisationSettings from "./pages/Organisation/OrganisationSettings";
import { ToastProvider } from "./context/ToastContext";
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
import ComingSoon from "./pages/OtherPage/ComingSoon";

export default function App() {
  return (
    <ToastProvider>
      <Router>
        <AuthProvider>
        <PermissionsProvider>
          <ScrollToTop />
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

              {/* Next iteration: the backend of these screens is ready */}
              <Route path="/planning" element={<ComingSoon />} />
              <Route path="/payroll/*" element={<ComingSoon />} />
              <Route path="/documents" element={<ComingSoon />} />
              <Route path="/my/time" element={<ComingSoon />} />
              <Route path="/my/payslips" element={<ComingSoon />} />
              <Route path="/my/documents" element={<ComingSoon />} />

              {/* Others Page */}
              <Route path="/profile" element={<UserProfiles />} />
              <Route path="/calendar" element={<Calendar />} />
              <Route path="/blank" element={<Blank />} />

              {/* Forms */}
              <Route path="/form-elements" element={<FormElements />} />

              {/* Tables */}
              <Route path="/basic-tables" element={<BasicTables />} />

              {/* Ui Elements */}
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/avatars" element={<Avatars />} />
              <Route path="/badge" element={<Badges />} />
              <Route path="/buttons" element={<Buttons />} />
              <Route path="/images" element={<Images />} />
              <Route path="/videos" element={<Videos />} />

              {/* Charts */}
              <Route path="/line-chart" element={<LineChart />} />
              <Route path="/bar-chart" element={<BarChart />} />
            </Route>
          </Route>

          {/* Auth Layout */}
          <Route path="/signin" element={<SignIn />} />
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

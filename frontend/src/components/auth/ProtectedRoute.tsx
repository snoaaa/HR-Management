import { Navigate, Outlet } from 'react-router';
import { useAuth } from '../../context/AuthContext';
import Loader from '../../components/common/Loader';

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

const ProtectedRoute = ({ allowedRoles }: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return <Loader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // If user does not have permission, redirect to their safe default dashboard
    return <Navigate to="/" replace />;
  }

  // BN-174: Enforce password change at first connection
  if (user?.requires_password_change && window.location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />;
  }

  // Also prevent users who don't need a password change from accessing the change-password page 
  // via this route flow (though they might access it via profile later, but for now we enforce the first connection rule).
  if (!user?.requires_password_change && window.location.pathname === '/change-password') {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../services/apiClient';

const AuthContext = createContext(null);

export const DEMO_USERS = [
  { username: 'admin', label: 'Security & System Admin', role: 'Security & Audit Officer', password: 'Antigravity#2026!' },
  { username: 'hr_manager', label: 'HR Administrator', role: 'HR Administrator', password: 'Corporate#HR2026!' },
  { username: 'payroll_officer', label: 'Payroll Officer', role: 'Payroll Officer', password: 'Payroll#Sec2026!' },
  { username: 'dept_manager', label: 'Department Manager', role: 'Department Manager', password: 'Engineering#2026!' },
  { username: 'employee_alice', label: 'Frontend Developer', role: 'Employee (Self-Service)', password: 'AliceDev#2026!' },
  { username: 'employee_bob', label: 'DevOps Engineer', role: 'Employee (Self-Service)', password: 'BobDev#2026!' },
  { username: 'new_hire', label: 'New Hire (Initial Setup)', role: 'Forced Pwd Change', password: 'Welcome#Staff2026!' },
];

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false);
  const [twoFactorVerified, setTwoFactorVerified] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessionRemaining, setSessionRemaining] = useState(1800); // 30 minutes in seconds

  const fetchCurrentUser = useCallback(async () => {
    try {
      const res = await apiClient.get('/auth/me/');
      setCurrentUser(res.data.user);
      setPermissions(res.data.permissions || []);
      setMustChangePassword(res.data.user.must_change_password);
      setRequiresTwoFactor(res.data.user.is_payroll_authorized || false);
      setTwoFactorEnabled(res.data.user.two_factor_enabled);
      return res.data;
    } catch {
      setCurrentUser(null);
      setPermissions([]);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  // Inactivity session timer simulation
  useEffect(() => {
    if (!currentUser) return;

    const resetTimer = () => setSessionRemaining(1800);
    window.addEventListener('mousemove', resetTimer);
    window.addEventListener('keydown', resetTimer);

    const interval = setInterval(() => {
      setSessionRemaining((prev) => {
        if (prev <= 1) {
          logout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      window.removeEventListener('mousemove', resetTimer);
      window.removeEventListener('keydown', resetTimer);
      clearInterval(interval);
    };
  }, [currentUser]);

  const login = async (username, password) => {
    try {
      const res = await apiClient.post('/auth/login/', { username, password });
      setCurrentUser(res.data.user);
      setMustChangePassword(res.data.must_change_password);
      setRequiresTwoFactor(res.data.requires_two_factor);
      setTwoFactorEnabled(res.data.two_factor_enabled);
      setTwoFactorVerified(false);
      setSessionRemaining(1800);
      await fetchCurrentUser();
      return { success: true, data: res.data };
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed.';
      return { success: false, error: msg, status: err.response?.status };
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout/');
    } catch {
      // ignore
    }
    setCurrentUser(null);
    setPermissions([]);
    setMustChangePassword(false);
    setRequiresTwoFactor(false);
    setTwoFactorVerified(false);
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      const res = await apiClient.post('/auth/password/change/', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMustChangePassword(false);
      await fetchCurrentUser();
      return { success: true, data: res.data };
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.new_password || err.response?.data?.current_password || err.response?.data?.detail || 'Password change failed.',
      };
    }
  };

  const setup2FA = async () => {
    try {
      const res = await apiClient.post('/auth/2fa/setup/');
      return { success: true, data: res.data };
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Failed to setup 2FA' };
    }
  };

  const verify2FA = async (code) => {
    try {
      const res = await apiClient.post('/auth/2fa/verify/', { code });
      setTwoFactorVerified(true);
      setTwoFactorEnabled(true);
      await fetchCurrentUser();
      return { success: true, data: res.data };
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Invalid 2FA code.' };
    }
  };

  const hasPermission = (module, action) => {
    if (!currentUser) return false;
    if (currentUser.is_superuser) return true;
    return permissions.some((p) => p.module === module && p.action === action);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        permissions,
        loading,
        mustChangePassword,
        requiresTwoFactor,
        twoFactorVerified,
        twoFactorEnabled,
        sessionRemaining,
        login,
        logout,
        changePassword,
        setup2FA,
        verify2FA,
        hasPermission,
        refreshUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

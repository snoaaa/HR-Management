import React, { useState } from 'react';
import { AuthProvider, useAuth, DEMO_USERS } from './context/AuthContext';
import LoginScreen from './components/LoginScreen';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import OverviewTab from './components/OverviewTab';
import UsersTab from './components/UsersTab';
import RolesPermissionsTab from './components/RolesPermissionsTab';
import SalaryVaultTab from './components/SalaryVaultTab';
import AuditTrailTab from './components/AuditTrailTab';
import PrivacyGdprTab from './components/PrivacyGdprTab';
import PasswordChangeModal from './components/PasswordChangeModal';
import TwoFactorModal from './components/TwoFactorModal';
import { Sparkles, Shield, AlertTriangle } from 'lucide-react';

function MainDashboard() {
  const { currentUser, loading, mustChangePassword, login } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [show2FAModal, setShow2FAModal] = useState(false);

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-app)',
          color: 'var(--text-secondary)',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div className="brand-icon" style={{ margin: '0 auto 16px', animation: 'pulse 1.5s infinite' }}>
            <Shield size={24} />
          </div>
          <p>Initializing Security Subsystem...</p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return <LoginScreen />;
  }

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab setActiveTab={setActiveTab} />;
      case 'users':
        return <UsersTab />;
      case 'roles':
        return <RolesPermissionsTab />;
      case 'salary':
        return <SalaryVaultTab />;
      case 'audit':
        return <AuditTrailTab />;
      case 'gdpr':
        return <PrivacyGdprTab />;
      default:
        return <OverviewTab setActiveTab={setActiveTab} />;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenPasswordModal={() => setShowPasswordModal(true)}
        onOpen2FAModal={() => setShow2FAModal(true)}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        <Topbar
          activeTab={activeTab}
          onOpenPasswordModal={() => setShowPasswordModal(true)}
          onOpen2FAModal={() => setShow2FAModal(true)}
        />

        <main className="content-body">
          {/* Persona Switcher Quick Bar */}
          <div className="demo-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="#818cf8" />
              <div>
                <strong style={{ fontSize: '0.82rem', color: '#fff' }}>Test Persona Switcher:</strong>
                <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginLeft: '6px' }}>
                  Click to switch roles and observe live perimeter scoping and confidentiality restrictions.
                </span>
              </div>
            </div>

            <div className="demo-chips">
              {DEMO_USERS.map((u) => {
                const isActive = currentUser.username === u.username;
                return (
                  <button
                    key={u.username}
                    className={`demo-chip ${isActive ? 'active' : ''}`}
                    onClick={() => login(u.username, u.password)}
                    title={`Switch to ${u.label}`}
                  >
                    <span>{u.label.split(' ')[0]}</span>
                    <span style={{ opacity: 0.7, fontSize: '0.7rem' }}>({u.username})</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tab View */}
          {renderActiveTab()}
        </main>
      </div>

      {/* Mandatory / Optional Password Change Modal */}
      <PasswordChangeModal
        isOpen={mustChangePassword || showPasswordModal}
        isForced={mustChangePassword}
        onClose={() => setShowPasswordModal(false)}
      />

      {/* 2FA Setup / Verification Modal */}
      <TwoFactorModal
        isOpen={show2FAModal}
        onClose={() => setShow2FAModal(false)}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainDashboard />
    </AuthProvider>
  );
}

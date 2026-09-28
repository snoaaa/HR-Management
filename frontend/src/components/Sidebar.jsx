import React from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  Users,
  Key,
  Lock,
  History,
  FolderLock,
  LayoutDashboard,
  LogOut,
  Building2,
  Clock,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, onOpenPasswordModal, onOpen2FAModal }) {
  const { currentUser, logout, sessionRemaining, twoFactorVerified } = useAuth();

  const minutes = Math.floor(sessionRemaining / 60);
  const seconds = sessionRemaining % 60;
  const timerDisplay = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;

  const navItems = [
    { id: 'overview', label: 'Security Overview', icon: LayoutDashboard },
    { id: 'users', label: 'Users & Perimeters', icon: Users },
    { id: 'roles', label: 'Roles & Permissions', icon: Key },
    { id: 'salary', label: 'Confidential Salary Vault', icon: Lock },
    { id: 'audit', label: 'Immutable Audit Trail', icon: History },
    { id: 'gdpr', label: 'Data Privacy & Rights', icon: FolderLock },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Shield size={22} />
          </div>
          <div className="brand-info">
            <h2>HRMS Portal</h2>
            <span>Security & Audit</span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="sidebar-nav">
        <div className="nav-section-title">Security Governance</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span style={{ flex: 1 }}>{item.label}</span>
            </button>
          );
        })}

        {/* Security Actions Section */}
        <div className="nav-section-title" style={{ marginTop: '12px' }}>
          Account Security
        </div>

        <button className="nav-item" onClick={onOpenPasswordModal}>
          <KeyRound size={18} />
          <span style={{ flex: 1 }}>Change Password</span>
        </button>

        <button className="nav-item" onClick={onOpen2FAModal}>
          <ShieldCheck size={18} />
          <span style={{ flex: 1 }}>2FA Authentication</span>
          <span
            className={`badge ${twoFactorVerified ? 'badge-emerald' : 'badge-amber'}`}
            style={{ fontSize: '0.62rem', padding: '1px 6px' }}
          >
            {twoFactorVerified ? 'Active' : 'Setup'}
          </span>
        </button>
      </div>

      {/* Footer / Session Timer & User Info */}
      <div className="sidebar-footer">
        {/* Session Inactivity Timeout Counter */}
        <div
          style={{
            padding: '8px 10px',
            background: sessionRemaining < 300 ? 'var(--rose-bg)' : 'var(--bg-input)',
            border: `1px solid ${sessionRemaining < 300 ? 'var(--rose-border)' : 'var(--border-subtle)'}`,
            borderRadius: 'var(--radius-md)',
            marginBottom: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={14} color={sessionRemaining < 300 ? '#fb7185' : '#818cf8'} />
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Session Timeout:</span>
          </div>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              fontWeight: 700,
              color: sessionRemaining < 300 ? '#fb7185' : '#38bdf8',
            }}
          >
            {timerDisplay}
          </span>
        </div>

        {/* Current User Badge */}
        <div className="user-badge-mini">
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <strong style={{ fontSize: '0.82rem', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {currentUser?.first_name || currentUser?.username}
            </strong>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              @{currentUser?.username}
            </span>
          </div>
          <button
            onClick={logout}
            className="btn btn-outline btn-sm"
            style={{ padding: '4px 8px', color: 'var(--rose-text)', borderColor: 'var(--rose-border)' }}
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}

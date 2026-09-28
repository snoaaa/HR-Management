import React from 'react';
import { useAuth, DEMO_USERS } from '../context/AuthContext';
import {
  ShieldCheck,
  Lock,
  User,
  LogOut,
  KeyRound,
  Shield,
  Layers,
  Sparkles,
} from 'lucide-react';

export default function Topbar({ activeTab, onOpenPasswordModal, onOpen2FAModal }) {
  const { currentUser, logout, twoFactorVerified, login } = useAuth();

  const tabTitles = {
    overview: { title: 'Security & Audit Governance', subtitle: 'Global system security status and compliance indicators' },
    users: { title: 'Individual Accounts & Perimeters', subtitle: 'User account administration & perimeter scoping' },
    roles: { title: 'Roles & Fine-Grained Permissions', subtitle: 'Functional module grants & action permission matrix' },
    salary: { title: 'Confidential Compensation Vault', subtitle: 'Protected salary records & two-factor verification' },
    audit: { title: 'Immutable Audit Trail', subtitle: 'Append-only chronological logging & CSV audit export' },
    gdpr: { title: 'Personal Data Protection & Privacy', subtitle: 'Data subject rights of access and rectification' },
  };

  const currentInfo = tabTitles[activeTab] || tabTitles.overview;

  const handleQuickSwitch = async (username) => {
    const demo = DEMO_USERS.find((d) => d.username === username);
    if (demo) {
      await login(demo.username, demo.password);
    }
  };

  return (
    <header className="topbar">
      {/* Title & Context */}
      <div className="page-title">
        <h1>{currentInfo.title}</h1>
        <p>{currentInfo.subtitle}</p>
      </div>

      {/* Actions & Role Switcher */}
      <div className="topbar-actions">
        {/* Quick Role Switcher Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
            Switch Persona:
          </span>
          <select
            className="select"
            style={{ padding: '6px 10px', fontSize: '0.78rem', width: 'auto' }}
            value={currentUser?.username || ''}
            onChange={(e) => handleQuickSwitch(e.target.value)}
          >
            {DEMO_USERS.map((u) => (
              <option key={u.username} value={u.username}>
                {u.label}
              </option>
            ))}
          </select>
        </div>

        {/* 2FA Status Indicator */}
        {twoFactorVerified ? (
          <span className="badge badge-emerald">
            <ShieldCheck size={12} /> 2FA Verified
          </span>
        ) : currentUser?.is_payroll_authorized ? (
          <button
            className="btn btn-primary btn-sm"
            onClick={onOpen2FAModal}
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
          >
            <Lock size={12} /> Verify 2FA
          </button>
        ) : (
          <span className="badge badge-cyan" style={{ fontSize: '0.75rem' }}>
            Standard Access
          </span>
        )}

        {/* User Avatar / Profile Menu */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #a855f7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 700,
              fontSize: '0.85rem',
            }}
          >
            {(currentUser?.first_name?.[0] || currentUser?.username?.[0] || 'U').toUpperCase()}
          </div>
        </div>
      </div>
    </header>
  );
}

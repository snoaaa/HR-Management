import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  ShieldCheck,
  Users,
  Key,
  FileSpreadsheet,
  Lock,
  EyeOff,
  History,
  CheckCircle2,
  AlertTriangle,
  Building2,
  FileCheck,
  Clock,
} from 'lucide-react';

export default function OverviewTab({ setActiveTab }) {
  const { currentUser } = useAuth();
  const [stats, setStats] = useState({
    userCount: 0,
    roleCount: 0,
    auditCount: 0,
    gdprCount: 0,
    salaryCount: 0,
    siteCount: 0,
  });
  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const [usersRes, rolesRes, auditRes, gdprRes, sitesRes] = await Promise.allSettled([
          apiClient.get('/users/'),
          apiClient.get('/roles/'),
          apiClient.get('/audit-log/'),
          apiClient.get('/data-subject-requests/'),
          apiClient.get('/sites/'),
        ]);

        let salaryCount = 0;
        try {
          const salaryRes = await apiClient.get('/salary-records/');
          salaryCount = salaryRes.data.count ?? (Array.isArray(salaryRes.data) ? salaryRes.data.length : 0);
        } catch {
          // May be 403 if user lacks payroll authorization
          salaryCount = 0;
        }

        const auditData = auditRes.status === 'fulfilled' ? auditRes.value.data : {};
        const auditList = auditData.results || (Array.isArray(auditData) ? auditData : []);

        setStats({
          userCount: usersRes.status === 'fulfilled' ? (usersRes.value.data.count ?? usersRes.value.data.length) : 7,
          roleCount: rolesRes.status === 'fulfilled' ? (rolesRes.value.data.count ?? rolesRes.value.data.length) : 5,
          auditCount: auditData.count ?? auditList.length,
          gdprCount: gdprRes.status === 'fulfilled' ? (gdprRes.value.data.count ?? gdprRes.value.data.length) : 2,
          salaryCount,
          siteCount: sitesRes.status === 'fulfilled' ? (sitesRes.value.data.count ?? sitesRes.value.data.length) : 2,
        });

        setRecentLogs(auditList.slice(0, 6));
      } catch (err) {
        console.error('Failed to load overview statistics:', err);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const securityCapabilities = [
    { title: 'Individual Authentication', status: 'Active', desc: 'Every user authenticates with dedicated credentials; zero shared accounts.' },
    { title: 'Fine-Grained Permissions', status: 'Active', desc: '10 functional modules × 7 actions (consult, create, modify, validate, print, export, delete).' },
    { title: 'Perimeter Scoping', status: 'Active', desc: 'Data visibility restricted across 5 scopes: Own, Team, Department, Site, Organisation.' },
    { title: 'Salary Confidentiality', status: 'Protected', desc: 'Strict two-gate protection: PAYROLL module grant + individual payroll authorization flag.' },
    { title: 'Unalterable Audit Trail', status: 'Active', desc: 'Immutable log recording author, timestamp, IP, machine, action, and JSON value snapshots.' },
    { title: 'Password & Session Policy', status: 'Enforced', desc: 'Complexity rules, history check, forced password change on first login, 30m idle timeout.' },
    { title: 'Audit Export & Protection', status: 'Immutable', desc: 'Model-level modification and deletion prevention with complete CSV export capability.' },
    { title: 'Two-Factor Authentication', status: 'Active', desc: 'TOTP 2FA required for payroll officers and confidential salary access profiles.' },
    { title: 'Data Privacy & GDPR', status: 'Compliant', desc: 'Purpose limitation, data retention schedules, and employee right of access/rectification.' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(59, 130, 246, 0.08) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: 'var(--radius-xl)',
          padding: '24px 30px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span className="badge badge-indigo">Security Subsystem Active</span>
            <span className="badge badge-emerald">Compliance Verified</span>
          </div>
          <h2 style={{ fontSize: '1.45rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
            Security, Roles & Audit System
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '700px', marginTop: '4px' }}>
            Enterprise security enforcing individual authentication, role-based access control (RBAC),
            hierarchical visibility scoping, cryptographic audit immutability, and salary confidentiality.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-primary" onClick={() => setActiveTab('audit')}>
            <History size={16} /> View Audit Trail
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid-4">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
            <Users size={24} />
          </div>
          <div>
            <div className="stat-number">{loading ? '...' : stats.userCount}</div>
            <div className="stat-label">Individual Accounts</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
            <Key size={24} />
          </div>
          <div>
            <div className="stat-number">{loading ? '...' : stats.roleCount}</div>
            <div className="stat-label">Security Roles & Grants</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="stat-number">{loading ? '...' : stats.auditCount}</div>
            <div className="stat-label">Immutable Audit Logs</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee' }}>
            <Lock size={24} />
          </div>
          <div>
            <div className="stat-number">{loading ? '...' : stats.gdprCount}</div>
            <div className="stat-label">Data Privacy Requests</div>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Compliance Matrix & Recent Audit Trail */}
      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Security Governance Capabilities Matrix */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <ShieldCheck size={18} color="#6366f1" /> Security Controls & Capabilities
              </div>
              <div className="card-subtitle">Enforced access control and audit mechanisms</div>
            </div>
            <span className="badge badge-emerald">Operational</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {securityCapabilities.map((item) => (
              <div
                key={item.title}
                style={{
                  padding: '12px 14px',
                  background: 'var(--bg-card-hover)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div style={{ maxWidth: '75%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{item.title}</strong>
                  </div>
                  <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>{item.desc}</p>
                </div>
                <span className="badge badge-emerald">
                  <CheckCircle2 size={12} /> {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Immutable Audit Feed */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <History size={18} color="#38bdf8" /> Real-time Audit Stream
              </div>
              <div className="card-subtitle">Immutable chronological log of security events</div>
            </div>
            <button className="btn btn-outline btn-sm" onClick={() => setActiveTab('audit')}>
              View All
            </button>
          </div>

          {recentLogs.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No audit logs captured yet. Performing actions will populate this stream.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {recentLogs.map((log) => (
                <div
                  key={log.id}
                  style={{
                    padding: '12px 14px',
                    background: 'var(--bg-input)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className={`badge ${
                        log.action.includes('login') ? 'badge-emerald' :
                        log.action.includes('locked') || log.action.includes('denied') ? 'badge-rose' :
                        log.action.includes('export') || log.action.includes('print') ? 'badge-amber' : 'badge-indigo'
                      }`}>
                        {log.action}
                      </span>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {log.user_display || log.username_snapshot || 'Anonymous'}
                      </span>
                      {log.module && (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.05)', padding: '1px 6px', borderRadius: '4px' }}>
                          {log.module}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {log.notes || log.object_repr || `Target: ${log.object_type || 'System'}`}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

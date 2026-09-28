import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  Key,
  Shield,
  Plus,
  Check,
  X,
  UserCheck,
  Building,
  Lock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Layers,
} from 'lucide-react';

const ALL_MODULES = [
  { key: 'employees', label: 'Employee Records' },
  { key: 'payroll', label: 'Payroll & Compensation' },
  { key: 'leave', label: 'Leave & Absence' },
  { key: 'time_attendance', label: 'Time & Attendance' },
  { key: 'recruitment', label: 'Recruitment & Onboarding' },
  { key: 'training', label: 'Training & Skills' },
  { key: 'performance', label: 'Performance Review' },
  { key: 'documents', label: 'Document Generation' },
  { key: 'admin', label: 'Security & System Admin' },
  { key: 'audit', label: 'Audit Trail & Compliance' },
];

const ALL_ACTIONS = [
  { key: 'consult', label: 'Consult' },
  { key: 'create', label: 'Create' },
  { key: 'modify', label: 'Modify' },
  { key: 'validate', label: 'Validate' },
  { key: 'print', label: 'Print' },
  { key: 'export', label: 'Export' },
  { key: 'delete', label: 'Delete' },
];

const SCOPES = [
  { key: 'own', label: 'Own Data Only' },
  { key: 'team', label: 'Team' },
  { key: 'department', label: 'Department' },
  { key: 'site', label: 'Site' },
  { key: 'organisation', label: 'Whole Organisation' },
];

export default function RolesPermissionsTab() {
  const { hasPermission } = useAuth();
  const [roles, setRoles] = useState([]);
  const [userRoles, setUserRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);

  // New Role Form State
  const [newRole, setNewRole] = useState({
    name: '',
    description: '',
    scope: 'department',
    requires_two_factor: false,
    permissions: {}, // format: { 'payroll_consult': true }
  });
  const [createError, setCreateError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Assign Role Form State
  const [assignData, setAssignData] = useState({ user_id: '', role_id: '' });
  const [assignError, setAssignError] = useState(null);

  const canAdmin = hasPermission('admin', 'create') || hasPermission('admin', 'modify');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rolesRes, userRolesRes, usersRes] = await Promise.allSettled([
        apiClient.get('/roles/'),
        apiClient.get('/user-roles/'),
        apiClient.get('/users/'),
      ]);

      if (rolesRes.status === 'fulfilled') {
        const rData = rolesRes.value.data;
        const rList = rData.results || (Array.isArray(rData) ? rData : []);
        setRoles(rList);
        if (rList.length > 0 && !selectedRole) {
          setSelectedRole(rList[0]);
        } else if (selectedRole) {
          const updated = rList.find((r) => r.id === selectedRole.id);
          if (updated) setSelectedRole(updated);
        }
      }

      if (userRolesRes.status === 'fulfilled') {
        const urData = userRolesRes.value.data;
        setUserRoles(urData.results || (Array.isArray(urData) ? urData : []));
      }

      if (usersRes.status === 'fulfilled') {
        const uData = usersRes.value.data;
        setUsers(uData.results || (Array.isArray(uData) ? uData : []));
      }
    } catch (err) {
      console.error('Failed to fetch roles & permissions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const hasGrant = (role, modKey, actKey) => {
    if (!role || !role.permissions) return false;
    return role.permissions.some((p) => p.module === modKey && p.action === actKey);
  };

  const handleCreateRole = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setCreateError(null);

    try {
      // 1. Create Role
      const roleRes = await apiClient.post('/roles/', {
        name: newRole.name,
        description: newRole.description,
        scope: newRole.scope,
        requires_two_factor: newRole.requires_two_factor,
        is_active: true,
      });
      const createdRoleId = roleRes.data.id;

      // 2. Create Grants
      const grants = [];
      Object.keys(newRole.permissions).forEach((key) => {
        if (newRole.permissions[key]) {
          const [module, action] = key.split(':');
          grants.push(apiClient.post('/role-permissions/', { role: createdRoleId, module, action }));
        }
      });
      await Promise.all(grants);

      setShowCreateModal(false);
      setNewRole({
        name: '',
        description: '',
        scope: 'department',
        requires_two_factor: false,
        permissions: {},
      });
      await fetchData();
    } catch (err) {
      setCreateError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to create role.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAssignRole = async (e) => {
    e.preventDefault();
    if (!assignData.user_id || !assignData.role_id) return;
    setSubmitting(true);
    setAssignError(null);

    try {
      await apiClient.post('/user-roles/', {
        user: parseInt(assignData.user_id),
        role: parseInt(assignData.role_id),
      });
      setShowAssignModal(false);
      setAssignData({ user_id: '', role_id: '' });
      await fetchData();
    } catch (err) {
      setAssignError(err.response?.data?.detail || 'Failed to assign role.');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleNewGrant = (modKey, actKey) => {
    const key = `${modKey}:${actKey}`;
    setNewRole((prev) => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        [key]: !prev.permissions[key],
      },
    }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <Key size={20} color="#a855f7" /> Fine-Grained Role & Permission Matrix
            </div>
            <div className="card-subtitle">
              Granular access control across functional modules & actions with perimeter scopes.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchData}>
              <RefreshCw size={14} /> Refresh
            </button>
            {canAdmin && (
              <>
                <button className="btn btn-secondary" onClick={() => setShowAssignModal(true)}>
                  <UserCheck size={16} /> Assign Role to User
                </button>
                <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                  <Plus size={16} /> Define New Role
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Role Selection & Permission Matrix */}
      <div className="grid-2" style={{ gridTemplateColumns: '320px 1fr', alignItems: 'start' }}>
        {/* Roles List */}
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Available Roles ({roles.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {roles.map((role) => (
              <div
                key={role.id}
                onClick={() => setSelectedRole(role)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: selectedRole?.id === role.id ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-input)',
                  border: `1px solid ${selectedRole?.id === role.id ? '#6366f1' : 'var(--border-subtle)'}`,
                  cursor: 'pointer',
                  transition: 'var(--transition)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <strong style={{ fontSize: '0.9rem', color: selectedRole?.id === role.id ? '#fff' : 'var(--text-primary)' }}>
                    {role.name}
                  </strong>
                  <span className="badge badge-indigo" style={{ fontSize: '0.68rem' }}>
                    {role.scope}
                  </span>
                </div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{role.description}</div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                  <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                    {role.permissions?.length || 0} grants
                  </span>
                  {role.requires_two_factor && (
                    <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                      <Lock size={8} /> 2FA Required
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Permissions Matrix for Selected Role */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title" style={{ fontSize: '1.1rem' }}>
                <Shield size={18} color="#6366f1" /> {selectedRole?.name}
              </div>
              <div className="card-subtitle">
                Scope: <strong style={{ color: '#818cf8', textTransform: 'uppercase' }}>{selectedRole?.scope}</strong> •{' '}
                {selectedRole?.permissions?.length || 0} active grants
              </div>
            </div>
            {selectedRole?.requires_two_factor && (
              <span className="badge badge-rose">
                <Lock size={12} /> Requires 2FA Verification
              </span>
            )}
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Functional Module</th>
                  {ALL_ACTIONS.map((a) => (
                    <th key={a.key} style={{ textAlign: 'center' }}>
                      {a.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ALL_MODULES.map((m) => (
                  <tr key={m.key}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{m.label}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {m.key}
                      </div>
                    </td>
                    {ALL_ACTIONS.map((a) => {
                      const granted = hasGrant(selectedRole, m.key, a.key);
                      return (
                        <td key={a.key} className="matrix-cell">
                          {granted ? (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '24px',
                                height: '24px',
                                background: 'rgba(16, 185, 129, 0.2)',
                                color: '#34d399',
                                borderRadius: '6px',
                                border: '1px solid rgba(16, 185, 129, 0.4)',
                              }}
                            >
                              <Check size={14} />
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', opacity: 0.3 }}>—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* User Role Assignments Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <UserCheck size={18} color="#38bdf8" /> User Role Assignments
            </div>
            <div className="card-subtitle">Active mapping of roles assigned to individual personnel</div>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>User Account</th>
                <th>Assigned Role</th>
                <th>Granted Perimeter Scope</th>
                <th>Assigned By</th>
                <th>Assignment Date</th>
              </tr>
            </thead>
            <tbody>
              {userRoles.map((ur) => (
                <tr key={ur.id}>
                  <td>
                    <strong>{ur.user_display || `User #${ur.user}`}</strong>
                  </td>
                  <td>
                    <span className="badge badge-indigo">{ur.role_name}</span>
                  </td>
                  <td>
                    <span className="badge badge-cyan">
                      {roles.find((r) => r.id === ur.role)?.scope || 'Organisation'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    {ur.assigned_by ? `Admin #${ur.assigned_by}` : 'System Initial Seed'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {new Date(ur.assigned_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Role Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '850px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '8px', borderRadius: '8px' }}>
                  <Plus size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Define Custom Role</h3>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Select perimeter scope and grant fine-grained permissions per module.
                  </p>
                </div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowCreateModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateRole}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {createError && (
                  <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem' }}>
                    {createError}
                  </div>
                )}

                <div className="grid-3">
                  <div className="form-group">
                    <label>Role Name *</label>
                    <input
                      type="text"
                      className="input"
                      required
                      value={newRole.name}
                      onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                      placeholder="e.g. Leave Officer"
                    />
                  </div>
                  <div className="form-group">
                    <label>Perimeter Scope *</label>
                    <select
                      className="select"
                      value={newRole.scope}
                      onChange={(e) => setNewRole({ ...newRole, scope: e.target.value })}
                    >
                      {SCOPES.map((s) => (
                        <option key={s.key} value={s.key}>
                          {s.label} ({s.key})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ justifyContent: 'center' }}>
                    <label>Security Requirement</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                      <input
                        type="checkbox"
                        id="role2faCheck"
                        className="matrix-check"
                        checked={newRole.requires_two_factor}
                        onChange={(e) => setNewRole({ ...newRole, requires_two_factor: e.target.checked })}
                      />
                      <label htmlFor="role2faCheck" style={{ cursor: 'pointer', color: 'var(--text-primary)' }}>
                        Enforce 2FA
                      </label>
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label>Description</label>
                  <input
                    type="text"
                    className="input"
                    value={newRole.description}
                    onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                    placeholder="Describe the duties and intended usage for this profile..."
                  />
                </div>

                {/* Permission Grant Matrix Checkboxes */}
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                    Grant Matrix (Module × Action)
                  </div>
                  <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Module</th>
                          {ALL_ACTIONS.map((a) => (
                            <th key={a.key} style={{ textAlign: 'center' }}>
                              {a.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {ALL_MODULES.map((m) => (
                          <tr key={m.key}>
                            <td style={{ fontWeight: 600, fontSize: '0.82rem' }}>{m.label}</td>
                            {ALL_ACTIONS.map((a) => (
                              <td key={a.key} className="matrix-cell">
                                <input
                                  type="checkbox"
                                  className="matrix-check"
                                  checked={!!newRole.permissions[`${m.key}:${a.key}`]}
                                  onChange={() => toggleNewGrant(m.key, a.key)}
                                />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating Role...' : 'Save Role & Grants'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Role to User Modal */}
      {showAssignModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '8px', borderRadius: '8px' }}>
                  <UserCheck size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Assign Role to User</h3>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Action will be recorded automatically in the audit trail.
                  </p>
                </div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowAssignModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleAssignRole}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {assignError && (
                  <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem' }}>
                    {assignError}
                  </div>
                )}

                <div className="form-group">
                  <label>Select User Account</label>
                  <select
                    className="select"
                    required
                    value={assignData.user_id}
                    onChange={(e) => setAssignData({ ...assignData, user_id: e.target.value })}
                  >
                    <option value="">Select a user...</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.username} ({u.first_name} {u.last_name || ''})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Select Role to Grant</label>
                  <select
                    className="select"
                    required
                    value={assignData.role_id}
                    onChange={(e) => setAssignData({ ...assignData, role_id: e.target.value })}
                  >
                    <option value="">Select a role...</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} (Scope: {r.scope})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAssignModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

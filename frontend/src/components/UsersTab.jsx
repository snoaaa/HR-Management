import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  Shield,
  Building,
  KeyRound,
  Lock,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

export default function UsersTab() {
  const { hasPermission } = useAuth();
  const [users, setUsers] = useState([]);
  const [sites, setSites] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [teams, setTeams] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterSite, setFilterSite] = useState('');
  const [filterDept, setFilterDept] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New User Form State
  const [formData, setFormData] = useState({
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    employee_id: '',
    password: '',
    site: '',
    department: '',
    team: '',
    is_payroll_authorized: false,
    processing_purpose: 'Human resources management: payroll, leave, performance and legal compliance.',
  });
  const [createError, setCreateError] = useState(null);
  const [createSuccess, setCreateSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const canCreateUser = hasPermission('admin', 'create');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, sitesRes, deptsRes, teamsRes, rolesRes] = await Promise.allSettled([
        apiClient.get('/users/'),
        apiClient.get('/sites/'),
        apiClient.get('/departments/'),
        apiClient.get('/teams/'),
        apiClient.get('/roles/'),
      ]);

      if (usersRes.status === 'fulfilled') {
        const uData = usersRes.value.data;
        setUsers(uData.results || (Array.isArray(uData) ? uData : []));
      }
      if (sitesRes.status === 'fulfilled') {
        const sData = sitesRes.value.data;
        setSites(sData.results || (Array.isArray(sData) ? sData : []));
      }
      if (deptsRes.status === 'fulfilled') {
        const dData = deptsRes.value.data;
        setDepartments(dData.results || (Array.isArray(dData) ? dData : []));
      }
      if (teamsRes.status === 'fulfilled') {
        const tData = teamsRes.value.data;
        setTeams(tData.results || (Array.isArray(tData) ? tData : []));
      }
      if (rolesRes.status === 'fulfilled') {
        const rData = rolesRes.value.data;
        setRoles(rData.results || (Array.isArray(rData) ? rData : []));
      }
    } catch (err) {
      console.error('Failed to load user management data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setCreateError(null);

    try {
      const payload = {
        username: formData.username,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        employee_id: formData.employee_id,
        password: formData.password,
        site: formData.site ? parseInt(formData.site) : null,
        department: formData.department ? parseInt(formData.department) : null,
        team: formData.team ? parseInt(formData.team) : null,
        is_payroll_authorized: formData.is_payroll_authorized,
        processing_purpose: formData.processing_purpose,
      };

      await apiClient.post('/users/', payload);
      setCreateSuccess(true);
      setTimeout(() => {
        setCreateSuccess(false);
        setShowCreateModal(false);
        setFormData({
          username: '',
          first_name: '',
          last_name: '',
          email: '',
          employee_id: '',
          password: '',
          site: '',
          department: '',
          team: '',
          is_payroll_authorized: false,
          processing_purpose: 'Human resources management: payroll, leave, performance and legal compliance.',
        });
        fetchData();
      }, 1000);
    } catch (err) {
      const detail = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to create user.';
      setCreateError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchSearch =
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      (u.first_name && u.first_name.toLowerCase().includes(search.toLowerCase())) ||
      (u.last_name && u.last_name.toLowerCase().includes(search.toLowerCase())) ||
      (u.employee_id && u.employee_id.toLowerCase().includes(search.toLowerCase()));

    const matchSite = !filterSite || u.site === parseInt(filterSite);
    const matchDept = !filterDept || u.department === parseInt(filterDept);

    return matchSearch && matchSite && matchDept;
  });

  const getSiteName = (id) => sites.find((s) => s.id === id)?.name || '-';
  const getDeptName = (id) => departments.find((d) => d.id === id)?.name || '-';
  const getTeamName = (id) => teams.find((t) => t.id === id)?.name || '-';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Controls */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <Users size={20} color="#6366f1" /> Individual User Accounts & Perimeters
            </div>
            <div className="card-subtitle">
              Individual account management & perimeter scoping (Site, Department, Team)
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchData}>
              <RefreshCw size={14} /> Refresh
            </button>
            {canCreateUser && (
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                <UserPlus size={16} /> Create Individual Account
              </button>
            )}
          </div>
        </div>

        {/* Filters Bar */}
        <div style={{ display: 'flex', gap: '14px', marginTop: '20px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 240px', position: 'relative' }}>
            <input
              type="text"
              className="input"
              placeholder="Search by username, name, or employee ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '36px' }}
            />
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
          </div>

          <div style={{ width: '200px' }}>
            <select className="select" value={filterSite} onChange={(e) => setFilterSite(e.target.value)}>
              <option value="">All Sites</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          <div style={{ width: '200px' }}>
            <select className="select" value={filterDept} onChange={(e) => setFilterDept(e.target.value)}>
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>User / Matriculation</th>
              <th>Full Name & Email</th>
              <th>Perimeter (Site / Dept / Team)</th>
              <th>Assigned Roles</th>
              <th>Security & 2FA Status</th>
              <th>Password Status</th>
              <th>Consent Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  Loading user records...
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No user accounts found matching current filters.
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{user.username}</div>
                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#818cf8' }}>
                      {user.employee_id || 'NO-ID'}
                    </div>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                      {user.first_name || user.last_name ? `${user.first_name} ${user.last_name}` : '-'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email || 'No email'}</div>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.82rem', fontWeight: 500 }}>{getDeptName(user.department)}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {getSiteName(user.site)} • {getTeamName(user.team)}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {user.roles && user.roles.length > 0 ? (
                        user.roles.map((r) => (
                          <span key={r} className="badge badge-indigo" style={{ fontSize: '0.7rem' }}>
                            {r}
                          </span>
                        ))
                      ) : (
                        <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                          No roles assigned
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {user.is_payroll_authorized ? (
                        <span className="badge badge-rose" style={{ fontSize: '0.7rem' }}>
                          <Lock size={10} /> Payroll Authorized
                        </span>
                      ) : (
                        <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                          Standard HR Access
                        </span>
                      )}
                      {user.two_factor_enabled ? (
                        <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                          <CheckCircle2 size={10} /> 2FA Active
                        </span>
                      ) : (
                        <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                          2FA Inactive
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    {user.must_change_password ? (
                      <span className="badge badge-rose" style={{ fontSize: '0.7rem' }}>
                        <KeyRound size={10} /> Change Required
                      </span>
                    ) : (
                      <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                        <CheckCircle2 size={10} /> Password Active
                      </span>
                    )}
                  </td>
                  <td>
                    {user.data_processing_consent ? (
                      <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                        <CheckCircle2 size={10} /> Consented
                      </span>
                    ) : (
                      <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                        Pending
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '8px', borderRadius: '8px' }}>
                  <UserPlus size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Create Individual Account</h3>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Enforces unique credentials, perimeter attachment, and mandatory first-login password change.
                  </p>
                </div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowCreateModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateUser}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {createError && (
                  <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', border: '1px solid var(--rose-border)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertCircle size={16} />
                    <span>{createError}</span>
                  </div>
                )}
                {createSuccess && (
                  <div style={{ padding: '10px 14px', background: 'var(--emerald-bg)', border: '1px solid var(--emerald-border)', color: 'var(--emerald-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={16} />
                    <span>User created successfully! Audit log entry recorded.</span>
                  </div>
                )}

                <div className="grid-2">
                  <div className="form-group">
                    <label>Username *</label>
                    <input
                      type="text"
                      className="input"
                      required
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      placeholder="e.g. jdoe"
                    />
                  </div>
                  <div className="form-group">
                    <label>Employee Matricule ID</label>
                    <input
                      type="text"
                      className="input"
                      value={formData.employee_id}
                      onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                      placeholder="e.g. EMP-042"
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>First Name</label>
                    <input
                      type="text"
                      className="input"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Last Name</label>
                    <input
                      type="text"
                      className="input"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Email Address</label>
                    <input
                      type="email"
                      className="input"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="name@hrms-enterprise.com"
                    />
                  </div>
                  <div className="form-group">
                    <label>Initial Temporary Password *</label>
                    <input
                      type="password"
                      className="input"
                      required
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="Min 10 chars, uppercase, digit, symbol"
                    />
                  </div>
                </div>

                <div className="grid-3">
                  <div className="form-group">
                    <label>Site</label>
                    <select
                      className="select"
                      value={formData.site}
                      onChange={(e) => setFormData({ ...formData, site: e.target.value })}
                    >
                      <option value="">Select Site...</option>
                      {sites.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Department</label>
                    <select
                      className="select"
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    >
                      <option value="">Select Dept...</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Team</label>
                    <select
                      className="select"
                      value={formData.team}
                      onChange={(e) => setFormData({ ...formData, team: e.target.value })}
                    >
                      <option value="">Select Team...</option>
                      {teams.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: 'rgba(244, 63, 94, 0.08)', borderRadius: '8px', border: '1px solid var(--rose-border)' }}>
                  <input
                    type="checkbox"
                    id="payrollAuthCheck"
                    className="matrix-check"
                    checked={formData.is_payroll_authorized}
                    onChange={(e) => setFormData({ ...formData, is_payroll_authorized: e.target.checked })}
                  />
                  <label htmlFor="payrollAuthCheck" style={{ color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.82rem' }}>
                    <strong>Enable Payroll Authorization</strong> — Grants access to salary records. Requires 2FA verification.
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

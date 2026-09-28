import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  History,
  ShieldCheck,
  Search,
  Download,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  FileCode,
  Laptop,
  Globe,
  Clock,
  User,
  Lock,
} from 'lucide-react';

const AUDIT_ACTIONS = [
  { key: '', label: 'All Actions' },
  { key: 'create', label: 'Create' },
  { key: 'update', label: 'Update / Modify' },
  { key: 'delete', label: 'Delete' },
  { key: 'validate', label: 'Validate / Approve' },
  { key: 'print', label: 'Print' },
  { key: 'export', label: 'Export' },
  { key: 'login_success', label: 'Login Success' },
  { key: 'login_failure', label: 'Login Failure' },
  { key: 'logout', label: 'Logout' },
  { key: 'password_change', label: 'Password Change' },
  { key: 'access_denied', label: 'Access Denied' },
  { key: 'account_locked', label: 'Account Locked' },
];

const MODULE_OPTIONS = [
  { key: '', label: 'All Modules' },
  { key: 'employees', label: 'Employees' },
  { key: 'payroll', label: 'Payroll' },
  { key: 'leave', label: 'Leave' },
  { key: 'time_attendance', label: 'Time Attendance' },
  { key: 'admin', label: 'Admin / Security' },
  { key: 'audit', label: 'Audit Trail' },
  { key: 'documents', label: 'Documents' },
];

export default function AuditTrailTab() {
  const { hasPermission } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const canConsultAudit = hasPermission('audit', 'consult');
  const canExportAudit = hasPermission('audit', 'export');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (actionFilter) params.action = actionFilter;
      if (moduleFilter) params.module = moduleFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await apiClient.get('/audit-log/', { params });
      const data = res.data;
      setLogs(data.results || (Array.isArray(data) ? data : []));
    } catch (err) {
      console.error('Failed to fetch audit log:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [actionFilter, moduleFilter, dateFrom, dateTo]);

  const handleExportCSV = async () => {
    try {
      const params = {};
      if (actionFilter) params.action = actionFilter;
      if (moduleFilter) params.module = moduleFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const response = await apiClient.get('/audit-log/export/', {
        params,
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit_trail_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export audit logs. Permission denied.');
    }
  };

  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (log.user_display && log.user_display.toLowerCase().includes(query)) ||
      (log.username_snapshot && log.username_snapshot.toLowerCase().includes(query)) ||
      (log.object_type && log.object_type.toLowerCase().includes(query)) ||
      (log.object_repr && log.object_repr.toLowerCase().includes(query)) ||
      (log.notes && log.notes.toLowerCase().includes(query)) ||
      (log.ip_address && log.ip_address.toLowerCase().includes(query))
    );
  });

  const getActionBadgeClass = (action) => {
    if (action.includes('login_success') || action === 'validate') return 'badge-emerald';
    if (action.includes('fail') || action.includes('denied') || action.includes('locked') || action === 'delete')
      return 'badge-rose';
    if (action === 'export' || action === 'print') return 'badge-amber';
    return 'badge-indigo';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <History size={20} color="#38bdf8" /> Immutable Audit Trail & Compliance Log
            </div>
            <div className="card-subtitle">
              Append-only cryptographic security trail. Modifications and deletions are permanently prohibited at database model layer.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchLogs}>
              <RefreshCw size={14} /> Refresh
            </button>
            {canExportAudit && (
              <button className="btn btn-primary" onClick={handleExportCSV}>
                <Download size={14} /> Export CSV Audit Record
              </button>
            )}
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 220px', position: 'relative' }}>
            <input
              type="text"
              className="input"
              placeholder="Search user, IP, notes, target..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '34px' }}
            />
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '12px', color: 'var(--text-muted)' }} />
          </div>

          <div style={{ width: '180px' }}>
            <select className="select" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
              {AUDIT_ACTIONS.map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ width: '180px' }}>
            <select className="select" value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}>
              {MODULE_OPTIONS.map((m) => (
                <option key={m.key} value={m.key}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="date"
              className="input"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              title="From date"
              style={{ width: '140px' }}
            />
            <span style={{ color: 'var(--text-muted)' }}>—</span>
            <input
              type="date"
              className="input"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              title="To date"
              style={{ width: '140px' }}
            />
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Module</th>
              <th>Actor / Account</th>
              <th>Target Object</th>
              <th>Origin IP & Host</th>
              <th>Notes / Details</th>
              <th style={{ textAlign: 'center' }}>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  Loading immutable audit events...
                </td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No audit log entries matching filters.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => {
                const isExpanded = expandedId === log.id;
                const hasDiff = log.previous_value || log.new_value;

                return (
                  <React.Fragment key={log.id}>
                    <tr
                      style={{ cursor: hasDiff ? 'pointer' : 'default' }}
                      onClick={() => hasDiff && setExpandedId(isExpanded ? null : log.id)}
                    >
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td>
                        <span className={`badge ${getActionBadgeClass(log.action)}`}>{log.action}</span>
                      </td>
                      <td>
                        {log.module ? (
                          <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                            {log.module}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>
                          {log.user_display || log.username_snapshot || 'System / Unauth'}
                        </div>
                        {log.user && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>UID: {log.user}</div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                          {log.object_repr || log.object_type || '—'}
                        </div>
                        {log.object_id && (
                          <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                            ID: {log.object_id}
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                          {log.ip_address || '127.0.0.1'}
                        </div>
                        {log.machine && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {log.machine}
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{log.notes || '—'}</div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {hasDiff ? (
                          <button
                            className="btn btn-outline btn-sm"
                            style={{ padding: '3px 8px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedId(isExpanded ? null : log.id);
                            }}
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Diff
                          </button>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>—</span>
                        )}
                      </td>
                    </tr>

                    {/* Expandable JSON Snapshot Diff */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} style={{ padding: '16px 20px', background: 'rgba(0, 0, 0, 0.4)' }}>
                          <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileCode size={16} color="#818cf8" />
                            <strong style={{ fontSize: '0.82rem', color: '#fff' }}>
                              Audit Value Snapshot Comparison
                            </strong>
                          </div>

                          <div className="diff-container">
                            <div className="diff-box">
                              <div className="diff-header" style={{ color: 'var(--rose-text)' }}>
                                Previous State (Before)
                              </div>
                              <pre style={{ margin: 0, color: 'var(--text-secondary)' }}>
                                {log.previous_value ? JSON.stringify(log.previous_value, null, 2) : 'null (None / Created)'}
                              </pre>
                            </div>

                            <div className="diff-box">
                              <div className="diff-header" style={{ color: 'var(--emerald-text)' }}>
                                New State (After)
                              </div>
                              <pre style={{ margin: 0, color: 'var(--text-secondary)' }}>
                                {log.new_value ? JSON.stringify(log.new_value, null, 2) : 'null (Deleted)'}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

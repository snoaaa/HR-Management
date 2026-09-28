import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  Lock,
  Unlock,
  ShieldAlert,
  ShieldCheck,
  DollarSign,
  Download,
  Printer,
  Plus,
  Edit2,
  RefreshCw,
  FileSpreadsheet,
  AlertCircle,
  Eye,
  CheckCircle2,
} from 'lucide-react';
import TwoFactorModal from './TwoFactorModal';

export default function SalaryVaultTab() {
  const { currentUser, hasPermission, twoFactorVerified, refreshUser } = useAuth();
  const [records, setRecords] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState(null); // null, 403, 401
  const [errorMessage, setErrorMessage] = useState('');
  const [show2FAModal, setShow2FAModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [printedRecord, setPrintedRecord] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    employee: '',
    base_salary: '',
    currency: 'XAF',
    effective_date: new Date().toISOString().split('T')[0],
    notes: '',
  });
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const isPayrollAuthorized = currentUser?.is_payroll_authorized;
  const hasPayrollPermission = hasPermission('payroll', 'consult');
  const needs2FA = (currentUser?.requires_two_factor || isPayrollAuthorized) && !twoFactorVerified;

  const fetchSalaryRecords = async () => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage('');

    try {
      const [salaryRes, usersRes] = await Promise.all([
        apiClient.get('/salary-records/'),
        apiClient.get('/users/'),
      ]);
      const sData = salaryRes.data;
      setRecords(sData.results || (Array.isArray(sData) ? sData : []));

      const uData = usersRes.data;
      setUsers(uData.results || (Array.isArray(uData) ? uData : []));
    } catch (err) {
      const status = err.response?.status;
      setErrorStatus(status || 500);
      setErrorMessage(err.response?.data?.detail || 'Access restricted to authorized payroll officers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSalaryRecords();
  }, [twoFactorVerified]);

  const handleCreateSalary = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      await apiClient.post('/salary-records/', {
        employee: parseInt(formData.employee),
        base_salary: parseFloat(formData.base_salary),
        currency: formData.currency,
        effective_date: formData.effective_date,
        notes: formData.notes,
      });

      setShowCreateModal(false);
      setFormData({
        employee: '',
        base_salary: '',
        currency: 'XAF',
        effective_date: new Date().toISOString().split('T')[0],
        notes: '',
      });
      fetchSalaryRecords();
    } catch (err) {
      setFormError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to record compensation.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await apiClient.get('/salary-records/export/', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'salary_records.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export salary records. Permission denied.');
    }
  };

  const handlePrintRecord = async (id) => {
    try {
      const res = await apiClient.get(`/salary-records/${id}/print/`);
      setPrintedRecord(res.data);
    } catch (err) {
      alert('Failed to generate print statement. Permission denied.');
    }
  };

  const getUserDisplay = (empId) => {
    const u = users.find((x) => x.id === empId);
    if (!u) return `Employee #${empId}`;
    return `${u.first_name || ''} ${u.last_name || ''} (${u.username})`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <Lock size={20} color="#f43f5e" /> Confidential Salary & Compensation Vault
            </div>
            <div className="card-subtitle">
              Strictly protected compensation records. Requires explicit payroll authorization flag and active 2FA.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchSalaryRecords}>
              <RefreshCw size={14} /> Refresh
            </button>
            {errorStatus === null && (
              <>
                <button className="btn btn-secondary" onClick={handleExportCSV}>
                  <Download size={14} /> Export CSV (Audited)
                </button>
                <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                  <Plus size={16} /> New Salary Entry
                </button>
              </>
            )}
          </div>
        </div>

        {/* Security Gates Status Bar */}
        <div
          style={{
            marginTop: '20px',
            padding: '12px 16px',
            background: 'var(--bg-input)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Gate 1 (Role Grant):</span>
              {hasPayrollPermission ? (
                <span className="badge badge-emerald">
                  <CheckCircle2 size={12} /> PAYROLL:consult Granted
                </span>
              ) : (
                <span className="badge badge-rose">Missing Permission</span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Gate 2 (Payroll Flag):</span>
              {isPayrollAuthorized ? (
                <span className="badge badge-emerald">
                  <CheckCircle2 size={12} /> is_payroll_authorized = True
                </span>
              ) : (
                <span className="badge badge-rose">Individual Flag False</span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Gate 3 (2FA Verification):</span>
              {twoFactorVerified ? (
                <span className="badge badge-emerald">
                  <CheckCircle2 size={12} /> 2FA Verified in Session
                </span>
              ) : (
                <span className="badge badge-amber">2FA Unverified</span>
              )}
            </div>
          </div>

          {!twoFactorVerified && isPayrollAuthorized && (
            <button className="btn btn-primary btn-sm" onClick={() => setShow2FAModal(true)}>
              <Unlock size={14} /> Verify 2FA to Unlock Vault
            </button>
          )}
        </div>
      </div>

      {/* Access Denied or 2FA Required State */}
      {errorStatus !== null ? (
        <div
          className="card"
          style={{
            padding: '48px 32px',
            textAlign: 'center',
            background: 'linear-gradient(180deg, rgba(244, 63, 94, 0.08) 0%, transparent 100%)',
            border: '1px solid var(--rose-border)',
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: 'rgba(244, 63, 94, 0.15)',
              color: '#fb7185',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <Lock size={32} />
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
            Salary Data Access Restricted
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '560px', margin: '0 auto 24px' }}>
            {errorMessage}
            <br />
            Department Managers and standard staff are isolated from salary figures by default to prevent leakage.
          </p>

          <div style={{ display: 'inline-flex', gap: '12px' }}>
            {isPayrollAuthorized && !twoFactorVerified ? (
              <button className="btn btn-primary" onClick={() => setShow2FAModal(true)}>
                <Unlock size={16} /> Authenticate with 2FA
              </button>
            ) : (
              <div className="badge badge-amber" style={{ padding: '8px 16px', fontSize: '0.82rem' }}>
                <ShieldAlert size={14} /> Switch to <strong>hr_manager</strong> or <strong>payroll_officer</strong> account to test.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Salary Records Table */
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Base Monthly Remuneration</th>
                <th>Effective Date</th>
                <th>Classification & Notes</th>
                <th>Last Modified</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Loading confidential salary records...
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No salary records in your perimeter.
                  </td>
                </tr>
              ) : (
                records.map((rec) => (
                  <tr key={rec.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{getUserDisplay(rec.employee)}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Employee ID: {rec.employee}</div>
                    </td>
                    <td>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.05rem', fontWeight: 700, color: '#34d399' }}>
                        {parseFloat(rec.base_salary).toLocaleString()} {rec.currency}
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-cyan">{rec.effective_date}</span>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{rec.notes || '—'}</div>
                    </td>
                    <td style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {new Date(rec.updated_at || rec.created_at).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => handlePrintRecord(rec.id)}
                        title="Print statement (Audited)"
                      >
                        <Printer size={14} /> Print
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Print Statement Modal */}
      {printedRecord && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '540px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Printer size={20} color="#6366f1" />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Salary Certificate / Decision</h3>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Print request has been automatically registered to the audit trail.
                  </p>
                </div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setPrintedRecord(null)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div
                style={{
                  background: '#fff',
                  color: '#111827',
                  padding: '24px',
                  borderRadius: '8px',
                  fontFamily: 'serif',
                }}
              >
                <div style={{ textAlign: 'center', borderBottom: '2px solid #111827', paddingBottom: '12px', marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '1.1rem', margin: 0 }}>HR MANAGEMENT SYSTEM</h4>
                  <p style={{ fontSize: '0.75rem', color: '#4b5563', margin: '4px 0 0' }}>CONFIDENTIAL REMUNERATION STATEMENT</p>
                </div>

                <div style={{ fontSize: '0.85rem', lineHeight: '1.8' }}>
                  <p><strong>Employee:</strong> {getUserDisplay(printedRecord.employee)}</p>
                  <p><strong>Monthly Base Salary:</strong> {parseFloat(printedRecord.base_salary).toLocaleString()} {printedRecord.currency}</p>
                  <p><strong>Effective Date:</strong> {printedRecord.effective_date}</p>
                  <p><strong>Notes:</strong> {printedRecord.notes || 'Official Remuneration'}</p>
                  <p style={{ marginTop: '16px', fontSize: '0.75rem', color: '#6b7280' }}>
                    Document Generated: {new Date().toLocaleString()} by {currentUser?.username}
                  </p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setPrintedRecord(null)}>
                Close
              </button>
              <button className="btn btn-primary" onClick={() => window.print()}>
                Send to Printer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Salary Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Plus size={20} color="#6366f1" />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Record Compensation</h3>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowCreateModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSalary}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {formError && (
                  <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem' }}>
                    {formError}
                  </div>
                )}

                <div className="form-group">
                  <label>Select Employee</label>
                  <select
                    className="select"
                    required
                    value={formData.employee}
                    onChange={(e) => setFormData({ ...formData, employee: e.target.value })}
                  >
                    <option value="">Select an employee...</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.username} ({u.first_name} {u.last_name || ''})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Base Salary Amount</label>
                    <input
                      type="number"
                      step="0.01"
                      className="input"
                      required
                      value={formData.base_salary}
                      onChange={(e) => setFormData({ ...formData, base_salary: e.target.value })}
                      placeholder="e.g. 1200000"
                    />
                  </div>
                  <div className="form-group">
                    <label>Currency</label>
                    <select
                      className="select"
                      value={formData.currency}
                      onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                    >
                      <option value="XAF">XAF (FCFA)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="USD">USD ($)</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label>Effective Date</label>
                  <input
                    type="date"
                    className="input"
                    required
                    value={formData.effective_date}
                    onChange={(e) => setFormData({ ...formData, effective_date: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Classification / Remuneration Notes</label>
                  <input
                    type="text"
                    className="input"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="e.g. Annual contractual adjustment"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save & Audit Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2FA Modal */}
      <TwoFactorModal isOpen={show2FAModal} onClose={() => setShow2FAModal(false)} />
    </div>
  );
}

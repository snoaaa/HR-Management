import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import {
  ShieldAlert,
  FileCheck,
  Send,
  CheckCircle2,
  Clock,
  User,
  Info,
  Calendar,
  AlertCircle,
  RefreshCw,
  FolderLock,
} from 'lucide-react';

export default function PrivacyGdprTab() {
  const { currentUser, hasPermission, refreshUser } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);

  // New Request Form
  const [requestType, setRequestType] = useState('access');
  const [details, setDetails] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Resolution Form
  const [resolutionStatus, setResolutionStatus] = useState('completed');
  const [resolutionNotes, setResolutionNotes] = useState('');

  const canResolve = hasPermission('employees', 'validate') || currentUser?.is_superuser;

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/data-subject-requests/');
      const data = res.data;
      setRequests(data.results || (Array.isArray(data) ? data : []));
    } catch (err) {
      console.error('Failed to fetch data subject requests:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post('/data-subject-requests/', {
        request_type: requestType,
        details,
      });
      setShowSubmitModal(false);
      setDetails('');
      fetchRequests();
    } catch (err) {
      alert('Failed to submit data subject request.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveRequest = async (e) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setSubmitting(true);
    try {
      await apiClient.post(`/data-subject-requests/${selectedRequest.id}/resolve/`, {
        status: resolutionStatus,
        resolution_notes: resolutionNotes,
      });
      setSelectedRequest(null);
      setResolutionNotes('');
      fetchRequests();
    } catch (err) {
      alert('Failed to resolve request.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <FolderLock size={20} color="#06b6d4" /> Personal Data Protection & Subject Rights
            </div>
            <div className="card-subtitle">
              Data privacy compliance: Purpose specification, data minimisation, retention schedules, and rights of access & rectification.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchRequests}>
              <RefreshCw size={14} /> Refresh
            </button>
            <button className="btn btn-primary" onClick={() => setShowSubmitModal(true)}>
              <Send size={16} /> Submit Subject Request
            </button>
          </div>
        </div>
      </div>

      {/* Employee Personal Privacy Card */}
      <div className="card" style={{ background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%)', border: '1px solid rgba(6, 182, 212, 0.25)' }}>
        <div className="card-title" style={{ fontSize: '1rem', marginBottom: '12px' }}>
          <Info size={18} color="#22d3ee" /> Your Data Privacy Profile ({currentUser?.username})
        </div>

        <div className="grid-3" style={{ gap: '16px' }}>
          <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
              Specified Processing Purpose
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
              {currentUser?.processing_purpose || 'Human resources administration, payroll calculation, legal and tax compliance.'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
              Legal Data Retention Period
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
              {currentUser?.data_retention_until || '10 Years Post-Termination'}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Statutory accounting & employment archive rule
            </div>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
              Processing Consent Status
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
              <span className="badge badge-emerald">
                <CheckCircle2 size={12} /> Active Consent Registered
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Data Subject Requests Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <FileCheck size={18} color="#6366f1" /> Exercise of Rights (Consultation & Rectification Requests)
            </div>
            <div className="card-subtitle">
              Audited workflow tracking requests for access to records or data corrections.
            </div>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Employee</th>
                <th>Right Type</th>
                <th>Details & Justification</th>
                <th>Submission Date</th>
                <th>Status</th>
                <th>Handled By / Notes</th>
                {canResolve && <th style={{ textAlign: 'right' }}>Action</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Loading privacy requests...
                  </td>
                </tr>
              ) : requests.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No data subject requests recorded.
                  </td>
                </tr>
              ) : (
                requests.map((req) => (
                  <tr key={req.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#818cf8' }}>
                      #REQ-{req.id}
                    </td>
                    <td>
                      <strong>Employee #{req.employee}</strong>
                    </td>
                    <td>
                      <span className={`badge ${req.request_type === 'access' ? 'badge-cyan' : 'badge-purple'}`}>
                        {req.request_type === 'access' ? 'Right of Access' : 'Right of Rectification'}
                      </span>
                    </td>
                    <td style={{ maxWidth: '280px' }}>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>{req.details}</div>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(req.requested_at).toLocaleString()}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          req.status === 'completed'
                            ? 'badge-emerald'
                            : req.status === 'rejected'
                            ? 'badge-rose'
                            : 'badge-amber'
                        }`}
                      >
                        {req.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {req.resolution_notes || '—'}
                      </div>
                      {req.handled_at && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          Resolved: {new Date(req.handled_at).toLocaleDateString()}
                        </div>
                      )}
                    </td>
                    {canResolve && (
                      <td style={{ textAlign: 'right' }}>
                        {req.status === 'pending' || req.status === 'in_progress' ? (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => {
                              setSelectedRequest(req);
                              setResolutionNotes('');
                            }}
                          >
                            Resolve
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Closed</span>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submit Request Modal */}
      {showSubmitModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Send size={20} color="#06b6d4" />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Exercise Data Privacy Right</h3>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Submit a formal request to consult or rectify your personal HR data.
                  </p>
                </div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowSubmitModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitRequest}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div className="form-group">
                  <label>Type of Right</label>
                  <select
                    className="select"
                    value={requestType}
                    onChange={(e) => setRequestType(e.target.value)}
                  >
                    <option value="access">Right of Access (Consult full employee record & export)</option>
                    <option value="rectification">Right of Rectification (Correct inaccurate personal details)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Request Details / Items to Consult or Correct</label>
                  <textarea
                    className="textarea"
                    rows={4}
                    required
                    value={details}
                    onChange={(e) => setDetails(e.target.value)}
                    placeholder="Specify the exact personal data or document you wish to inspect or correct..."
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSubmitModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting || !details}>
                  {submitting ? 'Submitting...' : 'Send Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resolve Request Modal */}
      {selectedRequest && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileCheck size={20} color="#6366f1" />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Resolve Request #REQ-{selectedRequest.id}
                </h3>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setSelectedRequest(null)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleResolveRequest}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '8px', fontSize: '0.82rem' }}>
                  <strong>Request:</strong> {selectedRequest.details}
                </div>

                <div className="form-group">
                  <label>Decision Status</label>
                  <select
                    className="select"
                    value={resolutionStatus}
                    onChange={(e) => setResolutionStatus(e.target.value)}
                  >
                    <option value="completed">Completed (Data delivered / rectified)</option>
                    <option value="in_progress">In Progress (Under review)</option>
                    <option value="rejected">Rejected (Not legally applicable)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Resolution Notes (Audited)</label>
                  <textarea
                    className="textarea"
                    rows={3}
                    required
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    placeholder="Explain actions taken to fulfill this subject request..."
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setSelectedRequest(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Resolving...' : 'Confirm Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

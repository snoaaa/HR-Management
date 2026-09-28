import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { KeyRound, ShieldAlert, CheckCircle2, XCircle } from 'lucide-react';

export default function PasswordChangeModal({ isOpen, isForced = false, onClose }) {
  const { changePassword, currentUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  // Validation checks
  const hasMinLength = newPassword.length >= 10;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSpecial = /[^A-Za-z0-9]/.test(newPassword);
  const passwordsMatch = newPassword === confirmPassword && newPassword !== '';

  const isValid = hasMinLength && hasUpper && hasLower && hasDigit && hasSpecial && passwordsMatch;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValid) return;
    setLoading(true);
    setError(null);

    const res = await changePassword(currentPassword, newPassword);
    setLoading(false);

    if (res.success) {
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        if (onClose) onClose();
      }, 1200);
    } else {
      setError(Array.isArray(res.error) ? res.error.join(' ') : res.error);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '8px', borderRadius: '8px' }}>
              <KeyRound size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                {isForced ? 'Mandatory Password Change' : 'Change Your Password'}
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {isForced
                  ? 'First connection security policy requires changing default temporary credentials.'
                  : 'Update your personal credentials according to security policy.'}
              </p>
            </div>
          </div>
          {!isForced && (
            <button className="btn btn-outline btn-sm" onClick={onClose}>
              ✕
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {error && (
              <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', border: '1px solid var(--rose-border)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={16} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div style={{ padding: '10px 14px', background: 'var(--emerald-bg)', border: '1px solid var(--emerald-border)', color: 'var(--emerald-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} />
                <span>Password successfully changed and audit entry recorded!</span>
              </div>
            )}

            <div className="form-group">
              <label>Current Password</label>
              <input
                type="password"
                className="input"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </div>

            <div className="form-group">
              <label>New Password</label>
              <input
                type="password"
                className="input"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter strong new password"
              />
            </div>

            <div className="form-group">
              <label>Confirm New Password</label>
              <input
                type="password"
                className="input"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-type new password"
              />
            </div>

            {/* Policy Checklist */}
            <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Password Policy Checklist
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasMinLength ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {hasMinLength ? <CheckCircle2 size={14} /> : <XCircle size={14} />} Minimum 10 characters
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasUpper ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {hasUpper ? <CheckCircle2 size={14} /> : <XCircle size={14} />} 1 Uppercase letter
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasLower ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {hasLower ? <CheckCircle2 size={14} /> : <XCircle size={14} />} 1 Lowercase letter
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasDigit ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {hasDigit ? <CheckCircle2 size={14} /> : <XCircle size={14} />} 1 Numeric digit
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasSpecial ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {hasSpecial ? <CheckCircle2 size={14} /> : <XCircle size={14} />} 1 Special character
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordsMatch ? 'var(--emerald-text)' : 'var(--text-muted)' }}>
                  {passwordsMatch ? <CheckCircle2 size={14} /> : <XCircle size={14} />} Passwords match
                </div>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            {!isForced && (
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
            )}
            <button type="submit" className="btn btn-primary" disabled={!isValid || loading}>
              {loading ? 'Updating...' : 'Set New Password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

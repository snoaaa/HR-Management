import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, QrCode, RefreshCw, CheckCircle2, AlertCircle, Copy, Key } from 'lucide-react';
import { generateTOTP } from '../utils/totp';

export default function TwoFactorModal({ isOpen, onClose }) {
  const { setup2FA, verify2FA, currentUser, refreshUser } = useAuth();
  const [secret, setSecret] = useState(currentUser?.two_factor_secret || 'JBSWY3DPEHPK3PXP');
  const [code, setCode] = useState('');
  const [simulatedCode, setSimulatedCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    // Load or generate 2FA secret
    const init2FA = async () => {
      if (!currentUser?.two_factor_enabled && !currentUser?.two_factor_secret) {
        const res = await setup2FA();
        if (res.success && res.data.secret) {
          setSecret(res.data.secret);
        }
      }
    };
    init2FA();
  }, [isOpen, currentUser]);

  // Continuously calculate current TOTP for easy testing
  useEffect(() => {
    if (!secret) return;
    const updateSimulatedOTP = async () => {
      const otp = await generateTOTP(secret);
      setSimulatedCode(otp);
    };
    updateSimulatedOTP();
    const timer = setInterval(updateSimulatedOTP, 5000);
    return () => clearInterval(timer);
  }, [secret]);

  if (!isOpen) return null;

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!code || code.length < 6) return;
    setLoading(true);
    setError(null);

    const res = await verify2FA(code);
    setLoading(false);

    if (res.success) {
      setSuccess(true);
      await refreshUser();
      setTimeout(() => {
        setSuccess(false);
        if (onClose) onClose();
      }, 1000);
    } else {
      setError(res.error);
    }
  };

  const copySecret = () => {
    navigator.clipboard.writeText(secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const useVirtualCode = () => {
    setCode(simulatedCode);
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ maxWidth: '500px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '8px', borderRadius: '8px' }}>
              <ShieldCheck size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Two-Factor Authentication</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Required for profiles with access to confidential payroll and compensation data.
              </p>
            </div>
          </div>
          <button className="btn btn-outline btn-sm" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleVerify}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {error && (
              <div style={{ padding: '10px 14px', background: 'var(--rose-bg)', border: '1px solid var(--rose-border)', color: 'var(--rose-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div style={{ padding: '10px 14px', background: 'var(--emerald-bg)', border: '1px solid var(--emerald-border)', color: 'var(--emerald-text)', borderRadius: '8px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} />
                <span>Second factor verified! Session unlocked for payroll data.</span>
              </div>
            )}

            {/* Secret key card */}
            <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  TOTP Secret Key (Base32)
                </span>
                <button type="button" onClick={copySecret} className="btn btn-outline btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem' }}>
                  <Copy size={12} /> {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#a5b4fc', letterSpacing: '0.1em', wordBreak: 'break-all' }}>
                {secret}
              </div>
            </div>

            {/* Live Virtual TOTP generator helper */}
            <div style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', padding: '14px', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#818cf8', fontWeight: 600 }}>
                    ⚡ Built-in Authenticator Generator
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Current 6-digit code for this secret:
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8', letterSpacing: '0.15em' }}>
                    {simulatedCode}
                  </span>
                  <button type="button" onClick={useVirtualCode} className="btn btn-primary btn-sm">
                    Use Code
                  </button>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label>Enter 6-digit Verification Code</label>
              <input
                type="text"
                className="input input-mono"
                maxLength={8}
                required
                value={code}
                onChange={(e) => setCode(e.target.value.trim())}
                placeholder="e.g. 123456"
                style={{ fontSize: '1.1rem', letterSpacing: '0.2em', textAlign: 'center' }}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !code}>
              {loading ? 'Verifying...' : 'Verify & Unlock'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

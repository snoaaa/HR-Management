import React, { useState } from 'react';
import { useAuth, DEMO_USERS } from '../context/AuthContext';
import {
  ShieldCheck,
  Lock,
  User,
  AlertCircle,
  Sparkles,
  Building2,
  KeyRound,
  GraduationCap,
} from 'lucide-react';

export default function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    setError(null);

    const res = await login(username, password);
    setLoading(false);

    if (!res.success) {
      if (res.status === 423) {
        setError('Account temporarily locked due to repeated failed login attempts.');
      } else {
        setError(res.error || 'Invalid credentials.');
      }
    }
  };

  const handleDemoSelect = (u) => {
    setUsername(u.username);
    setPassword(u.password);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'radial-gradient(circle at 50% 20%, rgba(99, 102, 241, 0.15) 0%, rgba(11, 15, 25, 1) 70%)',
      }}
    >
      <div style={{ width: '100%', maxWidth: '460px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Brand Title */}
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #6366f1, #3b82f6)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
              marginBottom: '14px',
            }}
          >
            <ShieldCheck size={32} />
          </div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
            HR Management System
          </h1>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Enterprise HRMS Portal — Security & Administration
          </p>
        </div>

        {/* Login Card */}
        <div className="card card-glass" style={{ padding: '30px' }}>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>Individual Authentication</h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Dedicated credentials, password complexity and lockout policies enforced.
            </p>
          </div>

          {error && (
            <div
              style={{
                padding: '12px 14px',
                background: 'var(--rose-bg)',
                border: '1px solid var(--rose-border)',
                color: 'var(--rose-text)',
                borderRadius: '8px',
                fontSize: '0.82rem',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Individual Username</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="input"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. admin, hr_manager, employee_alice"
                  style={{ paddingLeft: '36px' }}
                />
                <User size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="password"
                  className="input"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  style={{ paddingLeft: '36px' }}
                />
                <Lock size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            >
              {loading ? 'Authenticating...' : 'Sign In to Portal'}
            </button>
          </form>

          {/* Quick Demo Switcher Selection */}
          <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ⚡ Quick Select Test Profile
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {DEMO_USERS.map((u) => (
                <button
                  key={u.username}
                  type="button"
                  onClick={() => handleDemoSelect(u)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: username === u.username ? 'rgba(99, 102, 241, 0.2)' : 'var(--bg-input)',
                    border: `1px solid ${username === u.username ? '#6366f1' : 'var(--border-subtle)'}`,
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'var(--transition)',
                  }}
                >
                  <div>
                    <strong style={{ color: username === u.username ? '#a5b4fc' : '#fff' }}>{u.label}</strong>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Role: {u.role}</div>
                  </div>
                  <span className="badge badge-indigo" style={{ fontSize: '0.65rem' }}>
                    {u.username}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Human Resources Management System (HRMS) • Enterprise Security Portal
        </div>
      </div>
    </div>
  );
}

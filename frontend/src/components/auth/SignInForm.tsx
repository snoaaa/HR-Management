import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { EyeCloseIcon, EyeIcon } from "@/icons";

export default function SignInForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // BN-176: second step of the login when the second factor is active.
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState("");

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = challenge
        ? await api.post("auth/2fa/verify/", { challenge, code })
        : await api.post("auth/login/", { username, password });
      if (response.data.two_factor_required) {
        setChallenge(response.data.challenge);
        return;
      }
      const { access, refresh, user } = response.data;
      login(access, refresh, user);
      toast.success(`Welcome back, ${user.first_name || user.username}!`);
      const from = location.state?.from?.pathname || "/";
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid credentials or server error.");
      if (err.response?.data?.detail?.includes("expired")) setChallenge(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col justify-center">
      <div className="mx-auto w-full max-w-sm animate-fade-in">
        <div className="mb-8">
          <h1 className="text-[28px] font-bold tracking-tight text-primary-c">{challenge ? "Check your phone" : "Welcome back"}</h1>
          <p className="mt-2 text-sm text-secondary-c">
            {challenge ? "Enter the 6-digit code shown by your authenticator application." : "Sign in to your HR workspace with your personal account."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <div className="error-banner">{error}</div>}
          {challenge ? (
            <label className="block">
              <span className="field-label">Code of your authenticator application</span>
              <input
                className="input-field mono !min-h-12 text-center text-lg tracking-[0.4em]"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                autoFocus
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                required
              />
              <button type="button" className="btn-ghost mt-2" onClick={() => { setChallenge(null); setCode(""); }}>
                Use another account
              </button>
            </label>
          ) : (
          <>
          <label className="block">
            <span className="field-label">Username</span>
            <input
              className="input-field !min-h-12"
              placeholder="e.g. jean.dupont"
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="field-label">Password</span>
            <span className="relative block">
              <input
                className="input-field !min-h-12 pe-11"
                type={showPassword ? "text" : "password"}
                placeholder="Your password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-e-3 top-1/2 -translate-y-1/2"
                aria-label={showPassword ? "Hide the password" : "Show the password"}
              >
                {showPassword ? (
                  <EyeIcon className="size-5 fill-gray-500 dark:fill-gray-400" />
                ) : (
                  <EyeCloseIcon className="size-5 fill-gray-500 dark:fill-gray-400" />
                )}
              </button>
            </span>
          </label>
          </>
          )}
          <button type="submit" className="btn-primary btn-lg w-full" disabled={loading}>
            {loading ? "Signing in…" : challenge ? "Verify and sign in" : "Sign in"}
          </button>
          <p className="text-center text-[13px] text-muted-c">
            Forgot your password? Ask your HR department or the administrator to reset it.
          </p>
          <p className="text-center text-xs text-muted-c">
            For your security, the session closes automatically after a period of inactivity.
          </p>
        </form>
      </div>
    </div>
  );
}

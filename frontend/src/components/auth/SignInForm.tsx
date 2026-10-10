import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { LogoMark } from "@/components/brand/Logo";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { EyeCloseIcon, EyeIcon } from "@/icons";

export default function SignInForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await api.post("auth/login/", { username, password });
      const { access, refresh, user } = response.data;
      login(access, refresh, user);
      toast.success(`Welcome back, ${user.first_name || user.username}!`);
      const from = location.state?.from?.pathname || "/";
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid credentials or server error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col justify-center">
      <div className="mx-auto w-full max-w-sm animate-fade-in">
        <div className="mb-8 text-center">
          <div className="mb-5 hidden justify-center lg:flex">
            <LogoMark size={64} />
          </div>
          <h1 className="text-2xl font-bold text-primary-c">Sign in</h1>
          <p className="mt-1 text-sm text-secondary-c">Access your HR workspace with your personal account.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <div className="error-banner">{error}</div>}
          <label className="block">
            <span className="field-label">Username</span>
            <input
              className="input-field py-2.5"
              placeholder="e.g. jdoe"
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
                className="input-field py-2.5 pe-11"
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
          <button type="submit" className="btn-primary w-full py-2.5" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-center text-xs text-muted-c">
            Individual accounts only. Your session closes automatically after a period of inactivity.
          </p>
        </form>
      </div>
    </div>
  );
}

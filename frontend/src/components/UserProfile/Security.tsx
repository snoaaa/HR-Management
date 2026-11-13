import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import { useApiItem } from "@/components/kit/hooks";
import { Badge, Banner, Field, Modal } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

/** BN-174 password change and BN-176 second authentication factor. */
export default function Security() {
  const toast = useToast();
  const { data: twoFactor, reload } = useApiItem<{ enabled: boolean; secret: string; uri: string }>("auth/2fa/setup/");
  const [code, setCode] = useState("");
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [passwords, setPasswords] = useState({ old_password: "", new_password: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);

  const activate = async () => {
    try {
      await api.post("auth/2fa/setup/", { code });
      toast.success("Second factor activated: it will be asked at each sign-in.");
      setCode("");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  const deactivate = async () => {
    try {
      await api.delete("auth/2fa/setup/", { data: { code } });
      toast.success("Second factor deactivated.");
      setCode("");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  const changePassword = async () => {
    setError(null);
    if (passwords.new_password !== passwords.confirm) return setError("The two new passwords are different.");
    try {
      const res = await api.post("auth/change-password/", { old_password: passwords.old_password, new_password: passwords.new_password });
      localStorage.setItem("access_token", res.data.access);
      localStorage.setItem("refresh_token", res.data.refresh);
      toast.success("Password changed.");
      setPasswordOpen(false);
      setPasswords({ old_password: "", new_password: "", confirm: "" });
    } catch (err) {
      setError(apiError(err));
    }
  };

  return (
    <div className="card mb-6 p-5 lg:p-6">
      <h4 className="mb-4 text-lg font-semibold text-primary-c">Security</h4>
      <div className="flex flex-col justify-between gap-4 border-b pb-4 sm:flex-row sm:items-center" style={{ borderColor: "var(--border-color)" }}>
        <div>
          <span className="mb-1 block font-medium text-primary-c">Password</span>
          <p className="text-sm text-secondary-c">At least 8 characters with upper and lower case letters, a digit and a symbol.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => setPasswordOpen(true)}>Change the password</button>
      </div>
      <div className="pt-4">
        <span className="mb-1 flex items-center gap-2 font-medium text-primary-c">
          Two-factor authentication {twoFactor?.enabled ? <Badge tone="green">Active</Badge> : <Badge>Inactive</Badge>}
        </span>
        <p className="mb-3 text-sm text-secondary-c">A 6-digit code from an authenticator application (Google Authenticator, Microsoft Authenticator, FreeOTP…) is asked at each sign-in.</p>
        {twoFactor && !twoFactor.enabled && (
          <div className="space-y-2 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--border-color)" }}>
            <p>1. In your authenticator application, add an account with this key:</p>
            <p className="mono break-all rounded bg-brand-50 px-2 py-1 text-primary-c dark:bg-white/5">{twoFactor.secret}</p>
            <p>or, on your phone, <a className="text-brand-600 underline" href={twoFactor.uri}>open this link</a>.</p>
            <p>2. Type the code displayed by the application:</p>
          </div>
        )}
        {twoFactor && (
          <div className="mt-3 flex flex-wrap gap-2">
            <input className="input-field mono w-36 tracking-widest" inputMode="numeric" maxLength={6} placeholder="000000" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
            {twoFactor.enabled ? (
              <button type="button" className="btn-danger" disabled={code.length !== 6} onClick={deactivate}>Deactivate</button>
            ) : (
              <button type="button" className="btn-primary" disabled={code.length !== 6} onClick={activate}>Activate</button>
            )}
          </div>
        )}
      </div>
      <Modal open={passwordOpen} title="Change the password" onClose={() => setPasswordOpen(false)} size="sm"
        footer={<button type="button" className="btn-primary" onClick={changePassword}>Change</button>}>
        <div className="space-y-3">
          {error && <Banner tone="error">{error}</Banner>}
          <Field label="Current password"><input type="password" className="input-field" value={passwords.old_password} onChange={(e) => setPasswords({ ...passwords, old_password: e.target.value })} /></Field>
          <Field label="New password"><input type="password" className="input-field" value={passwords.new_password} onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} /></Field>
          <Field label="Confirm the new password"><input type="password" className="input-field" value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} /></Field>
        </div>
      </Modal>
    </div>
  );
}

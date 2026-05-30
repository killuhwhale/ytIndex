import { useMutation } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/auth";

function errorMessage(error: unknown) {
  if (typeof error === "object" && error && "response" in error) {
    const detail = (error as { response?: { data?: { detail?: string; non_field_errors?: string[]; password?: string[] } } }).response?.data;
    return detail?.detail ?? detail?.non_field_errors?.[0] ?? detail?.password?.[0] ?? "Password reset failed.";
  }
  return "Password reset failed.";
}

export function PasswordResetConfirmPage() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";
  const mutation = useMutation({ mutationFn: () => confirmPasswordReset(uid, token, password) });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 py-10">
      <section className="w-full max-w-md border bg-white p-6 shadow-sm">
        <div className="mb-6">
          <Link to="/" className="text-xl font-semibold">VideoRecall</Link>
          <p className="mt-2 text-sm text-zinc-600">Choose a new password for your account.</p>
        </div>
        {!uid || !token ? (
          <p className="text-sm text-red-700">This reset link is missing required fields.</p>
        ) : (
          <form className="space-y-4" onSubmit={submit}>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">New password</span>
              <input className="w-full border px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="new-password" />
            </label>
            {mutation.error ? <p className="text-sm text-red-700">{errorMessage(mutation.error)}</p> : null}
            {mutation.data ? <p className="text-sm text-green-700">{mutation.data.detail} <Link className="text-blue-700" to="/login">Log in</Link></p> : null}
            <button className="inline-flex w-full items-center justify-center gap-2 bg-zinc-950 px-4 py-2 text-white disabled:opacity-60" disabled={mutation.isPending || !password}>
              <KeyRound size={16} /> Reset password
            </button>
          </form>
        )}
      </section>
    </main>
  );
}

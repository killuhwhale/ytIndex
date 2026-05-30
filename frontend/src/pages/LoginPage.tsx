import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, LogIn, UserPlus } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login, register, requestPasswordReset } from "../api/auth";

type Mode = "login" | "register" | "reset";

function errorMessage(error: unknown) {
  if (typeof error === "object" && error && "response" in error) {
    const detail = (error as { response?: { data?: { detail?: string; non_field_errors?: string[]; email?: string[]; password?: string[] } } }).response?.data;
    return detail?.detail ?? detail?.non_field_errors?.[0] ?? detail?.email?.[0] ?? detail?.password?.[0] ?? "Request failed.";
  }
  return "Request failed.";
}

export function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  const authMutation = useMutation({
    mutationFn: () => mode === "register" ? register(email, password) : login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "me"], data);
      navigate(from, { replace: true });
    }
  });
  const resetMutation = useMutation({ mutationFn: () => requestPasswordReset(email) });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "reset") {
      resetMutation.mutate();
    } else {
      authMutation.mutate();
    }
  }

  const isReset = mode === "reset";
  const pending = authMutation.isPending || resetMutation.isPending;

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 py-10">
      <section className="w-full max-w-md border bg-white p-6 shadow-sm">
        <div className="mb-6">
          <Link to="/" className="text-xl font-semibold">VideoRecall</Link>
          <p className="mt-2 text-sm text-zinc-600">Sign in with an approved email address.</p>
        </div>

        <div className="mb-5 grid grid-cols-3 border text-sm">
          <button className={`px-3 py-2 ${mode === "login" ? "bg-zinc-950 text-white" : "bg-white"}`} onClick={() => setMode("login")} type="button">Login</button>
          <button className={`px-3 py-2 ${mode === "register" ? "bg-zinc-950 text-white" : "bg-white"}`} onClick={() => setMode("register")} type="button">Register</button>
          <button className={`px-3 py-2 ${mode === "reset" ? "bg-zinc-950 text-white" : "bg-white"}`} onClick={() => setMode("reset")} type="button">Reset</button>
        </div>

        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Email</span>
            <input className="w-full border px-3 py-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
          </label>

          {!isReset ? (
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Password</span>
              <input className="w-full border px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete={mode === "register" ? "new-password" : "current-password"} />
            </label>
          ) : null}

          {authMutation.error ? <p className="text-sm text-red-700">{errorMessage(authMutation.error)}</p> : null}
          {resetMutation.error ? <p className="text-sm text-red-700">{errorMessage(resetMutation.error)}</p> : null}
          {resetMutation.data ? <p className="text-sm text-green-700">{resetMutation.data.detail}</p> : null}

          <button className="inline-flex w-full items-center justify-center gap-2 bg-zinc-950 px-4 py-2 text-white disabled:opacity-60" disabled={pending || !email || (!isReset && !password)}>
            {mode === "login" ? <LogIn size={16} /> : mode === "register" ? <UserPlus size={16} /> : <KeyRound size={16} />}
            {mode === "login" ? "Log in" : mode === "register" ? "Create account" : "Send reset link"}
          </button>
        </form>
      </section>
    </main>
  );
}

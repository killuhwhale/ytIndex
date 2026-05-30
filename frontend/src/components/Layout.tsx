import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { getCurrentUser, logout } from "../api/auth";

export function Layout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const auth = useQuery({ queryKey: ["auth", "me"], queryFn: getCurrentUser });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "me"], data);
      queryClient.clear();
      navigate("/login", { replace: true });
    }
  });

  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <NavLink to="/" className="text-xl font-semibold">VideoRecall</NavLink>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/" className="hover:text-blue-700">Dashboard</NavLink>
            <NavLink to="/search" className="hover:text-blue-700">Search</NavLink>
            <span className="hidden text-zinc-500 md:inline">{auth.data?.user?.email}</span>
            <button className="inline-flex items-center gap-1 text-zinc-700 hover:text-blue-700" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
              <LogOut size={15} /> Logout
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

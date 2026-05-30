import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getCurrentUser } from "../api/auth";

type AuthGateProps = {
  children: ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const location = useLocation();
  const auth = useQuery({ queryKey: ["auth", "me"], queryFn: getCurrentUser, retry: false });

  if (auth.isPending) {
    return <div className="p-8 text-sm text-zinc-600">Loading...</div>;
  }

  if (!auth.data?.authenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

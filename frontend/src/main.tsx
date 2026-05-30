import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { AuthGate } from "./components/AuthGate";
import { Layout } from "./components/Layout";
import { BatchDetailPage } from "./pages/BatchDetailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { PasswordResetConfirmPage } from "./pages/PasswordResetConfirmPage";
import { SearchPage } from "./pages/SearchPage";
import { VideoDetailPage } from "./pages/VideoDetailPage";
import "./styles.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/reset-password/confirm" element={<PasswordResetConfirmPage />} />
          <Route element={<AuthGate><Layout /></AuthGate>}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/batches/:id" element={<BatchDetailPage />} />
            <Route path="/videos/:id" element={<VideoDetailPage />} />
            <Route path="*" element={<div className="p-8"><Link to="/">Back to dashboard</Link></div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);

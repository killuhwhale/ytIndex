import { Outlet, NavLink } from "react-router-dom";

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <NavLink to="/" className="text-xl font-semibold">VideoRecall</NavLink>
          <nav className="flex gap-4 text-sm">
            <NavLink to="/" className="hover:text-blue-700">Dashboard</NavLink>
            <NavLink to="/search" className="hover:text-blue-700">Search</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearAuthCookies } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tests", label: "Tests" },
  { href: "/results", label: "Results" },
  { href: "/users", label: "Users" },
];

function hasAccessToken() {
  if (typeof document === "undefined") return false;
  return /(?:^|; )access_token=/.test(document.cookie);
}

export default function NavSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  // Redirect to login if no token is present
  useEffect(() => {
    if (!hasAccessToken()) {
      router.replace("/login");
    }
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleLogout() {
    clearAuthCookies();
    router.push("/login");
  }

  return (
    <aside className="w-56 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <Image src="/icon-64.png" alt="Quizbee" width={32} height={32} className="shrink-0" />
          <span className="text-xl font-bold text-amber-500">Quizbee</span>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-lg text-sm font-medium transition ${
                active
                  ? "bg-amber-50 text-amber-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 py-4 border-t border-gray-100">
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:text-gray-800 rounded-lg hover:bg-gray-50 transition"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

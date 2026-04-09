"use client";

import Link from "next/link";

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link href="/tests" className="bg-white rounded-xl border border-gray-200 p-6 hover:border-amber-300 transition">
          <p className="text-sm text-gray-500 mb-1">Tests</p>
          <p className="text-lg font-semibold text-gray-900">Build & publish →</p>
        </Link>
        <Link href="/results" className="bg-white rounded-xl border border-gray-200 p-6 hover:border-amber-300 transition">
          <p className="text-sm text-gray-500 mb-1">Results</p>
          <p className="text-lg font-semibold text-gray-900">View submissions →</p>
        </Link>
      </div>
    </div>
  );
}

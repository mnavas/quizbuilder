"use client";

import { useParams } from "next/navigation";
import TestForm from "@/components/TestForm";

export default function EditTestPage() {
  const { id } = useParams() as { id: string };
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit Test</h1>
      <TestForm testId={id} />
    </div>
  );
}

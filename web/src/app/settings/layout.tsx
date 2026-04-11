import NavSidebar from "@/components/NavSidebar";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <NavSidebar />
      <main className="flex-1 p-8 bg-gray-50">{children}</main>
    </div>
  );
}

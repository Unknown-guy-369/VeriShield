import { AnalyzerWorkspace } from "@/components/analyzer/analyzer-workspace";
import { AppHeader } from "@/components/app-header";

export default function HomePage() {
  return (
    <>
      <AppHeader />
      <main id="main-content">
        <AnalyzerWorkspace />
      </main>
    </>
  );
}

import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AssessPage } from "./pages/AssessPage";
import { ModelsPage } from "./pages/ModelsPage";
import { NotFound } from "./pages/NotFound";
import { PlansPage } from "./pages/PlansPage";
import { ProgressPage } from "./pages/ProgressPage";
import { ResultPage } from "./pages/ResultPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<AssessPage />} />
        <Route path="plans" element={<PlansPage />} />
        <Route path="plans/:id" element={<ResultPage />} />
        <Route path="plans/:id/progress" element={<ProgressPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

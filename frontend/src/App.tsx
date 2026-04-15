import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Workspace } from "./pages/Workspace";
import { CreateProject } from "./pages/CreateProject";
import { Projects } from "./pages/Projects";
import { Outline } from "./pages/Outline";
import { Chapters } from "./pages/Chapters";
import { Characters } from "./pages/Characters";
import { WorldBuilder } from "./pages/WorldBuilder";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Projects />} />
        <Route path="/create" element={<CreateProject />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/outline" element={<Outline />} />
        <Route path="/chapters" element={<Chapters />} />
        <Route path="/characters" element={<Characters />} />
        <Route path="/world" element={<WorldBuilder />} />
        <Route path="/review" element={<Review />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

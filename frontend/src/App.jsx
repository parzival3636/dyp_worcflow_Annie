import { Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ProjectShell from './pages/ProjectShell';
import Board from './pages/Board';
import Plan from './pages/Plan';
import Graph from './pages/Graph';
import Contributions from './pages/Contributions';
import Activity from './pages/Activity';
import GuideChat from './pages/GuideChat';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />

      <Route path="/p/:code" element={<ProjectShell />}>
        <Route index element={<Board />} />
        <Route path="plan" element={<Plan />} />
        <Route path="graph" element={<Graph />} />
        <Route path="contributions" element={<Contributions />} />
        <Route path="activity" element={<Activity />} />
        <Route path="chat" element={<GuideChat />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

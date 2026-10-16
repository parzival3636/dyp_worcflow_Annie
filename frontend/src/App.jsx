import { Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ProjectShell from './pages/ProjectShell';
import Board from './pages/Board';
import Overview from './pages/Overview';
import Timeline from './pages/Timeline';
import Plan from './pages/Plan';
import Graph from './pages/Graph';
import Contributions from './pages/Contributions';
import Activity from './pages/Activity';
import GuideChat from './pages/GuideChat';
import LeaderPortal from './pages/LeaderPortal';
import GuideOverview from './pages/GuideOverview';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />

      <Route path="/p/:code" element={<ProjectShell />}>
        {/* Team Member Collaborative Workspace */}
        <Route index element={<Board />} />
        <Route path="overview" element={<Overview />} />
        <Route path="timeline" element={<Timeline />} />
        <Route path="plan" element={<Plan />} />
        <Route path="graph" element={<Graph />} />
        <Route path="contributions" element={<Contributions />} />
        <Route path="activity" element={<Activity />} />
        <Route path="chat" element={<GuideChat />} />

        {/* Dedicated Leader Portal */}
        <Route path="lead" element={<LeaderPortal />} />

        {/* Dedicated Guide / Evaluator Overview */}
        <Route path="guide" element={<GuideOverview />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

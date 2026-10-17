import { useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import { initCapacitor } from './lib/capacitor';

import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProjectListPage from './pages/ProjectListPage';
import CreateProjectPage from './pages/CreateProjectPage';
import ProjectSetupPage from './pages/ProjectSetupPage';
import InviteAcceptPage from './pages/InviteAcceptPage';

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

// Annie Verification & GitHub CI Pages
import AnnieDashboardPage from './pages/AnnieDashboardPage';
import AnnieSetupPage from './pages/AnnieSetupPage';
import AnnieTasksPage from './pages/AnnieTasksPage';
import AnnieWebhookLogPage from './pages/AnnieWebhookLogPage';

export default function App() {
  const navigate = useNavigate();

  useEffect(() => {
    initCapacitor(navigate);
  }, [navigate]);

  return (
    <AuthProvider>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#111827',
            color: '#e2e8f0',
            border: '1px solid #1e2d40',
            fontSize: '0.85rem',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/projects" element={<ProjectListPage />} />
        <Route path="/projects/new" element={<CreateProjectPage />} />
        <Route path="/invite/:token" element={<InviteAcceptPage />} />

        {/* Global Annie Routes */}
        <Route path="/annie" element={<AnnieDashboardPage />} />
        <Route path="/annie/setup" element={<AnnieSetupPage />} />
        <Route path="/annie/tasks" element={<AnnieTasksPage />} />
        <Route path="/annie/webhooks" element={<AnnieWebhookLogPage />} />

        {/* Convenient top-level shortcuts for Annie */}
        <Route path="/setup" element={<AnnieSetupPage />} />
        <Route path="/tasks" element={<AnnieTasksPage />} />
        <Route path="/webhooks" element={<AnnieWebhookLogPage />} />

        {/* Dynamic Project Workspace */}
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

          {/* Dedicated Leader Portal & Project Setup */}
          <Route path="lead" element={<LeaderPortal />} />
          <Route path="setup" element={<ProjectSetupPage />} />

          {/* Dedicated Guide / Evaluator Overview */}
          <Route path="guide" element={<GuideOverview />} />

          {/* Annie Verification & GitHub CI within Project */}
          <Route path="annie" element={<AnnieDashboardPage />} />
          <Route path="verify" element={<AnnieTasksPage />} />
          <Route path="webhooks" element={<AnnieWebhookLogPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/projects" replace />} />
      </Routes>
    </AuthProvider>
  );
}

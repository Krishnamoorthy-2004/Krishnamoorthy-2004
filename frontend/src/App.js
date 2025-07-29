import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AuthPage from './components/auth/AuthPage';
import Dashboard from './components/dashboard/Dashboard';
import EmailCompose from './components/email/EmailCompose';
import EmailView from './components/email/EmailView';
import Templates from './components/templates/Templates';
import Campaigns from './components/campaigns/Campaigns';
import Analytics from './components/analytics/Analytics';
import Settings from './components/settings/Settings';
import { AuthProvider, useAuth } from './context/AuthContext';
import { EmailProvider } from './context/EmailContext';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <EmailProvider>
        <Router>
          <div className="App">
            <Toaster position="top-right" />
            <Routes>
              <Route path="/auth" element={<AuthPage />} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/compose" element={<ProtectedRoute><EmailCompose /></ProtectedRoute>} />
              <Route path="/email/:id" element={<ProtectedRoute><EmailView /></ProtectedRoute>} />
              <Route path="/templates" element={<ProtectedRoute><Templates /></ProtectedRoute>} />
              <Route path="/campaigns" element={<ProtectedRoute><Campaigns /></ProtectedRoute>} />
              <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </Router>
      </EmailProvider>
    </AuthProvider>
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/auth" replace />;
}

export default App;
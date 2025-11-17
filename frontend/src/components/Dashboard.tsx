/**
 * Dashboard Component
 * Main dashboard showing user progress and quick actions
 */
'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';

interface UserMetrics {
  topics_studied: number;
  average_skill_level: number;
  total_sessions: number;
  total_time_hours: number;
  current_streak: number;
  topics: Array<{
    topic: string;
    skill_level: number;
    mastery: number;
  }>;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<UserMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingSession, setCreatingSession] = useState(false);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await apiClient.getMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    setCreatingSession(true);
    try {
      const session = await apiClient.createSession(20);
      // Navigate to session page
      window.location.href = `/session/${session.session_id}`;
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please try again.');
    } finally {
      setCreatingSession(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Learning Dashboard</h1>
        <p className="mt-2 text-gray-600">Track your progress and continue learning</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard
          title="Learning Streak"
          value={`${metrics?.current_streak || 0} days`}
          icon="🔥"
          color="orange"
        />
        <StatCard
          title="Topics Studied"
          value={metrics?.topics_studied || 0}
          icon="📚"
          color="blue"
        />
        <StatCard
          title="Total Sessions"
          value={metrics?.total_sessions || 0}
          icon="✅"
          color="green"
        />
        <StatCard
          title="Learning Time"
          value={`${(metrics?.total_time_hours || 0).toFixed(1)}h`}
          icon="⏱️"
          color="purple"
        />
      </div>

      {/* Main Actions */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Ready to Learn?</h2>
        <button
          onClick={handleCreateSession}
          disabled={creatingSession}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {creatingSession ? 'Creating Session...' : 'Start 20-Minute Learning Session'}
        </button>
      </div>

      {/* Topic Progress */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Your Topics</h2>
        {metrics?.topics && metrics.topics.length > 0 ? (
          <div className="space-y-4">
            {metrics.topics.map((topic, index) => (
              <TopicProgressBar
                key={index}
                topic={topic.topic}
                skillLevel={topic.skill_level}
                mastery={topic.mastery}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No topics yet. Start your first learning session!</p>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: any) {
  const colorClasses = {
    orange: 'bg-orange-100 text-orange-800',
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    purple: 'bg-purple-100 text-purple-800',
  };

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="text-3xl mr-4">{icon}</div>
          <div className="flex-1">
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">{value}</dd>
          </div>
        </div>
      </div>
    </div>
  );
}

function TopicProgressBar({ topic, skillLevel, mastery }: any) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">{topic}</span>
        <span className="text-sm text-gray-500">{skillLevel.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-blue-600 h-2.5 rounded-full"
          style={{ width: `${skillLevel}%` }}
        ></div>
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-500">Skill Level</span>
        <span className="text-xs text-gray-500">Mastery: {mastery.toFixed(0)}%</span>
      </div>
    </div>
  );
}

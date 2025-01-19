import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errors = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 20 },  // Ramp up to 20 users
    { duration: '3m', target: 20 },  // Stay at 20 users
    { duration: '1m', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    errors: ['rate<0.1'],            // Error rate must be less than 10%
  },
};

// Environment configuration
const environments = {
  local: 'http://localhost:8080',
  staging: 'https://staging.agent360.example.com',
  production: 'https://agent360.example.com',
};

// Get environment from command line argument or default to local
const baseUrl = environments[__ENV.ENV || 'local'];

// Main test function
export default function () {
  // Test group for API endpoints
  const endpoints = {
    health: `${baseUrl}/health`,
    ready: `${baseUrl}/ready`,
    listAgents: `${baseUrl}/api/v1/agents`,
    getAgent: `${baseUrl}/api/v1/agents/test-agent-1`,
    getAgentTasks: `${baseUrl}/api/v1/agents/test-agent-1/tasks`,
  };

  // Batch API calls
  const responses = http.batch([
    ['GET', endpoints.health],
    ['GET', endpoints.ready],
    ['GET', endpoints.listAgents],
    ['GET', endpoints.getAgent],
    ['GET', endpoints.getAgentTasks],
  ]);

  // Check responses
  responses.forEach((res, index) => {
    const endpoint = Object.keys(endpoints)[index];
    const success = check(res, {
      [`${endpoint} status is 200`]: (r) => r.status === 200,
      [`${endpoint} response time OK`]: (r) => r.timings.duration < 500,
    });
    
    // Record errors
    if (!success) {
      errors.add(1);
      console.log(`Error in ${endpoint}: ${res.status} - ${res.body}`);
    }
  });

  // Simulate user think time
  sleep(1);
}

// Test teardown
export function teardown(data) {
  console.log('Test completed');
}

import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const ahpAPI = {
  // Get AI score for supplier description
  getAIScore: async (description, criterion) => {
    const response = await api.post('/ahp/ai-score', {
      description,
      criterion
    })
    return response.data
  },

  // Calculate AHP scores
  calculateAHPScores: async (data) => {
    const response = await api.post('/ahp/calculate', data)
    return response.data
  }
}

export const optimizationAPI = {
  // Initialize and analyze data
  initializeOptimizer: async (config) => {
    const response = await api.post('/optimization/initialize', config)
    return response.data
  },

  // Run optimization
  runOptimization: async (params) => {
    const response = await api.post('/optimization/run', params)
    return response.data
  },

  // Run optimization with ranking analysis
  runOptimizationWithRanking: async (params) => {
    const response = await api.post('/optimization/run-with-ranking', params)
    return response.data
  },

  // Get solution details
  getSolutionDetails: async (solutionId) => {
    const response = await api.get(`/optimization/solution/${solutionId}`)
    return response.data
  },

  // Export results
  exportResults: async (format = 'csv') => {
    const response = await api.get(`/optimization/export/${format}`, {
      responseType: 'blob'
    })
    return response.data
  },

  // Get ranking analysis
  getRankingAnalysis: async (solutionId) => {
    const response = await api.get(`/optimization/ranking/${solutionId}`)
    return response.data
  }
}

export default api
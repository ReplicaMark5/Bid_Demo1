# Supply Chain Optimizer Architecture

## Overview

This document describes the architecture of the React + FastAPI version of the Supply Chain Optimizer, recreated from the original Streamlit application.

## System Architecture

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐
│                 │   API Calls     │                 │
│  React Frontend │◄──────────────►│ FastAPI Backend │
│  (Port 3000)    │                 │  (Port 8000)    │
│                 │                 │                 │
└─────────────────┘                 └─────────────────┘
                                             │
                                             │ Python
                                             │ Import
                                             ▼
                                    ┌─────────────────┐
                                    │   MOO Optimizer │
                                    │   (CPLEX Core)  │
                                    │                 │
                                    └─────────────────┘
```

## Frontend Architecture (React)

### Component Structure

```
src/
├── components/
│   ├── AHPScoringInterface.jsx     # Phase 1: AHP Scoring
│   └── OptimizationInterface.jsx   # Phase 2: Optimization
├── services/
│   └── api.js                      # API client with axios
├── hooks/                          # Custom React hooks (if needed)
├── utils/                          # Utility functions
├── App.jsx                         # Main app container
└── main.jsx                        # React app entry point
```

### Key Features

1. **Two-Phase Interface**:
   - Phase 1: AHP Supplier Scoring with AI integration
   - Phase 2: Supply Chain Optimization with Pareto front

2. **Interactive Visualizations**:
   - Plotly.js charts for AHP results
   - Interactive Pareto front with click-to-explore
   - Real-time chart updates

3. **State Management**:
   - React hooks for local state
   - Context API for global state (if needed)
   - Session persistence for optimization results

4. **UI Components**:
   - Ant Design for consistent UI
   - Responsive layout with CSS Grid/Flexbox
   - Loading states and error handling

### Data Flow

```
User Input → React Component → API Service → Backend API → Response → State Update → Re-render
```

## Backend Architecture (FastAPI)

### API Structure

```
backend/
├── backend_api.py                  # Main FastAPI application
├── requirements.txt               # Python dependencies
└── .env.example                   # Environment configuration
```

### API Endpoints

#### AHP Scoring
- `POST /api/ahp/ai-score` - AI-powered supplier scoring
- `POST /api/ahp/calculate` - AHP weighted score calculation

#### Optimization
- `POST /api/optimization/initialize` - Data loading and validation
- `POST /api/optimization/run` - Standard ε-constraint optimization
- `POST /api/optimization/run-with-ranking` - Enhanced optimization with ranking
- `GET /api/optimization/solution/{id}` - Solution details
- `GET /api/optimization/export/{format}` - Results export
- `GET /api/optimization/ranking/{id}` - Ranking analysis

#### Utility
- `GET /api/health` - Service health check
- `GET /` - API information

### Core Integration

The backend directly imports and uses the existing MOO optimizer:

```python
from MOO_e_constraint_Dynamic_Bid import SelectiveNAFlexibleEConstraintOptimizer
```

This maintains full compatibility with the original optimization engine while providing a modern API interface.

## Data Flow Architecture

### AHP Scoring Flow

```
1. User enters criteria and suppliers
2. AI service scores supplier descriptions
3. React calculates weighted AHP scores
4. Results stored in frontend state
5. Charts updated with new data
```

### Optimization Flow

```
1. User configures optimization parameters
2. Backend initializes optimizer with Excel data
3. ε-constraint optimization runs
4. Pareto front results returned to frontend
5. Interactive visualization enables solution exploration
6. Detailed analysis available on-demand
```

## Key Technologies

### Frontend Stack
- **React 18** - Component framework
- **Vite** - Build tool and dev server
- **Ant Design** - UI component library
- **Plotly.js** - Interactive charts
- **Axios** - HTTP client
- **Styled Components** - CSS-in-JS (if needed)

### Backend Stack
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Pandas** - Data manipulation
- **NumPy** - Numerical computing
- **CPLEX** - Optimization solver

### External Services
- **GitHub AI** - Supplier scoring (optional)
- **Excel Files** - Data source

## Security Considerations

### CORS Configuration
- Frontend-backend communication secured with CORS
- Only localhost origins allowed in development
- Production deployment requires proper CORS setup

### Data Validation
- Pydantic models validate all API inputs
- File upload restrictions and validation
- Error handling prevents information leakage

### Environment Variables
- Sensitive data (API keys) stored in environment
- Configuration separated from code
- Example environment file provided

## Performance Optimizations

### Frontend
- **Component Optimization**: Proper React hooks usage
- **Chart Performance**: Plotly.js optimized for large datasets
- **API Caching**: Results cached during user session
- **Lazy Loading**: Components loaded as needed

### Backend
- **Memory Management**: Optimizer instances reused
- **Data Caching**: Results cached in memory
- **Async Processing**: FastAPI async support
- **File Handling**: Efficient Excel processing

## Deployment Architecture

### Development
```bash
python run_dev.py  # Starts both servers
```

### Production
```
Frontend: npm run build → Static files → Nginx/Apache
Backend: uvicorn backend_api:app → Reverse proxy → Domain
```

## Error Handling

### Frontend
- Network error handling with retry logic
- Loading states for all async operations
- User-friendly error messages
- Fallback UI for failed operations

### Backend
- Comprehensive exception handling
- Detailed logging for debugging
- Graceful degradation when services unavailable
- Proper HTTP status codes

## Testing Strategy

### Frontend Testing
```bash
# Unit tests for components
npm test

# Integration tests for API calls
npm run test:integration

# E2E tests for full workflows
npm run test:e2e
```

### Backend Testing
```bash
# API endpoint tests
pytest tests/test_api.py

# Optimization logic tests
pytest tests/test_optimization.py

# Integration tests
pytest tests/test_integration.py
```

## Monitoring and Debugging

### Development Tools
- React DevTools for component inspection
- FastAPI automatic documentation at `/docs`
- Browser network tab for API monitoring
- Console logging for debugging

### Production Monitoring
- Application health checks
- Error tracking and logging
- Performance metrics collection
- User analytics (if required)

## Future Enhancements

### Planned Features
1. **Database Integration**: Persistent storage for results
2. **User Authentication**: Multi-user support
3. **Real-time Updates**: WebSocket for live optimization
4. **Advanced Visualizations**: 3D Pareto fronts
5. **Export Formats**: PDF reports, Excel exports
6. **Batch Processing**: Multiple optimization runs
7. **API Rate Limiting**: Production-ready API
8. **Docker Deployment**: Containerized deployment

### Scalability Considerations
- Database for result persistence
- Message queue for long-running optimizations
- Caching layer for frequently accessed data
- Load balancing for multiple instances
- CDN for static assets

This architecture provides a solid foundation for the Supply Chain Optimizer while maintaining the core functionality of the original Streamlit application and enabling future enhancements.
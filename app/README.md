# Supply Chain Optimizer - React + FastAPI

This project recreates the Streamlit-based Supply Chain Optimizer interface in React, with a FastAPI backend serving the optimization results.

## Project Structure

```
app/
├── backend/
│   ├── backend_api.py          # FastAPI server
│   ├── requirements.txt        # Python dependencies
│   └── run_backend.py         # Backend launcher script
├── react/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AHPScoringInterface.jsx
│   │   │   └── OptimizationInterface.jsx
│   │   ├── services/
│   │   │   └── api.js          # API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── README.md
└── run_dev.py                  # Development launcher
```

## Features

### Phase 1: AHP Supplier Scoring
- **Criteria Definition**: Configure evaluation criteria and weights
- **AI-Assisted Scoring**: Get AI-generated scores for supplier descriptions
- **AHP Calculation**: Calculate weighted supplier scores using AHP methodology
- **Visualization**: Interactive charts showing supplier rankings and criteria weights

### Phase 2: Supply Chain Optimization
- **Data Configuration**: Excel file path and sheet configuration
- **ε-Constraint Optimization**: Multi-objective optimization with configurable parameters
- **Pareto Front Visualization**: Interactive Plotly charts showing optimal solutions
- **Solution Analysis**: Detailed breakdown of allocations and rankings
- **Supplier Ranking Analysis**: Advanced ranking analysis with multiple metrics
- **Export Functionality**: Download results in various formats

## Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **CPLEX** (for optimization solver)
- **GitHub Token** (optional, for AI scoring)

## Installation

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd app

# Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install Node.js dependencies
cd react
npm install
cd ..
```

### 2. Environment Setup

Create a `.env` file in the backend directory:

```bash
# backend/.env
GITHUB_TOKEN=your_github_token_here  # Optional for AI scoring
```

### 3. Data Setup

Ensure your Excel data file is accessible and update the default path in the React interface or use the file path input.

## Running the Application

### Option 1: Using the Development Launcher (Recommended)

```bash
# From the app directory
python run_dev.py
```

This will start both the backend and frontend servers:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs

### Option 2: Manual Startup

**Terminal 1 - Backend:**
```bash
cd backend
python backend_api.py
# Or use uvicorn directly:
# uvicorn backend_api:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd react
npm run dev
```

## API Endpoints

### AHP Scoring
- `POST /api/ahp/ai-score` - Get AI-generated supplier scores
- `POST /api/ahp/calculate` - Calculate AHP weighted scores

### Optimization
- `POST /api/optimization/initialize` - Initialize optimizer with data
- `POST /api/optimization/run` - Run standard optimization
- `POST /api/optimization/run-with-ranking` - Run optimization with ranking analysis
- `GET /api/optimization/solution/{id}` - Get solution details
- `GET /api/optimization/export/{format}` - Export results
- `GET /api/optimization/ranking/{id}` - Get ranking analysis

### Utility
- `GET /api/health` - Health check
- `GET /` - API information

## Configuration

### Backend Configuration
- **Port**: 8000 (configurable in `backend_api.py`)
- **CORS**: Enabled for localhost:3000
- **File uploads**: Supported via multipart/form-data

### Frontend Configuration
- **Port**: 3000 (configurable in `vite.config.js`)
- **API Proxy**: Configured to proxy `/api` requests to backend
- **Build**: Production build with `npm run build`

## Data Format

The application expects Excel files with the following sheets:
- **Obj1_Coeff**: Cost coefficients (COC Rebate, DEL Rebate, Cost of Collection, Zone Differentials)
- **Obj2_Coeff**: Supplier scoring data
- **Annual Volumes**: Volume data for each depot

## Advanced Features

### Supplier Ranking Analysis
- **Cost Effectiveness**: Score improvement per cost increase
- **Cost Impact**: Prefer alternatives that reduce cost most
- **Score Impact**: Prefer alternatives that increase score most
- **Combined**: Balanced normalized combination

### ε-Constraint Parameters
- **Number of Points**: 5-400 (recommended: 21)
- **Constraint Type**: Cost or Score constraint
- **Random Seed**: For reproducible results

### AI Integration
- GitHub AI models for supplier performance scoring
- Automatic score generation from text descriptions
- Fallback to default scores if AI unavailable

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill processes on ports 3000 and 8000
   lsof -ti:3000 | xargs kill -9
   lsof -ti:8000 | xargs kill -9
   ```

2. **CPLEX Not Found**
   - Install IBM ILOG CPLEX Optimization Studio
   - Ensure CPLEX Python API is installed

3. **Import Errors**
   - Ensure Python path includes the MOO_e_constraint_Dynamic_Bid module
   - Check all dependencies are installed

4. **CORS Issues**
   - Verify frontend is running on localhost:3000
   - Check CORS configuration in backend

### Development Tips

- Use browser dev tools to monitor API calls
- Check backend logs for optimization errors
- Frontend hot-reloads automatically on changes
- Backend auto-reloads with `--reload` flag

## Performance Optimization

### Backend
- Results are cached in memory during session
- Optimizer instances are reused where possible
- File operations are optimized for large datasets

### Frontend
- Plotly charts are optimized for interactivity
- Large datasets are paginated in tables
- API calls are debounced for better UX

## Deployment

### Development
```bash
python run_dev.py
```

### Production
```bash
# Build frontend
cd react
npm run build

# Serve with production server
cd ../backend
uvicorn backend_api:app --host 0.0.0.0 --port 8000

# Serve built frontend with nginx or similar
```

## Contributing

1. Follow the existing code structure
2. Add proper error handling
3. Update API documentation
4. Test both frontend and backend changes
5. Update this README if needed

## License

This project is part of academic research. Please cite appropriately if used in publications.
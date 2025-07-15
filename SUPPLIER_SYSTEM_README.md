# Supplier Data Submission System

A comprehensive web application that replaces manual Excel file uploads with a modern, database-driven supplier data submission and management system.

## 🚀 Features

### For Suppliers
- **User-friendly form interface** for submitting pricing data
- **Real-time validation** of numeric inputs
- **Depot-specific data submission** with dropdown selection
- **Support for N/A values** when services aren't available
- **Submission history tracking** with status updates
- **Detailed submission view** with approval status

### For Administrators
- **Centralized submission management** with filtering and sorting
- **Approval/rejection workflow** for supplier submissions
- **Data validation dashboard** showing completeness status
- **Supplier and depot management** with creation capabilities
- **Real-time statistics** on submission status
- **Export functionality** for optimizer integration

### For the Optimizer
- **Seamless database integration** with existing SelectiveNAFlexibleEConstraintOptimizer
- **Automatic data format conversion** from SQLite to Excel format
- **Maintains full compatibility** with existing optimization workflows
- **One-click database loading** in the optimization interface

## 📋 System Requirements

### Backend
- Python 3.8+
- FastAPI
- SQLite3
- Pandas
- Pydantic

### Frontend
- React 18+
- Ant Design (antd)
- Axios for API calls

## 🛠️ Installation & Setup

### 1. Backend Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn sqlite3 pandas pydantic

# Navigate to backend directory
cd app/backend

# The database will be created automatically on first run
```

### 2. Frontend Setup

```bash
# Navigate to React directory
cd app/react

# Install dependencies
npm install

# Start development server
npm start
```

### 3. Running the Complete System

Use the provided script to run both backend APIs simultaneously:

```bash
# From the app directory
python run_full_backend.py
```

This will start:
- Main API on port 8000
- Supplier API on port 8001
- Frontend will be available on port 3000

## 💾 Database Schema

The system uses SQLite with the following tables:

### `suppliers`
- `id` (Primary Key)
- `name` (Unique supplier name)
- `email` (Optional contact email)
- `created_at` (Timestamp)

### `depots`
- `id` (Primary Key)
- `name` (Unique depot name)
- `annual_volume` (Annual volume in litres)
- `created_at` (Timestamp)

### `supplier_submissions`
- `id` (Primary Key)
- `supplier_id` (Foreign Key to suppliers)
- `depot_id` (Foreign Key to depots)
- `coc_rebate` (Collection rebate R/L, nullable)
- `cost_of_collection` (Collection cost R/L, nullable)
- `del_rebate` (Delivery rebate R/L, nullable)
- `zone_differential` (Zone differential, required)
- `distance_km` (Distance in km, nullable)
- `status` (pending/approved/rejected)
- `submitted_at` (Timestamp)
- `approved_at` (Timestamp, nullable)
- `approved_by` (Admin name, nullable)

### `supplier_scores`
- `id` (Primary Key)
- `supplier_id` (Foreign Key to suppliers)
- `total_score` (AHP total score)
- `criteria_scores` (JSON string of individual criteria scores)
- `created_at` (Timestamp)

## 🔄 Data Flow

1. **Supplier Submission**: Suppliers log in and submit pricing data through the web form
2. **Admin Review**: Administrators review submissions and approve/reject them
3. **Database Storage**: Approved data is stored in normalized SQLite tables
4. **Optimizer Integration**: The system converts database data to the required Excel format for the optimizer
5. **Optimization**: The optimizer runs using the database-sourced data

## 🎯 Usage Guide

### For Suppliers

1. **Select Your Supplier**: Choose your supplier account from the dropdown
2. **Submit Data**: Use the form to submit pricing data for each depot
3. **Track Progress**: Monitor submission status in the history tab
4. **Handle N/A Values**: Leave fields empty if you can't provide that service

### For Administrators

1. **Review Submissions**: Check the submissions tab for pending approvals
2. **Manage Data**: Use the management tab to add new suppliers/depots
3. **Validate Completeness**: Check the validation tab for data completeness
4. **Export Data**: Use the export functionality to download data for analysis

### For Optimization

1. **Load from Database**: Click "Load from Database" instead of uploading Excel files
2. **Run Optimization**: Use the standard optimization interface
3. **View Results**: Results are displayed in the same format as before

## 🔧 API Endpoints

### Supplier API (Port 8001)

#### Suppliers
- `GET /api/suppliers/` - Get all suppliers
- `POST /api/suppliers/` - Create new supplier
- `GET /api/suppliers/{id}/submissions/` - Get supplier submissions

#### Depots
- `GET /api/depots/` - Get all depots
- `POST /api/depots/` - Create new depot

#### Submissions
- `POST /api/suppliers/submit-data/` - Submit supplier data
- `POST /api/suppliers/submit-bulk-data/` - Submit bulk data
- `GET /api/admin/submissions/` - Get all submissions (admin)
- `POST /api/admin/submissions/approve/` - Approve submission (admin)
- `POST /api/admin/submissions/reject/` - Reject submission (admin)

#### Data Management
- `GET /api/admin/export/optimizer-data/` - Export optimizer-formatted data
- `POST /api/admin/create-temp-excel/` - Create temporary Excel file
- `GET /api/admin/validation/check-data/` - Validate data completeness

### Main API (Port 8000)

#### Existing Endpoints
- All existing optimization endpoints remain unchanged
- New: `POST /api/optimization/initialize-from-db` - Initialize optimizer from database

## 🔄 Data Validation

The system includes comprehensive validation:

### Form Validation
- **Numeric fields**: Automatic validation for rates and costs
- **Required fields**: Zone differential is always required
- **Optional fields**: Handles N/A values gracefully

### Database Validation
- **Unique constraints**: Prevents duplicate supplier-depot combinations
- **Foreign key constraints**: Ensures data integrity
- **Status tracking**: Maintains approval workflow

### Optimizer Validation
- **Completeness check**: Ensures all required data is present
- **Format compliance**: Maintains compatibility with existing optimizer
- **Error handling**: Graceful handling of missing or invalid data

## 📊 Data Export Format

The system automatically converts database data to the format expected by the SelectiveNAFlexibleEConstraintOptimizer:

### Sheet 1: Obj1_Coeff
- Depot, Supplier, COC Rebate(R/L), Cost of Collection (R/L), DEL Rebate(R/L), Zone Differentials, Distance(Km)

### Sheet 2: Obj2_Coeff
- Scoring data with supplier scores from AHP analysis

### Sheet 3: Annual Volumes
- Depot volumes for optimization calculations

## 🛡️ Security Considerations

- **Input validation**: All form inputs are validated both client and server-side
- **SQL injection protection**: Using parameterized queries
- **CORS configuration**: Properly configured for the frontend
- **Error handling**: Comprehensive error handling without exposing sensitive information

## 🚨 Troubleshooting

### Common Issues

1. **Database not found**: The database is created automatically - ensure write permissions
2. **Port conflicts**: Make sure ports 8000 and 8001 are available
3. **CORS errors**: Check that the frontend is running on port 3000
4. **Missing dependencies**: Run `pip install -r requirements.txt`

### Logs

- Backend logs are displayed in the console with prefixes [MAIN-API] and [SUPPLIER-API]
- Frontend errors appear in the browser console
- Database operations are logged in the backend

## 🔮 Future Enhancements

- **User authentication**: Add proper login/logout functionality
- **Role-based access**: Implement supplier and admin role separation
- **Email notifications**: Notify suppliers of approval/rejection
- **Data versioning**: Track changes to submissions over time
- **Audit trail**: Log all administrative actions
- **Bulk upload**: Allow Excel uploads for initial data migration
- **API rate limiting**: Prevent abuse of the submission endpoints

## 📞 Support

For technical issues or questions, please check:
1. The console logs for error messages
2. The browser developer tools for frontend issues
3. The database file permissions
4. The API endpoint documentation above

## 🤝 Contributing

When making changes:
1. Update the database schema in `database.py`
2. Update the API endpoints in `supplier_api.py`
3. Update the frontend components as needed
4. Test the complete workflow from submission to optimization
5. Update this documentation
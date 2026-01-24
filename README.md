# Smart Pantry

A smart and interactive pantry management system powered by AI.

## Features

- 🔐 **Authentication** - Full login and registration system with Supabase.
- 👤 **User Profile** - Personal settings, eating habits, and shopping frequency.
- 🏠 **Main Dashboard** - Central hub with quick access to all features.
- 🛒 **Smart Shopping** - Intelligent shopping list generation with recommendations.
- 🛍️ **Live Shopping** - Real-time tracking while you shop.
- 📄 **Receipt Scanning** - Automated pantry updates via AI receipt analysis.
- 📦 **Pantry Management** - Inventory tracking with visual indicators.
- 📊 **Habits** - Tracking preferences and special events.
- 💰 **Analytics** - Expense analysis and consumption trends.

## Technologies

### Backend
- FastAPI - API server
- Supabase - Database & Authentication
- PostgreSQL - Database

### Frontend
- Next.js 14 - React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- Recharts - Data visualization
- Zustand - State management

## Prerequisites

- **Python 3.9+**: During installation, ensure you check the **"Add Python to PATH"** option.
- **Node.js 18+**: During installation, ensure you check the **"Add to PATH"** option.

## Installation

### 1. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
npm install
```

### 3. Environment Configuration

**⚠️ Important: Every user must create a `.env.local` file in the `FRONT/` directory!**

📖 **Detailed Instructions:** See `FRONT/ENV_SETUP.md`

**Summary:**
1. Create a `.env.local` file in the `FRONT/` folder (not in the root!).
2. Copy the following content:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k

# API
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Update the `.env` file in the root directory for the Backend:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### 4. Running the Application

**Backend:**
```bash
uvicorn app.main:app --reload
```

**Frontend:**
```bash
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Test User

You can use the following credentials to test the system without registering:
- **Username/Email:** `rotembor_test_2000@gmail.com`
- **Password:** `1234`

## Project Structure

```
Smart-Pantry/
├── app/                    # Backend (FastAPI)
│   ├── api/               # API routes
│   ├── services/          # Business logic
│   ├── schemas/           # Pydantic models
│   └── main.py            # FastAPI app
├── src/                   # Frontend (Next.js)
│   ├── app/               # Pages & routes
│   ├── components/        # React components
│   ├── lib/               # Utilities
│   └── store/             # State management
├── data_scheme.sql        # Database schema
└── requirements.txt       # Python dependencies
```

## API Endpoints

### Products
- `GET /api/v1/products` - Get all products
- `POST /api/v1/products` - Create a new product
- `PUT /api/v1/products/{id}` - Update a product
- `DELETE /api/v1/products/{id}` - Delete a product

### Inventory
- `GET /api/v1/inventory?user_id={uuid}` - Get user inventory
- `POST /api/v1/inventory?user_id={uuid}` - Create/Update inventory item
- `PUT /api/v1/inventory/{product_id}?user_id={uuid}` - Update inventory item

### Shopping Lists
- `GET /api/v1/shopping-lists?user_id={uuid}` - Get shopping lists
- `POST /api/v1/shopping-lists?user_id={uuid}` - Create a new list
- `POST /api/v1/shopping-lists/{id}/items` - Add item to list

### Receipts
- `GET /api/v1/receipts?user_id={uuid}` - Get receipts
- `POST /api/v1/receipts?user_id={uuid}` - Create a new receipt

## AI Features (Planned)

The system learns your habits:
- Product consumption rates
- High-consumption days of the week
- Personal shopping style
- Recurring decisions

Natural communication examples:
- "I noticed the coffee is running out 30% faster than usual..."
- "I removed snacks again because you've removed them for 4 weeks in a row..."
- "There's a slight discrepancy: you bought 2 units but they finished faster than expected..."

## Development

### Adding a New Page

1. Create a file in `src/app/[route]/page.tsx`.
2. Use `DashboardLayout` for dashboard pages.
3. Use `useAuthStore` for authentication management.

### Adding an API Endpoint

1. Create a route in `app/api/[resource].py`.
2. Add a service in `app/services/[resource]_service.py`.
3. Add a schema in `app/schemas/[resource].py`.

## Troubleshooting

### PowerShell Script Execution Error
If you encounter an error when trying to activate the virtual environment (`venv\Scripts\activate`):
> "File ... cannot be loaded because running scripts is disabled on this system."

**The Solution:**
Run the following command in PowerShell (as the current user):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## License

MIT

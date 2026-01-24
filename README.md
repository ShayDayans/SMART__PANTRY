# Smart Pantry - Intelligent Pantry Management System

A comprehensive smart pantry management system with AI-powered consumption prediction, shopping list management, recipe generation, and intelligent inventory tracking.

## 🎯 Features

- 🔐 **User Management** -  authentication system with Supabase Auth
- 📦 **Pantry Management** - Track inventory with visual state indicators (FULL/MEDIUM/LOW/EMPTY)
- 🤖 **AI Predictions** - Machine learning model that learns your consumption patterns
- 🛒 **Smart Shopping Lists** - Create and manage shopping lists with AI recommendations
- 🍳 **Recipe Generator** - GPT-powered recipe generation based on available ingredients
- 📊 **Habits Tracking** - Track consumption habits and preferences
- 📄 **Receipt Scanning** - Automatic inventory updates from receipt scanning
- 📈 **Confidence Scoring** - AI confidence metrics for prediction reliability

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework for building APIs
- **Supabase** - Backend-as-a-Service (Database & Authentication)
- **PostgreSQL** - Database (hosted on Supabase)
- **OpenAI GPT** - Recipe generation and receipt processing

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **Zustand** - State management
- **Recharts** - Data visualization

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/) (Make sure to select **"Add Python to PATH"** during installation)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/) (Make sure to select **"Add to PATH"** during installation)
- **npm** (comes with Node.js) or **yarn**
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Supabase Account** - [Sign up for Supabase](https://supabase.com/) (or use existing project credentials)

### Verify Installation

Check that everything is installed correctly:

```bash
# Check Python version
python --version
# Should output: Python 3.8.x or higher

# Check Node.js version
node --version
# Should output: v18.x.x or higher

# Check npm version
npm --version
# Should output: 9.x.x or higher
```

## 🚀 Installation Guide

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd SMART__PANTRY
```

### Step 2: Install Backend Dependencies

1. **Navigate to the project root directory** (where `requirements.txt` is located)

2. **Create a virtual environment** (recommended):

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python packages**:

   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - FastAPI
   - Uvicorn
   - Supabase client
   - Pydantic
   - OpenAI
   - And other dependencies

### Step 3: Install Frontend Dependencies

1. **Navigate to the FRONT directory**:

   ```bash
   cd FRONT
   ```

2. **Install npm packages**:

   ```bash
   npm install
   ```

   This will install:
   - Next.js 14
   - React 18
   - TypeScript
   - Tailwind CSS
   - And other dependencies

3. **Return to project root**:

   ```bash
   cd ..
   ```

### Step 4: Configure Environment Variables

#### Frontend Configuration (`.env.local`)

**⚠️ IMPORTANT: You MUST create this file in the `FRONT/` directory, NOT in the root directory!**

1. **Navigate to the FRONT directory**:

   ```bash
   cd FRONT
   ```

2. **Create `.env.local` file**:

   **Windows (PowerShell):**
   ```powershell
   New-Item -Path ".env.local" -ItemType File
   ```

   **Windows (Command Prompt):**
   ```cmd
   type nul > .env.local
   ```

   **Mac/Linux:**
   ```bash
   touch .env.local
   ```

3. **Open `.env.local` and add the following content**:

   ```env
   # Supabase Configuration
   NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k

   # Backend API URL
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```

   **⚠️ Important Notes:**
   - Copy the API key exactly as shown (every character matters!)
   - The file must be named `.env.local` (with the dot at the beginning)
   - The file must be in the `FRONT/` directory, not the root directory

4. **Verify file location**:

   The file structure should look like this:
   ```
   SMART__PANTRY/
   ├── FRONT/
   │   ├── .env.local  ← HERE!
   │   ├── package.json
   │   └── src/
   ├── app/
   └── requirements.txt
   ```

5. **Return to project root**:

   ```bash
   cd ..
   ```

#### Backend Configuration (`.env`)

1. **Navigate to the project root directory** (where `app/` and `requirements.txt` are located)

2. **Modify the existing `.env` file**:

   Open `.env` and add/update the following content:

   ```env
   # Supabase Configuration
   SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k

   # OpenAI API Key (Optional - for recipe generation and receipt scanning)
   OPENAI_API_KEY=your-openai-api-key-here
   ```

   **Note:** 
   - OpenAI API key is optional but required for recipe generation and receipt scanning features

## ▶️ Running the Application

You need to run **two servers** simultaneously: the Backend API server and the Frontend development server.

### 👤 Test User

You can use the following credentials to test the system without registering:
- **Username/Email:** `rotembor_test_2000@gmail.com`
- **Password:** `1234`

### Terminal 1: Start Backend Server

1. **Navigate to project root** (if not already there):

   ```bash
   cd SMART__PANTRY
   ```

2. **Activate virtual environment** (if using one):

   ```bash
   # Windows
   venv\Scripts\activate

   # Mac/Linux
   source venv/bin/activate
   ```

3. **Start the FastAPI server**:

   ```bash
   uvicorn app.main:app --reload
   ```

   You should see output like:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process
   INFO:     Started server process
   INFO:     Waiting for application startup.
   ```

4. **Verify backend is running**:

   - Open your browser and go to: http://localhost:8000/docs
   - You should see the FastAPI interactive API documentation (Swagger UI)

### Terminal 2: Start Frontend Server

1. **Open a new terminal window/tab**

2. **Navigate to the FRONT directory**:

   ```bash
   cd SMART__PANTRY/FRONT
   ```

3. **Start the Next.js development server**:

   ```bash
   npm run dev
   ```

   You should see output like:
   ```
   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000
   - ready started server on 0.0.0.0:3000
   ```

4. **Verify frontend is running**:

   - Open your browser and go to: http://localhost:3000
   - You should see the login page

## ✅ Verification Checklist

Before using the application, verify that everything is set up correctly:

- [ ] Backend server is running on http://localhost:8000
- [ ] Backend API docs are accessible at http://localhost:8000/docs
- [ ] Frontend server is running on http://localhost:3000
- [ ] Frontend login page loads without errors
- [ ] No console errors in browser (press F12 to check)
- [ ] `.env.local` file exists in `FRONT/` directory
- [ ] `.env` file exists in root directory

## 🎮 Using the Application

1. **Register/Login**:
   - Go to http://localhost:3000/login
   - Create a new account or sign in with existing credentials

2. **Dashboard**:
   - After login, you'll see the main dashboard
   - View statistics and quick actions

3. **Add Products to Pantry**:
   - Click "Pantry" in the navigation
   - Click "Add Product" button
   - Fill in product details and add to inventory

4. **Create Shopping Lists**:
   - Click "Shopping List" in the navigation
   - Create a new shopping list
   - Add items with autocomplete search

5. **Generate Recipes**:
   - Click "Recipes" in the navigation
   - Click "Generate Recipe"
   - Select meal type and preferences
   - Get AI-generated recipes based on your pantry

## 📁 Project Structure

```
SMART__PANTRY/
├── app/                          # Backend (FastAPI)
│   ├── api/                     # API route handlers
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── inventory.py         # Inventory management
│   │   ├── products.py          # Product management
│   │   ├── shopping_lists.py    # Shopping list endpoints
│   │   ├── recipes.py           # Recipe generation
│   │   └── habits.py            # Habits management
│   ├── services/                # Business logic
│   │   ├── predictor_service.py # AI prediction service
│   │   ├── recipe_service.py    # Recipe generation service
│   │   └── ...
│   ├── schemas/                 # Pydantic models
│   ├── core/                    # Core configuration
│   │   ├── config.py           # Settings and environment
│   │   └── dependencies.py     # Dependency injection
│   └── main.py                 # FastAPI application entry point
│
├── FRONT/                       # Frontend (Next.js)
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   │   ├── dashboard/     # Dashboard pages
│   │   │   │   ├── pantry/    # Pantry management
│   │   │   │   ├── shopping/  # Shopping lists
│   │   │   │   ├── recipes/   # Recipe generation
│   │   │   │   └── habits/    # Habits management
│   │   │   └── login/         # Login page
│   │   ├── components/        # React components
│   │   ├── lib/               # Utilities and API clients
│   │   └── store/             # State management (Zustand)
│   ├── .env.local             # Frontend environment variables (YOU CREATE THIS)
│   └── package.json           # Frontend dependencies
│
├── migrations/                 # Database migration scripts
├── data_scheme.sql            # Database schema
├── ema_cycle_predictor.py     # AI prediction model
├── requirements.txt            # Python dependencies
├── .env                       # Backend environment variables (YOU MODIFY THIS)
└── README.md                  # This file
```

## 🔧 Troubleshooting

### PowerShell Script Execution Error
If you encounter an error when trying to activate the virtual environment (`venv\Scripts\activate`):
> "File ... cannot be loaded because running scripts is disabled on this system."

**The Solution:**
Run the following command in PowerShell (as the current user):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Common Issues

#### 1. "Invalid API key" Error

**Problem:** Frontend shows "Invalid API key" error

**Solution:**
- Verify `.env.local` exists in `FRONT/` directory (not root)
- Check that the API key is copied exactly (no extra spaces)
- Clear Next.js cache: `cd FRONT && rm -rf .next` (Mac/Linux) or `cd FRONT && rmdir /s /q .next` (Windows)
- Restart the frontend server

#### 2. Backend Server Won't Start

**Problem:** `uvicorn` command not found or import errors

**Solution:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

#### 3. Frontend Server Won't Start

**Problem:** `next` command not found or npm errors

**Solution:**
- Navigate to `FRONT/` directory: `cd FRONT`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 18+)

#### 4. Database Connection Errors

**Problem:** Cannot connect to Supabase

**Solution:**
- Verify Supabase URL and keys in `.env` and `.env.local`
- Check Supabase project is active
- Verify internet connection

#### 5. Port Already in Use

**Problem:** Port 3000 or 8000 is already in use

**Solution:**
- **For Backend (port 8000):**
  ```bash
  # Find and kill the process
  # Windows
  netstat -ano | findstr :8000
  taskkill /PID <PID> /F
  
  # Mac/Linux
  lsof -ti:8000 | xargs kill
  ```

- **For Frontend (port 3000):**
  ```bash
  # Windows
  netstat -ano | findstr :3000
  taskkill /PID <PID> /F
  
  # Mac/Linux
  lsof -ti:3000 | xargs kill
  ```

#### 6. Module Not Found Errors

**Problem:** Import errors in Python or TypeScript

**Solution:**
- **Python:** Reinstall dependencies: `pip install -r requirements.txt`
- **TypeScript:** Reinstall node modules: `cd FRONT && npm install`

## 📚 Additional Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **Next.js Documentation:** https://nextjs.org/docs
- **Supabase Documentation:** https://supabase.com/docs
- **Tailwind CSS Documentation:** https://tailwindcss.com/docs

## 🔐 Security Notes

- **Never commit `.env` or `.env.local` files to version control**
- These files contain sensitive API keys and should remain local
- The `.gitignore` file should already exclude these files
- If sharing the project, provide instructions for creating these files

## 🆘 Getting Help

If you encounter issues not covered in this guide:

1. Check the browser console (F12) for frontend errors
2. Check the terminal output for backend errors
3. Verify all environment variables are set correctly
4. Ensure both servers are running simultaneously
5. Check that you're using the correct directories for commands

## 📝 Development Notes

- Backend runs on: http://localhost:8000
- Frontend runs on: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- The backend must be running for the frontend to work properly
- Hot reload is enabled for both servers (changes auto-refresh)

## 🎉 You're All Set!

Once both servers are running and you can access the login page, you're ready to use the Smart Pantry system. Start by creating an account and adding your first products to the pantry!

---

**Happy coding! 🚀**

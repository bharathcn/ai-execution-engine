# AI Execution Engine

AI Execution Engine is a productivity system that converts **goals into structured daily execution plans using AI** and helps users focus on **what they should do today**.

Instead of managing long task lists, the system automatically generates and schedules actionable steps for each goal.

---

# 🚀 Features

* AI-generated execution plans
* Daily task focus system
* Multiple goals tracking
* Sequential day-by-day execution
* Unlock next day tasks when ready
* Progress tracking
* Clean minimal UI
* Dockerized full-stack application

---

# 🏗 Architecture

Frontend
Next.js (React)

Backend
FastAPI (Python)

Database
SQLite (can be replaced with Postgres)

AI
OpenAI API

Infrastructure
Docker + Docker Compose

```
Frontend → FastAPI API → Database → OpenAI
```

---

# 📂 Project Structure

```
ai-execution-engine
│
├── ai-execution-backend
│   ├── app
│   │   ├── api
│   │   ├── database
│   │   ├── models
│   │   └── services
│   └── requirements.txt
│
├── ai-execution-frontend
│   ├── app
│   ├── components
│   └── package.json
│
├── ai-execution-infra
│   └── docker-compose.yml
│
└── README.md
```

---

# ⚙️ Environment Setup

Create a `.env` file inside:

```
ai-execution-backend/.env
```

Add your OpenAI key:

```
OPENAI_API_KEY=your_api_key_here
```

---

# 🐳 Running with Docker

Navigate to:

```
ai-execution-infra
```

Run:

```
docker compose up --build
```

---

# 🌐 Application URLs

Frontend

```
http://localhost:3000
```

Backend API

```
http://localhost:8000/docs
```

---

# 🧠 How It Works

1. User creates a goal
2. AI generates a structured plan
3. User approves execution
4. Tasks appear in **Today's Focus**
5. After completing tasks, the next day can be unlocked
6. Progress is tracked automatically

---

# 🛣 Future Roadmap

* User authentication
* Multi-user SaaS platform
* Stripe subscription billing
* AI adaptive planning
* Calendar integration
* Habit analytics
* Goal performance heatmaps

---

# 📜 License

Karkane LLP

---

# 👨‍💻 Author

Bharath C N

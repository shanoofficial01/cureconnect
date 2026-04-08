🏥 CureConnect – Smart Healthcare & Community Platform

CureConnect is an intelligent healthcare web application that combines AI-powered symptom analysis, doctor recommendations, community health tracking, and real-time group communication into one unified platform.

🚀 Features
🤖 AI Symptom Checker
Detects symptoms from user input (text or voice)
Suggests the right medical specialist
Provides confidence score & explanation
Asks follow-up questions for better accuracy
Uses trained ML model (prescripto_model_v2.pkl)
🎤 Voice Assistant (AI Powered)
Convert speech → text using Deepgram API
Convert text → speech for AI responses
Hands-free interaction supported
🏥 Doctor Recommendation System
Suggests doctors based on detected condition
Filter by specialty
Displays:
Ratings
Fees
Location
Hospital
🌍 Community Health Monitoring
Users can report symptoms in their city
Calculates:
Health Score
Disease trends
Symptom trends (hourly)
Prevents spam using:
Duplicate detection
Time-based restriction
📰 Live Health News
Fetches real-time health news using GNews API
Displays latest global healthcare updates
👥 Community Groups (Real-Time Chat)
Create and join health-related groups
Admin approval system
Real-time chat using WebSockets
Supports multi-user communication
🔐 Authentication System
JWT-based authentication
Secure login & registration
Access + Refresh token system
Token rotation for security
🛠️ Tech Stack
Backend
FastAPI
JWT Authentication
WebSockets
Joblib (ML Model)
Pandas
Frontend
HTML, CSS, JavaScript
Chart.js (for analytics graphs)
APIs Used
Deepgram API (voice processing)
GNews API (health news)
📂 Project Structure
CureConnect/
│
├── main.py                  # FastAPI backend
├── app.js                   # Frontend logic
├── index.html               # UI
├── style.css                # Styling
│
├── prescripto_model_v2.pkl  # ML model
├── symptom_list_v2.pkl      # Symptom vocabulary
├── prescripto_db.json       # Database
│
├── .env                     # API keys
├── .env.example             # Sample env file
├── .gitignore               # Ignored files :contentReference[oaicite:2]{index=2}
⚙️ Installation & Setup
1️⃣ Clone Repository
git clone https://github.com/your-username/cureconnect.git
cd cureconnect
2️⃣ Install Backend Dependencies
pip install fastapi uvicorn python-jose passlib pandas joblib requests
3️⃣ Setup Environment Variables

Create .env file:

GNEWS_API_KEY=your_key
DEEPGRAM_API_KEY=your_key

(Example provided in project)

4️⃣ Run Backend Server
python main.py

Server runs at:

http://localhost:8000
5️⃣ Run Frontend
Open index.html in browser
OR
Use Live Server
🔌 API Endpoints
🔐 Authentication
POST /auth/register
POST /auth/login
POST /auth/refresh
🤖 AI Prediction
POST /predict → symptom analysis
🎤 Voice
POST /voice-to-text
POST /text-to-voice
🌍 Community Health
POST /report
GET /city-health/{city}
📰 News
GET /news/health
👨‍⚕️ Doctors
GET /doctors?specialty=
👥 Groups
POST /groups/create
GET /groups/all
POST /groups/request
POST /groups/approve
WebSocket /ws/groups/{group_id}
🧠 How It Works
🔍 Symptom Processing
User inputs symptoms (text/voice)
System:
Cleans text
Extracts symptoms using NLP rules
ML model predicts:
Disease
Severity
Specialist
📊 Community Health Engine
Collects reports from users
Calculates:
Severity score
Health score
Tracks:
Top diseases
Hourly symptom trends
💬 Real-Time Chat
Uses WebSocket connection
Broadcasts messages instantly to group members
🔒 Security Features
Password hashing (PBKDF2)
JWT authentication
Refresh token rotation
API access protection
⚠️ Important Notes
.env file is ignored for security
Model files (.pkl) are large → excluded from Git
Not a replacement for professional medical advice
📌 Future Improvements
Database upgrade (MongoDB / PostgreSQL)
Mobile app version
Advanced ML model
Appointment booking system
Push notifications

👨‍💻 Author
Shano
CureConnect Developer

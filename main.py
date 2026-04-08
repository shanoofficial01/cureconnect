from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import joblib
import pandas as pd
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
import re
from fastapi import HTTPException
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from deepgram import DeepgramClient
import io
from fastapi.responses import Response


def load_local_env(env_path=".env"):
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


load_local_env()


# ----------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------

CONFIG = {
    "MODEL_FILE": "prescripto_model_v2.pkl",
    "VOCAB_FILE": "symptom_list_v2.pkl",
    "DB_FILE": "prescripto_db.json",
    "APP_VERSION": "2.2.0 (Community Upgrade)",
    "DEFAULT_CITY": "Chennai",
    "NEWS_API_URL": "https://gnews.io/api/v4/top-headlines",
    "NEWS_FALLBACK_API_URL": "https://gnews.io/api/v4/search",
    "NEWS_CATEGORY": "health",
    "NEWS_QUERY": "health OR medicine OR public health OR healthcare",
    "NEWS_LANGUAGE": "en",
    "NEWS_COUNTRY": "in",
    "NEWS_MAX_RESULTS": 6
}

# ----------------------------------------------------
# AUTH CONFIGURATION
# ----------------------------------------------------

SECRET_KEY = "super-secret-key-change-this"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ----------------------------------------------------
# PASSWORD HASHING
# ----------------------------------------------------

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

# ----------------------------------------------------
# AUTH SECURITY (JWT BEARER)
# ----------------------------------------------------

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# --- 1. DATA MODELS ---
class SymptomInput(BaseModel):
    symptoms: List[str]
    user_id: Optional[str] = "guest"

class ReportRequest(BaseModel):
    symptoms: List[str]
    city: str
    user_id: Optional[str] = "anonymous"

class Doctor(BaseModel):
    id: str
    name: str
    specialty: str
    hospital: str
    rating: float
    fees: int
    location: str
    gender: str
    image: str

class CreateGroupRequest(BaseModel):
    name: str
    disease_tag: Optional[str] = ""

class ApproveRequest(BaseModel):
    group_id: str
    user_id: str    

class JoinGroupRequest(BaseModel):
    group_id: str

class GroupMessageRequest(BaseModel):
    group_id: str
    message: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"    

# --- 2. DATABASE MANAGER ---
class DatabaseManager:

    def __init__(self, db_file):
        self.db_file = db_file
        self.data = self._load_db()

    # -------------------------
    # CORE DB OPERATIONS
    # -------------------------

    def _load_db(self):
        if not os.path.exists(self.db_file):
            return self._seed_data()
        try:
            with open(self.db_file, "r") as f:
                return json.load(f)
        except:
            return self._seed_data()

    def _save_db(self):
        with open(self.db_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def _seed_data(self):
        seed = {
            "users": {},
            "reports": [],
            "chat_history": {},
            "doctors": [
                {"id": "doc_1", "name": "Dr. Aditi Sharma", "specialty": "dermatologist", "hospital": "Apollo Skin Clinic", "rating": 4.9, "fees": 800, "location": "Chennai Central", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/44.jpg"},
                {"id": "doc_2", "name": "Dr. Raj Malhotra", "specialty": "dermatologist", "hospital": "General Hospital", "rating": 4.5, "fees": 500, "location": "Adyar", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/32.jpg"},
                {"id": "doc_3", "name": "Dr. Arjun Verma", "specialty": "cardiologist", "hospital": "Heart Care Institute", "rating": 5.0, "fees": 1500, "location": "Velachery", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/85.jpg"},
                {"id": "doc_4", "name": "Dr. Priya Singh", "specialty": "cardiologist", "hospital": "Fortis Malar", "rating": 4.7, "fees": 1200, "location": "Mylapore", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/68.jpg"},
                {"id": "doc_5", "name": "Dr. Manoj Gupta", "specialty": "general_physician", "hospital": "Family Health", "rating": 4.3, "fees": 400, "location": "T.Nagar", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/11.jpg"},
                {"id": "doc_6", "name": "Dr. Sneha Patil", "specialty": "general_physician", "hospital": "Kauvery Hospital", "rating": 4.8, "fees": 600, "location": "Anna Nagar", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/90.jpg"},
                {"id": "doc_7", "name": "Dr. Vikram Seth", "specialty": "neurologist", "hospital": "Brain & Spine Center", "rating": 4.9, "fees": 2000, "location": "OMR", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/55.jpg"},
                {"id": "doc_8", "name": "Dr. Meera Krishnan", "specialty": "ent_specialist", "hospital": "MGM Healthcare", "rating": 4.6, "fees": 900, "location": "Aminjikarai", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/52.jpg"},
                {"id": "doc_9", "name": "Dr. Naveen Kumar", "specialty": "orthopedic", "hospital": "MIOT International", "rating": 4.8, "fees": 1400, "location": "Manapakkam", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/61.jpg"},
                {"id": "doc_10", "name": "Dr. Lakshmi Narayanan", "specialty": "pediatrician", "hospital": "Rainbow Children's Hospital", "rating": 4.7, "fees": 950, "location": "Guindy", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/63.jpg"},
                {"id": "doc_11", "name": "Dr. Harish Raman", "specialty": "psychiatrist", "hospital": "Mindwell Clinic", "rating": 4.5, "fees": 1300, "location": "Nungambakkam", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/48.jpg"},
                {"id": "doc_12", "name": "Dr. Divya Subramaniam", "specialty": "gynecologist", "hospital": "Cloudnine Hospital", "rating": 4.9, "fees": 1200, "location": "Teynampet", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/57.jpg"},
                {"id": "doc_13", "name": "Dr. Arun Prakash", "specialty": "pulmonologist", "hospital": "Apollo Hospitals", "rating": 4.6, "fees": 1500, "location": "Greams Road", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/71.jpg"},
                {"id": "doc_14", "name": "Dr. Swetha Iyer", "specialty": "gastroenterologist", "hospital": "SIMS Hospital", "rating": 4.7, "fees": 1600, "location": "Vadapalani", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/73.jpg"},
                {"id": "doc_15", "name": "Dr. Karthik Rajan", "specialty": "ophthalmologist", "hospital": "Dr. Agarwals Eye Hospital", "rating": 4.4, "fees": 850, "location": "Ashok Nagar", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/66.jpg"},
                {"id": "doc_16", "name": "Dr. Ananya Bose", "specialty": "endocrinologist", "hospital": "Kauvery Hospital", "rating": 4.8, "fees": 1700, "location": "Alwarpet", "gender": "Female", "image": "https://randomuser.me/api/portraits/women/81.jpg"},
                {"id": "doc_17", "name": "Dr. Ritesh Menon", "specialty": "urologist", "hospital": "Gleneagles HealthCity", "rating": 4.5, "fees": 1450, "location": "Perumbakkam", "gender": "Male", "image": "https://randomuser.me/api/portraits/men/76.jpg"}
            ],
            "groups": [],
            "group_messages": [],
            "group_requests": [],
            "news": []
        }

        with open(self.db_file, "w") as f:
            json.dump(seed, f, indent=4)

        return seed

    # -------------------------
    # REPORTS
    # -------------------------

    def add_report(self, report):
        self.data["reports"].append(report)
        self._save_db()

    def get_reports_by_city(self, city):
        return [
            r for r in self.data["reports"]
            if r["city"].lower() == city.lower()
        ]

    # -------------------------
    # CHAT
    # -------------------------

    def log_chat(self, user_id, message, sender):
        if user_id not in self.data["chat_history"]:
            self.data["chat_history"][user_id] = []

        self.data["chat_history"][user_id].append({
            "sender": sender,
            "text": message,
            "timestamp": datetime.now().isoformat()
        })

        self._save_db()

    # -------------------------
    # DOCTORS
    # -------------------------

    def get_doctors(self):
        return self.data["doctors"]

    # -------------------------
    # GROUPS (PHASE 2)
    # -------------------------

    def create_group(self, group):
        self.data["groups"].append(group)
        self._save_db()

    def get_all_groups(self):
        return self.data["groups"]

    def add_member_to_group(self, group_id, user_id):
        for g in self.data["groups"]:
            if g["id"] == group_id:
                if user_id not in g["members"]:
                    g["members"].append(user_id)
        self._save_db()

    def get_user_groups(self, user_id):
        return [
            g for g in self.data["groups"]
            if user_id in g["members"]
        ]

    # -------------------------
    # GROUP MESSAGES
    # -------------------------

    def add_group_message(self, msg):
        self.data["group_messages"].append(msg)
        self._save_db()

    def get_group_messages(self, group_id):
        return [
            m for m in self.data["group_messages"]
            if m["group_id"] == group_id
        ]

    # -------------------------
    # JOIN REQUEST SYSTEM
    # -------------------------

    def create_join_request(self, request):
        self.data["group_requests"].append(request)
        self._save_db()

    def get_group_requests(self, group_id):
        return [
            r for r in self.data["group_requests"]
            if r["group_id"] == group_id and r["status"] == "pending"
        ]

    def approve_request(self, group_id, user_id):
        # Update request status
        for r in self.data["group_requests"]:
            if r["group_id"] == group_id and r["user_id"] == user_id:
                r["status"] = "approved"

        # Add user to group members
        for g in self.data["groups"]:
            if g["id"] == group_id:
                if user_id not in g["members"]:
                    g["members"].append(user_id)

        self._save_db()


# Initialize DB
db = DatabaseManager(CONFIG["DB_FILE"])

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.data["users"].get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return username



class ConnectionManager:
    def __init__(self):
        self.active_connections = {}  # {group_id: [websockets]}

    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: str):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)

    async def broadcast(self, group_id: str, message: dict):
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_json(message)

manager = ConnectionManager()


# --- 3. APP INIT ---
app = FastAPI(title="CureConnect API", version=CONFIG["APP_VERSION"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "").strip()

deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)

# --- 4. AI MODEL ---
model = None
vocab = []
# --- AI CONVERSATION MEMORY ---
ai_memory = {}
ai_question_state = {}



if os.path.exists(CONFIG["MODEL_FILE"]):
    model = joblib.load(CONFIG["MODEL_FILE"])
    vocab = joblib.load(CONFIG["VOCAB_FILE"])
    print(f"✅ AI Brain Loaded. Vocabulary Size: {len(vocab)}")



def extract_symptoms_from_text(text: str):

    text = text.lower()

    # remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    words = text.split()

    detected = []

    # -------------------------
    # 1️⃣ Detect trained vocab symptoms
    # -------------------------
    for symptom in vocab:

        symptom_words = symptom.replace("_", " ").split()

        if all(word in words for word in symptom_words):
            detected.append(symptom)

    # -------------------------
    # 2️⃣ Natural language mapping
    # -------------------------
    phrase_map = {

    # Body pain
    "body pain": "body_pain",
    "whole body pain": "body_pain",
    "pain all over body": "body_pain",
    "my body hurts": "body_pain",
    "muscle pain": "body_pain",
    "body aches": "body_pain",

    # Fever
    "high temperature": "fever",
    "burning up": "fever",
    "very hot": "fever",
    "body feels hot": "fever",
    "temperature is high": "fever",

    # Headache
    "head hurts": "headache",
    "pain in head": "headache",
    "head is hurting": "headache",
    "pressure in my head": "headache",

    # Chest pain
    "chest hurts": "chest_pain",
    "pain in chest": "chest_pain",
    "tight chest": "chest_pain",
    "pressure in chest": "chest_pain",

    # Breathing
    "can't breathe": "breathlessness",
    "difficulty breathing": "breathlessness",
    "shortness of breath": "breathlessness",
    "breathing problem": "breathlessness",
    "hard to breathe": "breathlessness",

    # Fatigue
    "feel weak": "fatigue",
    "very tired": "fatigue",
    "low energy": "fatigue",
    "exhausted": "fatigue",
    "extremely tired": "fatigue",

    # Dizziness
    "feeling dizzy": "dizziness",
    "room spinning": "dizziness",
    "light headed": "dizziness",
    "feeling faint": "dizziness",

    # Vomiting
    "throwing up": "vomiting",
    "feel like vomiting": "nausea",
    "want to vomit": "nausea",
    "sick to stomach": "nausea",

    # Stomach pain
    "stomach hurts": "abdominal_pain",
    "pain in stomach": "abdominal_pain",
    "belly pain": "abdominal_pain",

    # chills
    "feeling cold": "chills",
    "cold shivering": "chills",

    # Skin
    "skin is itchy": "itching",
    "itchy skin": "itching",
    "red skin spots": "skin_rash",
    "red rash": "skin_rash",

    # Cold / flu
    "runny nose": "runny_nose",
    "blocked nose": "runny_nose",
    "nose running": "runny_nose",
    "sneezing a lot": "sneezing",

    # Throat
    "throat hurts": "sore_throat",
    "pain in throat": "sore_throat",
    "difficulty swallowing": "sore_throat",

    # Back pain
    "back hurts": "back_pain",
    "pain in back": "back_pain",
    "lower back pain": "back_pain",

    # Neck
    "neck hurts": "neck_pain",
    "pain in neck": "neck_pain",

    # Vision
    "blurry vision": "blurred_vision",
    "cannot see clearly": "blurred_vision",
    "vision is blurry": "blurred_vision",

    # Ear
    "ear hurts": "ear_pain",
    "pain in ear": "ear_pain",

    # Appetite
    "not hungry": "loss_of_appetite",
    "lost appetite": "loss_of_appetite",

    # Sleep
    "can't sleep": "insomnia",
    "trouble sleeping": "insomnia",

    # Anxiety
    "feel anxious": "anxiety",
    "feeling nervous": "anxiety",
    "panic feeling": "anxiety",

    # Depression
    "feel depressed": "depression",
    "feel very sad": "depression",
}
    for phrase, symptom in phrase_map.items():
        if phrase in text:
            detected.append(symptom)

    # -------------------------
    # 3️⃣ Basic keyword fallback
    # -------------------------
    basic_symptoms = [

    "fever",
    "headache",
    "cough",
    "dizziness",
    "nausea",
    "vomiting",
    "chest pain",
    "breathlessness",
    "fatigue",
    "itching",
    "rash",

    "abdominal pain",
    "diarrhea",
    "constipation",
    "joint pain",
    "back pain",
    "neck pain",

    "runny nose",
    "sneezing",
    "sore throat",

    "blurred vision",
    "eye pain",
    "ear pain",

    "swelling",
    "weight loss",
    "weight gain",

    "loss of appetite",
    "insomnia",

    "anxiety",
    "depression",

    "body pain",
    "muscle pain",
    "body ache"
]

    for s in basic_symptoms:
        if s in text:
            detected.append(s.replace(" ", "_"))

    return list(set(detected))

# ----------------------------------------------------
# 🔥 STEP 1: COMMUNITY HEALTH CALCULATION ENGINE
# ----------------------------------------------------

def calculate_city_health(city: str):

    now = datetime.now()
    last_24h = now - timedelta(hours=24)

    reports = [
        r for r in db.get_reports_by_city(city)
        if datetime.fromisoformat(r["timestamp"]) >= last_24h
    ]

   
    disease_count = {}
    severity_score = 0
    valid_reports = 0

    # 🔥 NEW: symptom tracking
    symptom_count = {}
    symptom_hourly = {}

    for report in reports:

        # 🔥 CLEAN + VALIDATE
        symptoms = [
            s.lower().strip().replace(" ", "_")
            for s in report["symptoms"]
            if s.strip() != ""
        ]

        if not symptoms:
            continue

        # 🔥 EXTRACT HOUR (0–23)
        hour = datetime.fromisoformat(report["timestamp"]).hour

        # 🔥 TRACK SYMPTOMS
        for s in symptoms:

            # total count
            if s not in symptom_count:
                symptom_count[s] = 0
            symptom_count[s] += 1

            # hourly init (24 hours)
            if s not in symptom_hourly:
                symptom_hourly[s] = [0] * 24

            symptom_hourly[s][hour] += 1

        # Predict disease
        result = predict_disease(symptoms)

        disease = result["disease"]
        severity = result["severity"]

        if disease == "Unknown":
            continue

        valid_reports += 1

        if disease not in disease_count:
            disease_count[disease] = 0
        disease_count[disease] += 1

        if severity == "mild":
            severity_score += 1
        elif severity == "moderate":
            severity_score += 2
        elif severity == "severe":
            severity_score += 4
        elif severity == "critical":
            severity_score += 6

    # 🟢 No valid reports
    if valid_reports == 0:
        return {
            "city": city,
            "health_score": 100,
            "status": "Excellent",
            "total_reports": 0,
            "top_diseases": [],
            "trend": "stable",
            "symptom_trends": []
        }

    # 📊 HEALTH CALCULATION
    avg_severity = severity_score / valid_reports
    health_score = max(0, 100 - (avg_severity * 18))

    if health_score >= 85:
        status = "Excellent"
    elif health_score >= 70:
        status = "Good"
    elif health_score >= 50:
        status = "Moderate"
    elif health_score >= 30:
        status = "Risky"
    else:
        status = "Critical"

    # 🦠 Top diseases
    top_diseases = sorted(
        disease_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # 📈 Trend
    if valid_reports < 5:
        trend = "stable"
    elif valid_reports < 15:
        trend = "increasing"
    else:
        trend = "high"

    # 🔥 TOP 5 SYMPTOMS (for graph)
    top_symptoms = sorted(
        symptom_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    symptom_trends = [
        {
            "name": name,
            "values": symptom_hourly[name]  # 24 values
        }
        for name, _ in top_symptoms
    ]

    return {
        "city": city,
        "health_score": round(health_score, 2),
        "status": status,
        "total_reports": valid_reports,
        "top_diseases": top_diseases,
        "trend": trend,
        "symptom_trends": symptom_trends
    }


def extract_news_error_message(response):
    try:
        error_payload = response.json()
    except ValueError:
        error_payload = {}

    for key in ("errors", "message", "error"):
        value = error_payload.get(key)
        if isinstance(value, list) and value:
            return "; ".join(str(item) for item in value)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return f"GNews returned HTTP {response.status_code}"


def fetch_world_health_news():
    api_key = os.getenv("GNEWS_API_KEY", "").strip()

    if not api_key:
        return {
            "articles": [],
            "configured": False,
            "message": "Set GNEWS_API_KEY to load live health headlines."
        }

    try:
        session = requests.Session()
        primary_response = session.get(
            CONFIG["NEWS_API_URL"],
            params={
                "category": CONFIG["NEWS_CATEGORY"],
                "lang": CONFIG["NEWS_LANGUAGE"],
                "country": CONFIG["NEWS_COUNTRY"],
                "max": CONFIG["NEWS_MAX_RESULTS"],
                "apikey": api_key
            },
            timeout=10
        )

        if not primary_response.ok:
            error_message = extract_news_error_message(primary_response)
            raise requests.HTTPError(error_message, response=primary_response)

        payload = primary_response.json()
        articles_payload = payload.get("articles", [])

        if not articles_payload:
            fallback_response = session.get(
                CONFIG["NEWS_FALLBACK_API_URL"],
                params={
                    "q": CONFIG["NEWS_QUERY"],
                    "lang": CONFIG["NEWS_LANGUAGE"],
                    "country": CONFIG["NEWS_COUNTRY"],
                    "max": CONFIG["NEWS_MAX_RESULTS"],
                    "sortby": "publishedAt",
                    "apikey": api_key
                },
                timeout=10
            )

            if not fallback_response.ok:
                error_message = extract_news_error_message(fallback_response)
                raise requests.HTTPError(error_message, response=fallback_response)

            payload = fallback_response.json()
    except requests.RequestException as exc:
        return {
            "articles": [],
            "configured": True,
            "message": f"Unable to load live health news right now: {exc}"
        }

    articles = []
    for article in payload.get("articles", []):
        articles.append({
            "title": article.get("title", "Untitled health update"),
            "description": article.get("description") or "Open the article for more details.",
            "url": article.get("url", "#"),
            "source": (article.get("source") or {}).get("name", "Global Health News"),
            "published_at": article.get("publishedAt")
        })

    return {
        "articles": articles,
        "configured": True,
        "message": "Live health headlines loaded successfully."
    }


def attach_medical_news(payload: dict):
    news_result = fetch_world_health_news()
    articles = news_result.get("articles", [])

    payload["medical_news"] = [
        article.get("title", "Health update")
        for article in articles
    ]
    payload["medical_news_articles"] = articles

    if not payload["medical_news"] and news_result.get("message"):
        payload["medical_news"] = [news_result["message"]]

    return payload

# --- FOLLOW UP QUESTION ENGINE ---

followup_questions = {

    "body_pain": [
    "Is the pain throughout your whole body?",
    "Do you feel muscle soreness?",
    "Did the pain start suddenly?",
    "Do you feel fatigue along with the pain?"
    ],

    "fever": [
        "Do you also have chills?",
        "Are you experiencing headache?",
        "Do you feel body pain or fatigue?",
        "Do you have cough or sore throat?"
    ],

    "headache": [
        "Do you feel dizziness?",
        "Do you also have nausea?",
        "Are you sensitive to light?",
        "Do you feel pressure around your temples?"
    ],

    "dizziness": [
        "Do you feel nausea or vomiting?",
        "Do you experience blurred vision?",
        "Does the dizziness worsen when standing?",
        "Do you also have headache?"
    ],

    "cough": [
        "Is the cough dry or producing mucus?",
        "Do you also have fever?",
        "Do you feel chest tightness?",
        "Are you experiencing sore throat?"
    ],

    "sore_throat": [
        "Do you have difficulty swallowing?",
        "Do you also have fever?",
        "Do you feel swelling in your neck?",
        "Do you have cough?"
    ],

    "chest_pain": [
        "Do you feel breathlessness?",
        "Does the pain spread to your arm or jaw?",
        "Do you feel sweating or nausea?",
        "Does the pain worsen with movement?"
    ],

    "breathlessness": [
        "Do you also have chest pain?",
        "Do you feel wheezing while breathing?",
        "Does it worsen when lying down?",
        "Do you feel dizziness?"
    ],

    "nausea": [
        "Are you vomiting as well?",
        "Do you have abdominal pain?",
        "Do you feel dizziness?",
        "Did you recently eat something unusual?"
    ],

    "vomiting": [
        "Do you also feel nausea?",
        "Do you have abdominal pain?",
        "Do you have fever?",
        "Are you experiencing dehydration?"
    ],

    "abdominal_pain": [
        "Is the pain sharp or dull?",
        "Do you feel nausea or vomiting?",
        "Does the pain worsen after eating?",
        "Do you also have fever?"
    ],

    "diarrhea": [
        "Do you have abdominal cramps?",
        "Do you feel dehydration?",
        "Do you have fever?",
        "Have you eaten outside recently?"
    ],

    "constipation": [
        "Do you feel abdominal discomfort?",
        "Have you had a change in diet recently?",
        "Are you experiencing bloating?",
        "Do you feel nausea?"
    ],

    "skin_rash": [
        "Do you also feel itching?",
        "Is the rash spreading?",
        "Do you have fever with the rash?",
        "Did the rash appear suddenly?"
    ],

    "itching": [
        "Is the itching constant or occasional?",
        "Do you see redness or rash?",
        "Did you recently try new skincare products?",
        "Is the itching worse at night?"
    ],

    "joint_pain": [
        "Do you feel swelling in the joints?",
        "Is the pain worse in the morning?",
        "Do you feel stiffness?",
        "Did you experience any injury?"
    ],

    "back_pain": [
        "Did you lift heavy objects recently?",
        "Do you feel numbness in your legs?",
        "Does the pain spread to your legs?",
        "Is the pain worse while sitting?"
    ],

    "neck_pain": [
        "Does the pain spread to your shoulders?",
        "Do you feel stiffness while turning your head?",
        "Did you sleep in an unusual position?",
        "Do you have headache as well?"
    ],

    "fatigue": [
        "Do you feel weakness throughout the day?",
        "Are you experiencing sleep problems?",
        "Do you have fever?",
        "Do you feel dizziness?"
    ],

    "blurred_vision": [
        "Do you feel headache?",
        "Do you experience eye pain?",
        "Do you feel dizziness?",
        "Did the vision problem appear suddenly?"
    ],

    "eye_pain": [
        "Do you have redness in the eyes?",
        "Do you feel sensitivity to light?",
        "Is your vision blurry?",
        "Do you feel headache?"
    ],

    "ear_pain": [
        "Do you have hearing problems?",
        "Do you feel pressure in your ear?",
        "Do you have fever?",
        "Do you feel dizziness?"
    ],

    "runny_nose": [
        "Do you also have sneezing?",
        "Do you feel sinus pressure?",
        "Do you have cough?",
        "Do you have fever?"
    ],

    "sneezing": [
        "Do you have runny nose?",
        "Do you feel itchy eyes?",
        "Do you have cough?",
        "Did symptoms start suddenly?"
    ],

    "swelling": [
        "Is the swelling painful?",
        "Did it appear suddenly?",
        "Do you have redness in the area?",
        "Do you feel fever?"
    ],

    "weight_loss": [
        "Was the weight loss sudden?",
        "Do you feel fatigue?",
        "Do you have appetite loss?",
        "Do you have abdominal pain?"
    ],

    "weight_gain": [
        "Did your diet change recently?",
        "Do you feel fatigue?",
        "Do you have swelling?",
        "Are you exercising regularly?"
    ],

    "loss_of_appetite": [
        "Do you feel nausea?",
        "Do you have abdominal discomfort?",
        "Have you experienced weight loss?",
        "Do you feel fatigue?"
    ],

    "insomnia": [
        "Do you have stress or anxiety?",
        "Do you wake up frequently at night?",
        "Do you feel fatigue during the day?",
        "Have you changed your sleep routine?"
    ],

    "anxiety": [
        "Do you feel restlessness?",
        "Do you experience rapid heartbeat?",
        "Do you feel sweating or trembling?",
        "Do you have difficulty sleeping?"
    ],

    "depression": [
        "Do you feel loss of interest in activities?",
        "Do you feel fatigue most of the day?",
        "Do you have trouble sleeping?",
        "Do you feel loss of appetite?"
    ]
}

yes_words = ["yes", "yeah", "yep", "y", "correct", "true"]
no_words = ["no", "nope", "not", "false"]


# ----------------------------------------------------
# MEDICAL REASONING ENGINE
# ----------------------------------------------------

reasoning_map = {

    "cardiologist": {
        "condition": "a possible heart-related issue",
        "symptoms": ["chest_pain", "breathlessness", "fatigue"]
    },

    "dermatologist": {
        "condition": "a possible skin condition",
        "symptoms": ["skin_rash", "itching"]
    },

    "neurologist": {
        "condition": "a possible neurological condition",
        "symptoms": ["headache", "dizziness", "blurred_vision"]
    },

    "general_physician": {
        "condition": "a possible general infection",
        "symptoms": ["fever", "fatigue", "cough"]
    }

}

def generate_followup_reason(symptoms, question):

    # If no symptoms detected, just ask the question
    if not symptoms:
        return question

    return (
        "Based on the symptoms you mentioned, "
        "I need a little more information.\n\n"
        f"{question}"
    )


DISEASE_RULES = [

# -------------------------
# RESPIRATORY
# -------------------------
{
    "disease": "Common Cold",
    "symptoms": ["cough", "sore_throat", "runny_nose", "sneezing"],
    "severity": "mild",
    "doctor": "general_physician"
},
{
    "disease": "Influenza",
    "symptoms": ["fever", "body_pain", "fatigue", "headache", "cough"],
    "severity": "moderate",
    "doctor": "general_physician"
},
{
    "disease": "COVID-19",
    "symptoms": ["fever", "cough", "fatigue", "breathlessness", "loss_of_appetite"],
    "severity": "moderate",
    "doctor": "general_physician"
},
{
    "disease": "Bronchitis",
    "symptoms": ["cough", "fatigue", "chest_pain", "breathlessness"],
    "severity": "moderate",
    "doctor": "general_physician"
},

# -------------------------
# CARDIO
# -------------------------
{
    "disease": "Heart Attack Risk",
    "symptoms": ["chest_pain", "jaw", "sweating", "dizziness", "breathlessness"],
    "severity": "critical",
    "doctor": "cardiologist"
},
{
    "disease": "Hypertension",
    "symptoms": ["headache", "dizziness", "fatigue"],
    "severity": "moderate",
    "doctor": "cardiologist"
},

# -------------------------
# GASTRO
# -------------------------
{
    "disease": "Food Poisoning",
    "symptoms": ["vomiting", "diarrhea", "abdominal_pain", "fever"],
    "severity": "moderate",
    "doctor": "general_physician"
},
{
    "disease": "Gastritis",
    "symptoms": ["abdominal_pain", "nausea", "vomiting", "loss_of_appetite"],
    "severity": "mild",
    "doctor": "general_physician"
},
{
    "disease": "Acid Reflux (GERD)",
    "symptoms": ["chest_pain", "abdominal_pain", "nausea"],
    "severity": "mild",
    "doctor": "general_physician"
},

# -------------------------
# NEURO
# -------------------------
{
    "disease": "Migraine",
    "symptoms": ["headache", "nausea", "blurred_vision"],
    "severity": "moderate",
    "doctor": "neurologist"
},
{
    "disease": "Vertigo",
    "symptoms": ["dizziness", "nausea", "blurred_vision"],
    "severity": "moderate",
    "doctor": "neurologist"
},

# -------------------------
# SKIN
# -------------------------
{
    "disease": "Skin Allergy",
    "symptoms": ["itching", "skin_rash"],
    "severity": "mild",
    "doctor": "dermatologist"
},
{
    "disease": "Fungal Infection",
    "symptoms": ["itching", "skin_rash", "redness"],
    "severity": "mild",
    "doctor": "dermatologist"
},

# -------------------------
# GENERAL / INFECTION
# -------------------------
{
    "disease": "Dengue",
    "symptoms": ["fever", "body_pain", "headache", "vomiting"],
    "severity": "severe",
    "doctor": "general_physician"
},
{
    "disease": "Malaria",
    "symptoms": ["fever", "chills", "sweating", "headache"],
    "severity": "severe",
    "doctor": "general_physician"
},
{
    "disease": "Typhoid",
    "symptoms": ["fever", "abdominal_pain", "fatigue", "headache"],
    "severity": "severe",
    "doctor": "general_physician"
},

# -------------------------
# MUSCULOSKELETAL
# -------------------------
{
    "disease": "Muscle Strain",
    "symptoms": ["body_pain", "fatigue"],
    "severity": "mild",
    "doctor": "general_physician"
},
{
    "disease": "Back Pain Syndrome",
    "symptoms": ["back_pain", "body_pain"],
    "severity": "mild",
    "doctor": "general_physician"
}
]

def predict_disease(user_symptoms):

    best_match = None
    best_score = 0

    for disease in DISEASE_RULES:

        disease_symptoms = set(disease["symptoms"])
        user_symptoms_set = set(user_symptoms)

        # Match count
        match = disease_symptoms & user_symptoms_set

        # Precision + recall style scoring
        match_score = len(match) / len(disease_symptoms)

        # Bonus if core symptoms matched
        if len(match) >= 2:
            match_score += 0.2

        if match_score > best_score:
            best_score = match_score
            best_match = disease

    if best_match:
        return {
            "disease": best_match["disease"],
            "confidence": round(best_score * 100, 2),
            "severity": best_match["severity"],
            "doctor": best_match["doctor"]
        }

    return {
        "disease": "Unknown",
        "confidence": 0,
        "severity": "unknown",
        "doctor": "general_physician"
    }

# ----------------------------------------------------
# END POINTS
# ----------------------------------------------------
@app.post("/predict")
def predict_specialist(input_data: SymptomInput):

    user = input_data.user_id
    text = input_data.symptoms[0].lower().strip()

    # -------------------------
    # RESET COMMAND
    # -------------------------
    if "reset" in text:
        ai_memory[user] = []
        ai_question_state[user] = {
            "last_symptom": None,
            "asked": []
        }
        return {
            "message": "Conversation reset",
            "detected_symptoms": []
        }

    # -------------------------
    # INIT MEMORY
    # -------------------------
    if user not in ai_memory:
        ai_memory[user] = []

    if user not in ai_question_state:
        ai_question_state[user] = {
            "last_symptom": None,
            "asked": []
        }

    # -------------------------
    # DETECT YES / NO
    # -------------------------
    text_clean = text.strip().lower()

    is_yes = any(text_clean.startswith(word) for word in yes_words)
    is_no = any(text_clean.startswith(word) for word in no_words)

    # -------------------------
    # EXTRACT SYMPTOMS
    # -------------------------
    extracted = list(dict.fromkeys(ai_memory[user]))

    if not is_yes and not is_no:

        if " " in text:
            extracted = extract_symptoms_from_text(text)
        else:
            extracted = [
                s.strip().lower().replace(" ", "_")
                for s in input_data.symptoms
            ]

    # -------------------------
    # UPDATE MEMORY
    # -------------------------
    if is_yes and ai_question_state[user]["last_symptom"]:
        symptom = ai_question_state[user]["last_symptom"]
        if symptom not in ai_memory[user]:
            ai_memory[user].append(symptom)

    elif not is_no:
        for s in extracted:
            if s not in ai_memory[user]:
                ai_memory[user].append(s)

    extracted = ai_memory[user]
    
    # -------------------------
    # DEFAULT RESPONSE
    # -------------------------
    specialist = "General Physician"
    specialist_key = "general_physician"
    confidence = 0.0
    explanation = ""
    question = None
    
    
    if not extracted:
        return {
        "followup_question": "Can you describe your symptoms in more detail?",
        "detected_symptoms": []
    }

    # -------------------------
    # MODEL PREDICTION
    # -------------------------
    if model and vocab and extracted:

        input_vector = pd.DataFrame(0, index=[0], columns=vocab)

        found_symptoms = []

        for s in extracted:
            if s in vocab:
                input_vector.at[0, s] = 1
                found_symptoms.append(s)

        if found_symptoms:

            prediction = model.predict(input_vector)[0]
            probs = model.predict_proba(input_vector)

            confidence = float(max(probs[0]))

            specialist = prediction.replace("_", " ").title()
            specialist_key = prediction

            if specialist_key in reasoning_map:
                condition = reasoning_map[specialist_key]["condition"]
                explanation = f"Your symptoms suggest {condition}."

            if confidence < 0.60:
                specialist = "General Physician"
                specialist_key = "general_physician"
                explanation = "The current symptom match is below the specialist confidence threshold, so starting with a General Physician is the safest next step."

    # -------------------------
    # FOLLOW UP QUESTION LOGIC
    # -------------------------
    if len(ai_question_state[user]["asked"]) < 4:

        # Case 1: single symptom
        if len(extracted) == 1:

            symptom = extracted[0]

            if symptom in followup_questions:

                remaining = []

                for q in followup_questions[symptom]:

                    if q in ai_question_state[user]["asked"]:
                        continue

    # Prevent asking about symptoms already confirmed
                    skip = False
                    for s in extracted:
                        readable = s.replace("_"," ")
                        if readable in q.lower():
                            skip = True
                            break

                    if not skip:
                        remaining.append(q)

                if remaining:

                    question = random.choice(remaining)

                    ai_question_state[user]["asked"].append(question)
                    ai_question_state[user]["last_symptom"] = symptom

        # Case 2: multiple symptoms but low confidence
        elif confidence < 0.70:

    # prioritize the last confirmed symptom
            last = ai_question_state[user]["last_symptom"]

            priority_list = extracted
            if last and last in extracted:
                priority_list = [last] + [s for s in extracted if s != last]

            for s in priority_list:

                if s in followup_questions:

                    remaining = [
                        q for q in followup_questions[s]
                        if q not in ai_question_state[user]["asked"]
                    ]

                    if remaining:

                        question = random.choice(remaining)

                        ai_question_state[user]["asked"].append(question)
                        ai_question_state[user]["last_symptom"] = s
                        break

    # -------------------------
    # LOG CHAT
    # -------------------------
    if extracted:
        db.log_chat(user, f"Symptoms: {', '.join(extracted)}", "user")
    else:
        db.log_chat(user, "Symptoms: unknown", "user")

    db.log_chat(user, f"Recommended: {specialist}", "ai")

    # -------------------------
    # RESPONSE
    # -------------------------
    if question:

        reasoned_question = generate_followup_reason(extracted, question)

        return {
            "followup_question": reasoned_question,
            "detected_symptoms": extracted
        }

    if not explanation:
        if extracted:
            explanation = f"Based on symptoms such as {', '.join(extracted)}, this condition may require a {specialist}."
        else:
            explanation = f"Based on the provided symptoms, consulting a {specialist} is recommended."

    return {
        "specialist": specialist,
        "specialist_key": specialist_key,
        "confidence": f"{confidence:.0%}",
        "detected_symptoms": extracted,
        "explanation": explanation
    }

import requests

@app.post("/voice-to-text")
async def voice_to_text(file: UploadFile = File(...)):

    audio_bytes = await file.read()
    if not audio_bytes:
        return {"text": ""}

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/webm"
    }

    response = requests.post(
        "https://api.deepgram.com/v1/listen?model=nova-2&punctuate=false&diarize=false&smart_format=false&paragraphs=false&utterances=false&multichannel=false&filler_words=false",
        headers=headers,
        data=audio_bytes,
        timeout=20
    )

    result = response.json()
    text = (
        result.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
        .strip()
    )

    return {"text": text}



@app.post("/text-to-voice")
async def text_to_voice(data: dict):

    text = data.get("text")

    audio_stream = deepgram.speak.v1.audio.generate(
        text=text,
        model="aura-asteria-en"
    )

    audio_bytes = b"".join(audio_stream)

    return Response(content=audio_bytes, media_type="audio/wav")


@app.get("/news/health")
def get_health_news():
    return fetch_world_health_news()


@app.get("/city-health/{city}")
def get_city_dashboard(city: str):
    return attach_medical_news(calculate_city_health(city))

# ----------------------------------------------------
# 🔥 STEP 2: UPDATED REPORT ENDPOINT
# ----------------------------------------------------

@app.post("/report")
def submit_community_report(
    report: ReportRequest,
    current_user: str = Depends(get_current_user)
):

    # 🔥 CLEAN INPUT
    cleaned_symptoms = [
        s.strip().lower()
        for s in report.symptoms
        if s.strip() != ""
    ]

    # 🚫 BLOCK INVALID REPORT
    if not cleaned_symptoms:
        raise HTTPException(
            status_code=400,
            detail="Invalid symptoms. Please provide valid input."
        )

    # 🔥 GET USER REPORTS (FOR SPAM CONTROL)
    all_reports = db.get_reports_by_city(report.city)

    user_reports = [
        r for r in all_reports
        if r["user_id"] == current_user
    ]

    now = datetime.now()

    # 🔥 1. TIME-BASED LIMIT (30 seconds)
    if user_reports:
        last_report = user_reports[-1]  # latest
        last_time = datetime.fromisoformat(last_report["timestamp"])

        if (now - last_time).seconds < 30:
            raise HTTPException(
                status_code=429,
                detail="Please wait before submitting another report."
            )

    # 🔥 2. DUPLICATE CHECK (same symptoms)
    if user_reports:
        last_report = user_reports[-1]

        last_symptoms = sorted([
            s.strip().lower()
            for s in last_report["symptoms"]
        ])

        if last_symptoms == sorted(cleaned_symptoms):
            raise HTTPException(
                status_code=400,
                detail="Duplicate report detected."
            )

    # ✅ SAVE REPORT
    new_report = {
        "id": str(uuid.uuid4()),
        "city": report.city,
        "symptoms": cleaned_symptoms,
        "user_id": current_user,
        "timestamp": now.isoformat()
    }

    db.add_report(new_report)

    updated_health = calculate_city_health(report.city)
    updated_health = attach_medical_news(updated_health)

    return {
        "message": "Report submitted successfully.",
        "updated_city_health": updated_health
    }


    
@app.post("/groups/create")
def create_group(
    req: CreateGroupRequest,
    current_user: str = Depends(get_current_user)):

    new_group = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "disease_tag": req.disease_tag,
        "created_by": current_user,
        "members": [current_user]
    }

    db.create_group(new_group)

    return {"message": "Group created successfully", "group": new_group}
    




@app.get("/groups/user/{user_id}")
def get_user_groups(user_id: str):
    return db.get_user_groups(user_id)



@app.post("/groups/message")
def send_group_message(
    req: GroupMessageRequest,
    current_user: str = Depends(get_current_user)
):

    group = next(
        (g for g in db.data["groups"] if g["id"] == req.group_id),
        None
    )

    if not group or current_user not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a group member")

    new_msg = {
        "id": str(uuid.uuid4()),
        "group_id": req.group_id,
        "sender": current_user,
        "message": req.message,
        "timestamp": datetime.now().isoformat()
    }

    db.add_group_message(new_msg)

    return {"message": "Message sent"}

@app.get("/groups/messages/{group_id}")
def get_messages(group_id: str):
    return db.get_group_messages(group_id)



@app.get("/groups/all")
def get_all_groups():
    return db.get_all_groups()


@app.post("/groups/request")
def request_join(
    req: JoinGroupRequest,
    current_user: str = Depends(get_current_user)
):

    new_request = {
        "group_id": req.group_id,
        "user_id": current_user,
        "status": "pending"
    }

    db.create_join_request(new_request)

    return {"message": "Join request sent"}


@app.get("/groups/requests/{group_id}")
def get_requests(group_id: str):
    return db.get_group_requests(group_id)


@app.post("/groups/approve")
def approve(req: ApproveRequest):
    db.approve_request(req.group_id, req.user_id)
    return {"message": "User approved"}

@app.post("/auth/register")
def register(req: RegisterRequest):

    if req.username in db.data["users"]:
        raise HTTPException(status_code=400, detail="User already exists")

    db.data["users"][req.username] = {
        "password_hash": hash_password(req.password),
        "refresh_tokens": []
    }

    db._save_db()

    return {"message": "User registered successfully"}

@app.get("/doctors")
def get_doctors(specialty: str = None):

    doctors = db.get_doctors()

    if specialty:
        doctors = [
            d for d in doctors
            if d["specialty"] == specialty
        ]

    return {"doctors": doctors}

@app.post("/auth/login", response_model=TokenResponse)
def login(req: RegisterRequest):

    user = db.data["users"].get(req.username)

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        {"sub": req.username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = create_refresh_token({"sub": req.username})

    user["refresh_tokens"].append(refresh_token)
    db._save_db()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


from pydantic import BaseModel

class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest):

    refresh_token = req.refresh_token

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.data["users"].get(username)

    if not user or refresh_token not in user["refresh_tokens"]:
        raise HTTPException(status_code=401, detail="Refresh token invalid")

    # Remove old refresh token (rotation)
    user["refresh_tokens"].remove(refresh_token)

    new_access = create_access_token(
        {"sub": username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    new_refresh = create_refresh_token({"sub": username})
    user["refresh_tokens"].append(new_refresh)

    db._save_db()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh
    }
@app.websocket("/ws/groups/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str, token: str):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            await websocket.close()
            return
    except JWTError:
        await websocket.close()
        return

    # Validate membership
    group = next(
        (g for g in db.data["groups"] if g["id"] == group_id),
        None
    )

    if not group or username not in group["members"]:
        await websocket.close()
        return

    await manager.connect(websocket, group_id)

    try:
        while True:
            data = await websocket.receive_json()

            new_msg = {
                "id": str(uuid.uuid4()),
                "group_id": group_id,
                "sender": username,
                "message": data["message"],
                "timestamp": datetime.now().isoformat()
            }

            db.add_group_message(new_msg)

            await manager.broadcast(group_id, new_msg)

    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

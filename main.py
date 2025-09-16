import os
import uuid
import base64
import sqlite3
from io import BytesIO
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from dotenv import load_dotenv

load_dotenv()

# Import your custom services
import reddit_service
import ai_service
import cleanup_service

# --- Database Setup ---
DATABASE_URL = "users.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

# --- Application Setup ---
app = FastAPI()
scheduler = BackgroundScheduler()

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Security and Authentication ---

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_dev__replace_it")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get the current user from a token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (username,)).fetchone()
    conn.close()
    
    if user is None:
        raise credentials_exception
    return dict(user)

# --- Scheduled Jobs ---
@app.on_event("startup")
def start_scheduler():
    """Initializes and starts the background task scheduler using FastAPI's startup event."""
    interval_hours = int(os.getenv("CLEANUP_INTERVAL_HOURS", 1))
    print(f"Scheduling background cleanup job to run every {interval_hours} hour(s).")
    scheduler.add_job(cleanup_service.run_cleanup_if_needed, "interval", hours=interval_hours)
    scheduler.start()
    print("Scheduler started...")

@app.on_event("shutdown")
def shutdown_scheduler():
    """Stops the scheduler on application shutdown."""
    print("Shutting down scheduler...")
    scheduler.shutdown()

# --- HTML Page Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main landing page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Serves the main application dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# --- API Routes ---

@app.post("/api/register")
async def register_user(request: Request):
    """Registers a new user in the SQLite database."""
    data = await request.json()
    username = data.get('email')
    password = data.get('password')
    referral_code = data.get('referralCode')
    print("Registering user:", username)

    required_referral = os.getenv("SIGNUP_REFERRAL_CODE")
    if required_referral and (not referral_code or referral_code != required_referral):
        raise HTTPException(status_code=403, detail="Invalid or missing referral code.")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (username,)).fetchone()
    if user:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered.")
        
    hashed_password = get_password_hash(password)
    conn.execute('INSERT INTO users (email, hashed_password) VALUES (?, ?)',
                 (username, hashed_password))
    conn.commit()
    conn.close()
    
    print(f"User registered: {username}")
    
    return JSONResponse(content={"ok": True, "message": "User registered successfully."})

@app.post("/api/login")
async def login_for_access_token(request: Request):
    """Logs in a user and returns a JWT access token."""
    data = await request.json()
    username = data.get('email')
    password = data.get('password')
    print("logging in user:", username)

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (username,)).fetchone()
    conn.close()

    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "email": user["email"]}

@app.get("/api/posts")
async def get_reddit_posts(current_user: dict = Depends(get_current_user)):
    """(Protected) Fetches the latest image posts from r/PhotoshopRequest."""
    print("Fetching posts...")
    try:
        posts = reddit_service.get_photoshop_request_posts(limit=10, cache=False)
        return {"ok": True, "posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """(Protected) Handles user image uploads and saves them locally."""
    print(f"receiving upload: {file.filename}, content_type: {file.content_type}")
    if not os.path.exists("static/uploads"):
        os.makedirs("static/uploads")
        
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("static/uploads", unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    print(f"File uploaded: {file_path}")
    return {"ok": True, "file_path": f"/static/uploads/{unique_filename}"}


@app.post("/api/analyze")
async def analyze_post(request: Request, current_user: dict = Depends(get_current_user)):
    """(Protected) Analyzes a post title and description to generate an edit prompt."""
    data = await request.json()
    title = data.get("title", "")
    description = data.get("description", "")
    
    analysis = ai_service.analyze_request(title, description)
    return {"ok": True, "analysis": analysis}


@app.post("/api/edit")
async def edit_image(request: Request, current_user: dict = Depends(get_current_user)):
    """
    (Protected) Takes an image URL and a prompt, uses an AI to edit, and saves the new image.
    """
    try:
        data = await request.json()
        image_url = data.get('imageUrl')
        print(f"Image Request at : {image_url}")
        prompt = data.get('prompt')

        if not image_url or not prompt:
            raise HTTPException(status_code=400, detail="imageUrl and prompt are required")

        if image_url.startswith('/'):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(base_dir, image_url.lstrip('/'))
            image_source = image_path
        else:
            image_source = image_url

        result = ai_service.edit_image_with_gemini(image_source, prompt)

        if result.get("ok"):
            image_data_url = result.get("edited_image_data")
            if image_data_url:
                header, encoded = image_data_url.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                
                edited_dir = "static/edited_images"
                if not os.path.exists(edited_dir):
                    os.makedirs(edited_dir)
                
                filename = f"edited_{uuid.uuid4()}.png"
                file_path = os.path.join(edited_dir, filename)
                
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                
                print(f"Edited image saved to {file_path}")
                result["edited_image_path"] = f"/{file_path}"

        return JSONResponse(content=result)

    except Exception as e:
        print(f"Error in /api/edit: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during image editing.")


from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import uuid
from typing import Optional, List
import json
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
import aioimaplib
import email
import asyncio
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import bcrypt

load_dotenv()

app = FastAPI(title="StartupMail API", description="Email service for startups")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
mongo_client = MongoClient(os.environ.get('MONGO_URL'))
db = mongo_client.startupmail
users_collection = db.users
emails_collection = db.emails
drafts_collection = db.drafts
contacts_collection = db.contacts

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY')
ALGORITHM = os.environ.get('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30))

# Email configuration
SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

IMAP_HOST = os.environ.get('IMAP_HOST')
IMAP_PORT = int(os.environ.get('IMAP_PORT', 993))
IMAP_USERNAME = os.environ.get('IMAP_USERNAME')
IMAP_PASSWORD = os.environ.get('IMAP_PASSWORD')
IMAP_USE_SSL = os.environ.get('IMAP_USE_SSL', 'true').lower() == 'true'

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class EmailSend(BaseModel):
    to: List[EmailStr]
    cc: Optional[List[EmailStr]] = []
    bcc: Optional[List[EmailStr]] = []
    subject: str
    body: str
    is_html: bool = False

class EmailDraft(BaseModel):
    to: Optional[List[EmailStr]] = []
    cc: Optional[List[EmailStr]] = []
    bcc: Optional[List[EmailStr]] = []
    subject: Optional[str] = ""
    body: Optional[str] = ""
    is_html: bool = False

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        user = users_collection.find_one({"email": email})
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/register")
async def register(user: UserCreate):
    # Check if user already exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "hashed_password": hashed_password,
        "full_name": user.full_name,
        "company": user.company,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    users_collection.insert_one(user_doc)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login")
async def login(user: UserLogin):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/user/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "company": current_user.get("company"),
        "created_at": current_user["created_at"]
    }

@app.post("/api/emails/send")
async def send_email(email_data: EmailSend, current_user: dict = Depends(get_current_user)):
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = current_user["email"]
        msg['To'] = ', '.join(email_data.to)
        msg['Subject'] = email_data.subject
        
        if email_data.cc:
            msg['Cc'] = ', '.join(email_data.cc)
        
        # Add body
        if email_data.is_html:
            msg.attach(MIMEText(email_data.body, 'html'))
        else:
            msg.attach(MIMEText(email_data.body, 'plain'))
        
        # Send email via SMTP
        if not SMTP_HOST:
            raise HTTPException(status_code=500, detail="SMTP not configured")
        
        smtp = aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT, use_tls=SMTP_USE_TLS)
        await smtp.connect()
        await smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        recipients = email_data.to + email_data.cc + email_data.bcc
        await smtp.send_message(msg, recipients=recipients)
        await smtp.quit()
        
        # Save to sent emails
        email_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "message_id": msg['Message-ID'],
            "from_email": current_user["email"],
            "to": email_data.to,
            "cc": email_data.cc,
            "bcc": email_data.bcc,
            "subject": email_data.subject,
            "body": email_data.body,
            "is_html": email_data.is_html,
            "sent_at": datetime.utcnow(),
            "folder": "sent",
            "is_read": True
        }
        
        emails_collection.insert_one(email_doc)
        
        return {"message": "Email sent successfully", "email_id": email_doc["id"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.get("/api/emails/inbox")
async def get_inbox(current_user: dict = Depends(get_current_user)):
    try:
        # For now, return emails from database
        # In production, this would sync with IMAP
        emails = list(emails_collection.find(
            {"user_id": current_user["id"], "folder": {"$in": ["inbox", "sent"]}},
            {"_id": 0}
        ).sort("sent_at", -1))
        
        return {"emails": emails}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@app.post("/api/emails/drafts")
async def save_draft(draft: EmailDraft, current_user: dict = Depends(get_current_user)):
    try:
        draft_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "to": draft.to,
            "cc": draft.cc,
            "bcc": draft.bcc,
            "subject": draft.subject,
            "body": draft.body,
            "is_html": draft.is_html,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        drafts_collection.insert_one(draft_doc)
        
        return {"message": "Draft saved successfully", "draft_id": draft_doc["id"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {str(e)}")

@app.get("/api/emails/drafts")
async def get_drafts(current_user: dict = Depends(get_current_user)):
    try:
        drafts = list(drafts_collection.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("updated_at", -1))
        
        return {"drafts": drafts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch drafts: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
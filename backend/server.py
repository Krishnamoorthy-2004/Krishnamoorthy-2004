from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import uuid
from typing import Optional, List, Dict, Any
import json
import base64
import httpx
import asyncio
from pydantic import BaseModel, EmailStr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import random
import time

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
templates_collection = db.templates
campaigns_collection = db.campaigns
sessions_collection = db.sessions
email_accounts_collection = db.email_accounts

# Security
security = HTTPBearer()

# Mock email providers
class MockEmailProvider:
    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        self.mock_emails = self._generate_mock_emails()
    
    def _generate_mock_emails(self) -> List[Dict]:
        """Generate mock emails for demonstration"""
        mock_emails = []
        senders = [
            "john.doe@example.com", "jane.smith@startup.com", "info@techcompany.com",
            "support@saasplatform.com", "newsletter@businessnews.com"
        ]
        subjects = [
            "Project Update - Q1 Results", "New Feature Release", "Meeting Invitation",
            "Invoice #12345", "Welcome to our platform", "Weekly Newsletter",
            "Partnership Opportunity", "Customer Feedback", "Security Update"
        ]
        
        for i in range(20):
            email = {
                "id": str(uuid.uuid4()),
                "from": random.choice(senders),
                "subject": random.choice(subjects),
                "body": f"This is a mock email body for email {i+1}. Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "received_at": datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                "is_read": random.choice([True, False]),
                "is_important": random.choice([True, False, False, False]),
                "labels": random.sample(["Work", "Personal", "Important", "Follow-up"], k=random.randint(0, 2)),
                "attachments": []
            }
            mock_emails.append(email)
        
        return sorted(mock_emails, key=lambda x: x['received_at'], reverse=True)
    
    async def authenticate_oauth(self, auth_code: str) -> Dict[str, Any]:
        """Mock OAuth authentication"""
        await asyncio.sleep(0.5)  # Simulate API call
        return {
            "access_token": f"mock_token_{uuid.uuid4()}",
            "refresh_token": f"mock_refresh_{uuid.uuid4()}",
            "expires_in": 3600,
            "email": f"user@{self.provider_type.lower()}.com"
        }
    
    async def get_emails(self, access_token: str, folder: str = "inbox") -> List[Dict]:
        """Mock get emails"""
        await asyncio.sleep(0.3)  # Simulate API call
        return self.mock_emails
    
    async def send_email(self, access_token: str, email_data: Dict) -> Dict:
        """Mock send email"""
        await asyncio.sleep(0.5)  # Simulate API call
        return {
            "message_id": f"mock_msg_{uuid.uuid4()}",
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def get_profile(self, access_token: str) -> Dict:
        """Mock get user profile"""
        await asyncio.sleep(0.2)  # Simulate API call
        return {
            "email": f"user@{self.provider_type.lower()}.com",
            "name": f"Mock {self.provider_type} User",
            "picture": f"https://via.placeholder.com/150?text={self.provider_type[0]}"
        }

# Initialize mock providers
gmail_provider = MockEmailProvider("Gmail")
outlook_provider = MockEmailProvider("Outlook")

# Pydantic models
class UserProfile(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None

class EmailAccount(BaseModel):
    provider: str  # "gmail" or "outlook"
    email: EmailStr
    name: str
    is_primary: bool = False

class EmailSend(BaseModel):
    to: List[EmailStr]
    cc: Optional[List[EmailStr]] = []
    bcc: Optional[List[EmailStr]] = []
    subject: str
    body: str
    is_html: bool = False
    template_id: Optional[str] = None

class EmailDraft(BaseModel):
    to: Optional[List[EmailStr]] = []
    cc: Optional[List[EmailStr]] = []
    bcc: Optional[List[EmailStr]] = []
    subject: Optional[str] = ""
    body: Optional[str] = ""
    is_html: bool = False

class EmailTemplate(BaseModel):
    name: str
    category: str
    subject: str
    body: str
    is_html: bool = True

class BulkCampaign(BaseModel):
    name: str
    template_id: str
    recipients: List[EmailStr]
    schedule_at: Optional[datetime] = None

class EmailFilter(BaseModel):
    name: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]

# Helper functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from session token"""
    try:
        session_token = credentials.credentials
        session = sessions_collection.find_one({"session_token": session_token})
        
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Check if session is expired
        if datetime.utcnow() > session["expires_at"]:
            raise HTTPException(status_code=401, detail="Session expired")
        
        user = users_collection.find_one({"id": session["user_id"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/session")
async def authenticate_session(request: Request):
    """Authenticate user with Emergent session"""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Call Emergent auth API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        auth_data = response.json()
        
        # Create or update user
        user_data = {
            "id": auth_data["id"],
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data.get("picture", ""),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        existing_user = users_collection.find_one({"email": auth_data["email"]})
        if not existing_user:
            users_collection.insert_one(user_data)
        else:
            users_collection.update_one(
                {"email": auth_data["email"]},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
        
        # Create session
        session_data = {
            "session_token": auth_data["session_token"],
            "user_id": auth_data["id"],
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }
        
        sessions_collection.insert_one(session_data)
        
        return {
            "session_token": auth_data["session_token"],
            "user": user_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/api/user/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user.get("picture", ""),
        "created_at": current_user["created_at"]
    }

@app.post("/api/email-accounts/connect")
async def connect_email_account(
    provider: str,
    auth_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Connect Gmail or Outlook account"""
    try:
        if provider not in ["gmail", "outlook"]:
            raise HTTPException(status_code=400, detail="Invalid provider")
        
        # Mock OAuth flow
        provider_instance = gmail_provider if provider == "gmail" else outlook_provider
        auth_result = await provider_instance.authenticate_oauth(auth_code)
        profile = await provider_instance.get_profile(auth_result["access_token"])
        
        # Save email account
        account_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "provider": provider,
            "email": profile["email"],
            "name": profile["name"],
            "access_token": auth_result["access_token"],
            "refresh_token": auth_result["refresh_token"],
            "token_expires_at": datetime.utcnow() + timedelta(seconds=auth_result["expires_in"]),
            "is_primary": email_accounts_collection.count_documents({"user_id": current_user["id"]}) == 0,
            "created_at": datetime.utcnow()
        }
        
        email_accounts_collection.insert_one(account_data)
        
        return {
            "message": f"{provider.capitalize()} account connected successfully",
            "account": {
                "id": account_data["id"],
                "provider": provider,
                "email": profile["email"],
                "name": profile["name"],
                "is_primary": account_data["is_primary"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")

@app.get("/api/email-accounts")
async def get_email_accounts(current_user: dict = Depends(get_current_user)):
    """Get connected email accounts"""
    accounts = list(email_accounts_collection.find(
        {"user_id": current_user["id"]},
        {"_id": 0, "access_token": 0, "refresh_token": 0}
    ))
    
    return {"accounts": accounts}

@app.get("/api/emails/inbox")
async def get_inbox(
    account_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get emails from inbox"""
    try:
        if account_id:
            account = email_accounts_collection.find_one({"id": account_id, "user_id": current_user["id"]})
            if not account:
                raise HTTPException(status_code=404, detail="Email account not found")
            
            # Get emails from specific provider
            provider_instance = gmail_provider if account["provider"] == "gmail" else outlook_provider
            emails = await provider_instance.get_emails(account["access_token"])
            
            # Add account info to each email
            for email in emails:
                email["account_id"] = account_id
                email["account_email"] = account["email"]
                email["provider"] = account["provider"]
        else:
            # Get emails from all accounts
            accounts = list(email_accounts_collection.find({"user_id": current_user["id"]}))
            all_emails = []
            
            for account in accounts:
                provider_instance = gmail_provider if account["provider"] == "gmail" else outlook_provider
                emails = await provider_instance.get_emails(account["access_token"])
                
                for email in emails:
                    email["account_id"] = account["id"]
                    email["account_email"] = account["email"]
                    email["provider"] = account["provider"]
                
                all_emails.extend(emails)
            
            # Sort by received date
            emails = sorted(all_emails, key=lambda x: x['received_at'], reverse=True)
        
        return {"emails": emails}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@app.post("/api/emails/send")
async def send_email(
    email_data: EmailSend,
    account_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Send email"""
    try:
        # Get account to send from
        if account_id:
            account = email_accounts_collection.find_one({"id": account_id, "user_id": current_user["id"]})
        else:
            account = email_accounts_collection.find_one({"user_id": current_user["id"], "is_primary": True})
        
        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        # Get template if specified
        body = email_data.body
        subject = email_data.subject
        
        if email_data.template_id:
            template = templates_collection.find_one({"id": email_data.template_id, "user_id": current_user["id"]})
            if template:
                body = template["body"]
                subject = template["subject"]
        
        # Send via provider
        provider_instance = gmail_provider if account["provider"] == "gmail" else outlook_provider
        send_result = await provider_instance.send_email(account["access_token"], {
            "to": email_data.to,
            "cc": email_data.cc,
            "bcc": email_data.bcc,
            "subject": subject,
            "body": body,
            "is_html": email_data.is_html
        })
        
        # Save to sent emails
        email_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "account_id": account["id"],
            "message_id": send_result["message_id"],
            "from_email": account["email"],
            "to": email_data.to,
            "cc": email_data.cc,
            "bcc": email_data.bcc,
            "subject": subject,
            "body": body,
            "is_html": email_data.is_html,
            "sent_at": datetime.utcnow(),
            "folder": "sent",
            "is_read": True,
            "provider": account["provider"]
        }
        
        emails_collection.insert_one(email_doc)
        
        return {
            "message": "Email sent successfully",
            "email_id": email_doc["id"],
            "sent_at": email_doc["sent_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/api/emails/drafts")
async def save_draft(
    draft: EmailDraft,
    draft_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Save or update draft"""
    try:
        if draft_id:
            # Update existing draft
            existing_draft = drafts_collection.find_one({"id": draft_id, "user_id": current_user["id"]})
            if not existing_draft:
                raise HTTPException(status_code=404, detail="Draft not found")
            
            drafts_collection.update_one(
                {"id": draft_id},
                {"$set": {
                    "to": draft.to,
                    "cc": draft.cc,
                    "bcc": draft.bcc,
                    "subject": draft.subject,
                    "body": draft.body,
                    "is_html": draft.is_html,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            return {"message": "Draft updated successfully", "draft_id": draft_id}
        else:
            # Create new draft
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
    """Get user's drafts"""
    try:
        drafts = list(drafts_collection.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("updated_at", -1))
        
        return {"drafts": drafts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch drafts: {str(e)}")

@app.delete("/api/emails/drafts/{draft_id}")
async def delete_draft(draft_id: str, current_user: dict = Depends(get_current_user)):
    """Delete draft"""
    try:
        result = drafts_collection.delete_one({"id": draft_id, "user_id": current_user["id"]})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return {"message": "Draft deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete draft: {str(e)}")

@app.post("/api/templates")
async def create_template(
    template: EmailTemplate,
    current_user: dict = Depends(get_current_user)
):
    """Create email template"""
    try:
        template_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "name": template.name,
            "category": template.category,
            "subject": template.subject,
            "body": template.body,
            "is_html": template.is_html,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        templates_collection.insert_one(template_doc)
        
        return {"message": "Template created successfully", "template_id": template_doc["id"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

@app.get("/api/templates")
async def get_templates(current_user: dict = Depends(get_current_user)):
    """Get user's email templates"""
    try:
        templates = list(templates_collection.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1))
        
        return {"templates": templates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch templates: {str(e)}")

@app.get("/api/templates/startup")
async def get_startup_templates():
    """Get predefined startup email templates"""
    startup_templates = [
        {
            "id": "welcome_investor",
            "name": "Investor Welcome Email",
            "category": "Investor Relations",
            "subject": "Welcome to {company_name} - Investment Opportunity",
            "body": "<p>Dear {investor_name},</p><p>Thank you for your interest in {company_name}. We're excited to share our vision with you...</p>",
            "is_html": True
        },
        {
            "id": "product_launch",
            "name": "Product Launch Announcement",
            "category": "Marketing",
            "subject": "🚀 Introducing {product_name} - Now Live!",
            "body": "<p>Hi {customer_name},</p><p>We're thrilled to announce the launch of {product_name}! After months of development...</p>",
            "is_html": True
        },
        {
            "id": "partnership_proposal",
            "name": "Partnership Proposal",
            "category": "Business Development",
            "subject": "Partnership Opportunity - {company_name}",
            "body": "<p>Hello {partner_name},</p><p>I hope this email finds you well. I'm reaching out to explore a potential partnership...</p>",
            "is_html": True
        }
    ]
    
    return {"templates": startup_templates}

@app.post("/api/campaigns")
async def create_campaign(
    campaign: BulkCampaign,
    current_user: dict = Depends(get_current_user)
):
    """Create bulk email campaign"""
    try:
        campaign_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "name": campaign.name,
            "template_id": campaign.template_id,
            "recipients": campaign.recipients,
            "schedule_at": campaign.schedule_at or datetime.utcnow(),
            "status": "scheduled",
            "created_at": datetime.utcnow(),
            "sent_count": 0,
            "failed_count": 0
        }
        
        campaigns_collection.insert_one(campaign_doc)
        
        return {"message": "Campaign created successfully", "campaign_id": campaign_doc["id"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")

@app.get("/api/campaigns")
async def get_campaigns(current_user: dict = Depends(get_current_user)):
    """Get user's campaigns"""
    try:
        campaigns = list(campaigns_collection.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1))
        
        return {"campaigns": campaigns}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {str(e)}")

@app.get("/api/analytics/dashboard")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get dashboard analytics"""
    try:
        # Mock analytics data
        analytics = {
            "total_emails_sent": random.randint(50, 500),
            "total_emails_received": random.randint(100, 1000),
            "open_rate": round(random.uniform(0.15, 0.45), 2),
            "click_rate": round(random.uniform(0.02, 0.08), 2),
            "bounce_rate": round(random.uniform(0.01, 0.05), 2),
            "unsubscribe_rate": round(random.uniform(0.001, 0.01), 2),
            "recent_activity": [
                {
                    "type": "email_sent",
                    "count": random.randint(1, 10),
                    "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                }
                for i in range(7)
            ],
            "top_recipients": [
                {"email": "john@example.com", "count": random.randint(1, 15)},
                {"email": "jane@startup.com", "count": random.randint(1, 12)},
                {"email": "info@client.com", "count": random.randint(1, 8)}
            ]
        }
        
        return {"analytics": analytics}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
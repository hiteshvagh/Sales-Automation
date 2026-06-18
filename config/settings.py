import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

COMPANY_NAME = "Aspire Softserv"
COMPANY_TAGLINE = "Global IT Consulting & Digital Transformation"
COMPANY_SERVICES = [
    "AI Agents", "Generative AI", "AI Chatbots", "AI Automation", "LLM Integration",
    "SaaS Development", "Enterprise Software", "Product Engineering",
    "Web Development", "Mobile Development",
    "Odoo ERP", "ERPNext", "Custom ERP",
    "AWS", "Azure", "GCP", "DevOps",
    "BI & Analytics", "Data Engineering",
    "Legacy Modernization", "Process Automation",
    "UI/UX Design", "QA Automation",
]

TARGET_INDUSTRIES = [
    "Healthcare", "Manufacturing", "Retail", "Hospitality", "Logistics",
    "Finance", "Insurance", "Education", "Construction", "Real Estate",
    "Energy", "Government", "Travel", "Supply Chain", "Food & Beverage",
    "Pharma", "E-commerce",
]

TARGET_COUNTRIES = [
    "USA", "Canada", "UK", "Germany", "France",
    "Netherlands", "Australia", "Singapore", "UAE", "Saudi Arabia",
]

TARGET_EMPLOYEE_RANGES = ["100,500", "500,1000", "1000,5000"]

DECISION_MAKER_TITLES = [
    "CEO", "Founder", "Co-Founder", "Managing Director",
    "CTO", "CIO", "VP Engineering", "Head of IT", "Head of Technology",
    "Digital Transformation Director", "Operations Director",
    "Innovation Director", "Engineering Director",
    "Procurement Head",
]

BUYING_SIGNALS = [
    "Recently raised funding",
    "Hiring AI Engineers",
    "Hiring Developers",
    "Hiring ERP Consultants",
    "Expanding globally",
    "Opening new offices",
    "Launching new products",
    "Migrating ERP",
    "Moving to Cloud",
    "Hiring DevOps",
    "Hiring Data Engineers",
    "Replacing legacy systems",
    "Building internal products",
    "Growing rapidly",
    "Acquiring companies",
]

MODEL = "claude-sonnet-4-6"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "crm.db")

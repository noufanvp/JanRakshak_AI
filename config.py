"""
JanRakshak AI
Configuration File
"""

import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# --------------------------------------------------
# Application
# --------------------------------------------------

APP_NAME = "JanRakshak AI"
VERSION = "2.0"
COUNTRY = "India"
DEVELOPER = "Aaqib Omar"

# Backward compatibility
App_name = APP_NAME
version = VERSION
Country = COUNTRY
Developer = DEVELOPER

# --------------------------------------------------
# AI
# --------------------------------------------------

OFFLINE_AI_ENABLED = True

# Backward compatibility
Offline_AI_Enabled = OFFLINE_AI_ENABLED


# --------------------------------------------------
# Files
# --------------------------------------------------

DATABASE_FILE = "data/reports.db"
REPORT_FOLDER = "reports"
LOG_FOLDER = "Logs"

EMERGENCY_FILE = "data/emergency_contacts.json"
SETTINGS_FILE = "data/settings.json"
AI_MEMORY_FILE = "data/ai_memory.json"

# Backward compatibility
Database_File = DATABASE_FILE
Report_Folder = REPORT_FOLDER
Log_Folder = LOG_FOLDER
Emergency_file = EMERGENCY_FILE
Settings_file = SETTINGS_FILE
ai_memory_file = AI_MEMORY_FILE

# --------------------------------------------------
# Welcome Message
# --------------------------------------------------

WELCOME_MESSAGE = f"""
============================================================
                 {APP_NAME}
                    Version {VERSION}
============================================================

AI Powered Civic Issue Reporting System

Helping Citizens
Helping Authorities
Building a Smarter India

============================================================
"""

Welcome_message = WELCOME_MESSAGE

# --------------------------------------------------
# Languages
# --------------------------------------------------

SUPPORTED_LANGUAGES = [
    "English",
    "Hindi",
    "Malayalam"
]

Supported_languages = SUPPORTED_LANGUAGES

# --------------------------------------------------
# Issue Types
# --------------------------------------------------

ISSUE_TYPES = [
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Flood",
    "Fire",
    "Electricity",
    "Tree Fall",
    "Other"
]

Issue_types = ISSUE_TYPES

# --------------------------------------------------
# Priorities
# --------------------------------------------------

PRIORITY_LEVELS = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

Priority_levels = PRIORITY_LEVELS
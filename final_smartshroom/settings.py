"""
Django settings for final_smartshroom project.
"""

from pathlib import Path
import os
import json
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # load .env file

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-b#)yfyb6pz9o9$_x4ngth@r)9qsc_t0ljehxix1-x7*r9b8j36')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Added for production static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Moved before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

ROOT_URLCONF = 'final_smartshroom.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.firebase_user', 
            ],
        },
    },
]

WSGI_APPLICATION = 'final_smartshroom.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Production static files configuration for Render
if not DEBUG:
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Firebase Configuration ---
def initialize_firebase():
    """Initialize Firebase Admin SDK with proper error handling"""
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            print("✅ Firebase already initialized")
            return True

        # --- THIS IS THE MISSING PIECE ---
        # We must tell Firebase where the Realtime Database is located
        firebase_options = {
            'databaseURL': 'https://smartshroom-597b2-default-rtdb.firebaseio.com'
        }
        # --------------------------------
            
        # Method 1: Try service account file from FIREBASE_SERVICE_ACCOUNT_PATH
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if service_account_path:
            cred_path = BASE_DIR / service_account_path
            if cred_path.exists():
                cred = credentials.Certificate(str(cred_path))
                # Pass firebase_options here
                firebase_admin.initialize_app(cred, firebase_options)
                print(f"✅ Firebase initialized from: {cred_path}")
                return True
            else:
                print(f"⚠️  Service account path not found: {cred_path}")
        
        # Method 2: Try direct file path (simplified)
        cred_path = BASE_DIR / "firebase_credentials.json"
        if cred_path.exists():
            cred = credentials.Certificate(str(cred_path))
            # Pass firebase_options here
            firebase_admin.initialize_app(cred, firebase_options)
            print(f"✅ Firebase initialized from: {cred_path}")
            return True
        
        # Method 3: Try FIREBASE_CREDENTIALS_JSON environment variable
        firebase_credentials_json_str = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if firebase_credentials_json_str:
            try:
                cred_dict = json.loads(firebase_credentials_json_str)
                cred = credentials.Certificate(cred_dict)
                # Pass firebase_options here
                firebase_admin.initialize_app(cred, firebase_options)
                print("✅ Firebase initialized from FIREBASE_CREDENTIALS_JSON")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in FIREBASE_CREDENTIALS_JSON: {e}")
            except Exception as e:
                print(f"❌ Error initializing Firebase from env var: {e}")
        
        # If no method worked
        print("❌ Firebase not initialized: No valid credentials found")
        return False
        
    except ImportError:
        print("❌ Firebase Admin SDK not installed. Run: pip install firebase-admin")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during Firebase initialization: {e}")
        return False

# Render configuration
if 'RENDER' in os.environ:
    ALLOWED_HOSTS.extend([
        os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),
        'smartshroom.onrender.com'
    ])
    DEBUG = False
    
    # Security settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    # Local development settings
    DEBUG = True
    
    
# Initialize Firebase
firebase_initialized = initialize_firebase()

# Firebase Frontend Config (for JavaScript client)
CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", "AIzaSyDbQpy2qSjPN7c316KhNT1hfNMDnwGK6IE"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "smartshroom-597b2.firebaseapp.com"),
    "databaseURL": os.getenv("FIREBASE_DB_URL", "https://smartshroom-597b2-default-rtdb.firebaseio.com"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", "smartshroom-597b2"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "smartshroom-597b2.firebasestorage.app"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", "625325732992"),
    "appId": os.getenv("FIREBASE_APP_ID", "1:625325732992:web:9057838a9f2e766e3a2265"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "G-HDFM5GQX16"),
}



# Also keep FIREBASE_CONFIG for consistency
FIREBASE_CONFIG = CONFIG

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
from django.conf import settings
from django.http import JsonResponse
import firebase_admin
from firebase_admin import auth, firestore
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
import base64
import uuid
import pyrebase
import os
import io
import json
import numpy as np
from PIL import Image
import tensorflow as tf
import keras
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import torch
import torch.nn as nn
from torch.serialization import add_safe_globals
import requests
import time
import pytz
from io import BytesIO
from PIL import Image
from torchvision import models, transforms
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


# Initialize Firestore client
db = firestore.client()

# Initialize Firebase
config = settings.CONFIG
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
database = firebase.database()
# storage = firebase.storage()



def signup(request):
    if request.method == 'POST':
        # Basic account info
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Personal information
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        # Professional information
        job_title = request.POST.get('job_title', 'SmartShroom User')
        organization = request.POST.get('organization', '')
        department = request.POST.get('department', '')
        experience = request.POST.get('experience', '0-1')
        specialization = request.POST.get('specialization', 'oyster')
        
        # Preferences
        timezone = request.POST.get('timezone', 'EST')
        language = request.POST.get('language', 'en')
        email_notifications = request.POST.get('email_notifications') == 'on'
        data_sharing = request.POST.get('data_sharing') == 'on'
        bio = request.POST.get('bio', '')
        
        # Basic server-side validation
        if not all([email, password, confirm_password, first_name, last_name]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/signup.html')
            
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/signup.html')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'accounts/signup.html')
        
        # Create user in Firebase
        try:
            # Create user with email and password
            user = auth.create_user_with_email_and_password(email, password)
            
            user_data = {
                # Personal Information
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "phone": phone,
                
                # Professional Information
                "jobTitle": job_title,
                "organization": organization,
                "department": department,
                "experience": experience,
                "specialization": specialization,
                
                # Preferences
                "timezone": timezone,
                "language": language,
                "emailNotifications": email_notifications,
                "dataSharing": data_sharing,
                "bio": bio,
                
                # System fields
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "avatarUrl": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=120&h=120&fit=crop&crop=face"
            }

            # Save user data in Firestore
            db.collection("users").document(user['localId']).set(user_data)
            
            # Send email verification
            auth.send_email_verification(user['idToken'])
            
            messages.success(request, 'Account created successfully! Please verify your email address.')
            return redirect('login')
            
        except Exception as e:
            error_message = str(e)
            if "EMAIL_EXISTS" in error_message:
                messages.error(request, 'Email already exists. Please use a different email or login.')
            elif "WEAK_PASSWORD" in error_message:
                messages.error(request, 'Password is too weak. Please use a stronger password.')
            elif "INVALID_EMAIL" in error_message:
                messages.error(request, 'Invalid email address. Please enter a valid email.')
            else:
                messages.error(request, f'An error occurred during registration: {error_message}')
            
            return render(request, 'accounts/signup.html', {
                'preserved_data': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'job_title': job_title,
                    'organization': organization,
                    'department': department,
                    'bio': bio
                }
            })
    
    return render(request, 'accounts/signup.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Sign in with email and password
            user = auth.sign_in_with_email_and_password(email, password)
            
            # Get user info
            user_info = auth.get_account_info(user['idToken'])
            
            # Check if email is verified
            email_verified = user_info['users'][0]['emailVerified']
            
            if not email_verified:
                messages.warning(request, 'Please verify your email before logging in.')
                return render(request, 'accounts/login.html')
            
            # Store user session info
            request.session['user'] = {
                'localId': user['localId'],
                'email': user_info['users'][0]['email'],
                'idToken': user['idToken'],
                'refreshToken': user['refreshToken']
            }
            
            return redirect('dashboard')  # Redirect to dashboard or home page
            
        except Exception as e:
            error_message = str(e)
            
            # Check for various Firebase authentication error types
            if any(error_type in error_message for error_type in [
                "INVALID_PASSWORD",
                "EMAIL_NOT_FOUND", 
                "INVALID_LOGIN_CREDENTIALS",
                "INVALID_EMAIL",
                "USER_DISABLED",
                "TOO_MANY_ATTEMPTS_TRY_LATER"
            ]):
                messages.error(request, 'Invalid email or password. Please try again.')
            elif "WEAK_PASSWORD" in error_message:
                messages.error(request, 'Password is too weak. Please choose a stronger password.')
            elif "EMAIL_EXISTS" in error_message:
                messages.error(request, 'An account with this email already exists.')
            elif "OPERATION_NOT_ALLOWED" in error_message:
                messages.error(request, 'Email/password accounts are not enabled.')
            else:
                # For any other errors, show a generic message instead of the technical details
                messages.error(request, 'Login failed. Please check your credentials and try again.')
            
            # Optional: Log the actual error for debugging purposes (remove in production)
            # print(f"Login error: {error_message}")
    
    return render(request, 'accounts/login.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            # Send password reset email
            auth.send_password_reset_email(email)
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('login')
        except Exception as e:
            error_message = str(e)
            
            if "USER_NOT_FOUND" in error_message:
                messages.error(request, 'No account found with this email address.')
            elif "INVALID_EMAIL" in error_message:
                messages.error(request, 'The email address is not valid.')
            else:
                messages.error(request, 'Failed to send reset email. Please try again.')
            
            return redirect('login')
    
    return render(request, 'accounts/forgot_password.html')


def landingpage(request):
    return render(request, 'accounts/landingpage.html')

def logout(request):
    request.session.flush()  # Clear session
    messages.success(request, "Logged out successfully!")
    return redirect('landingpage')

def dashboard(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')
    
    return render(request, 'accounts/dashboard.html')

def add_harvest(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login') 

    if request.method == "POST":
        action = request.POST.get("action", "add")
        
        if action == "delete":
            harvest_id = request.POST.get("harvest_id")
            try:
                # Delete from Firestore
                db.collection("harvests").document(harvest_id).delete()
                messages.success(request, "Harvest deleted successfully!")
            except Exception as e:
                messages.error(request, f"Error deleting harvest: {str(e)}")
                
        elif action == "edit":
            harvest_id = request.POST.get("harvest_id")
            date = request.POST.get("date")
            kilograms = request.POST.get("kilograms")
            try:
                # Update in Firestore
                db.collection("harvests").document(harvest_id).update({
                    "date": date,
                    "kilograms": float(kilograms),
                    "timestamp": datetime.utcnow()
                })
                messages.success(request, "Harvest updated successfully!")
            except Exception as e:
                messages.error(request, f"Error updating harvest: {str(e)}")
                
        else:  # Default action: add
            date = request.POST.get("date")
            kilograms = request.POST.get("kilograms")
            try:
                # Save data to Firestore
                db.collection("harvests").add({
                    "date": date,
                    "kilograms": float(kilograms),
                    "timestamp": datetime.utcnow()
                })
                messages.success(request, "Harvest added successfully!")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    return redirect("report")

def report(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')
    try:
        # Fetch all harvest records from Firestore
        harvests = db.collection("harvests").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        # Convert Firestore documents to a list
        harvest_list = []
        total_kg = 0
        
        for doc in harvests:
            data = doc.to_dict()
            harvest_data = {
                "id": doc.id,
                "date": data.get("date"),
                "kilograms": data.get("kilograms", 0)
            }
            harvest_list.append(harvest_data)
            
            # Add to total (ensure kilograms is a number)
            try:
                kg_value = float(data.get("kilograms", 0))
                total_kg += kg_value
            except (ValueError, TypeError):
                # Skip invalid values
                pass
        
        # Calculate average harvest
        average_kg = round(total_kg / len(harvest_list), 2) if harvest_list else 0
        
        context = {
            "harvests": harvest_list,
            "total_harvest": round(total_kg, 2),
            "average_harvest": average_kg
        }
        
    except Exception as e:
        harvest_list = []
        context = {
            "harvests": harvest_list,
            "total_harvest": 0,
            "average_harvest": 0
        }
        messages.error(request, f"Error fetching data: {str(e)}")
    
    return render(request, "accounts/report.html", context)


def get_harvest_data(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')
    try:
        # Fetch all harvest records from Firestore, ordered by timestamp
        harvests = db.collection("harvests").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        # Convert Firestore documents to a list
        harvest_list = []
        total_kg = 0
        
        for doc in harvests:
            data = doc.to_dict()
            kg_value = data.get("kilograms", 0)
            
            harvest_data = {
                "date": data.get("date"),
                "kilograms": kg_value
            }
            harvest_list.append(harvest_data)
            
            # Add to total (ensure kilograms is a number)
            try:
                total_kg += float(kg_value)
            except (ValueError, TypeError):
                pass
        
        # Calculate average
        average_kg = round(total_kg / len(harvest_list), 2) if harvest_list else 0
        
        return JsonResponse({
            'harvest': harvest_list,
            'total_harvest': round(total_kg, 2),
            'average_harvest': average_kg,
            'total_records': len(harvest_list)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Optional: Add a separate function to get just statistics if needed
def get_harvest_statistics(request):
    """Helper function to get harvest statistics"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        harvests = db.collection("harvests").stream()
        total_kg = 0
        count = 0
        
        for doc in harvests:
            data = doc.to_dict()
            try:
                kg_value = float(data.get("kilograms", 0))
                total_kg += kg_value
                count += 1
            except (ValueError, TypeError):
                continue
        
        average_kg = round(total_kg / count, 2) if count > 0 else 0
        
        return JsonResponse({
            'total_harvest': round(total_kg, 2),
            'average_harvest': average_kg,
            'total_records': count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def remote(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login') 

    # Fetch device statuses from Firestore
    devices = {}
    current_temperature = None
    try:
        # Fetch sensor data to get current temperature
        sensor_data = database.child("sensors").get().val()
        if isinstance(sensor_data, dict):
            current_temperature = sensor_data.get('temperature')
        
        # Fetch Mist Maker status
        mistmaker_ref = db.collection("devices").document("mistmaker")
        mistmaker_data = mistmaker_ref.get().to_dict()
        devices["mistmaker"] = {
            "active": mistmaker_data.get("active", False) if mistmaker_data else False
        }

        # Fetch Fan Heater status
        fan_heater_ref = db.collection("devices").document("fan_heater")
        fan_heater_data = fan_heater_ref.get().to_dict()
        devices["fan_heater"] = {
            "active": fan_heater_data.get("active", False) if fan_heater_data else False,
            "temperature": fan_heater_data.get("temperature", None) if fan_heater_data else None
        }

        # Fetch Temperature Control status
        temperature_ref = db.collection("devices").document("temperature")
        temperature_data = temperature_ref.get().to_dict()
        devices["temperature"] = {
            "target": temperature_data.get("target", None) if temperature_data else None,
            "mode": temperature_data.get("mode", "auto") if temperature_data else "auto"
        }
        
        # AUTOMATIC FAN CONTROL LOGIC
        # Only activate if mode is auto and temperature is available
        if (devices["temperature"].get("mode") == "auto" and 
            current_temperature is not None and 
            fan_heater_data is not None):
            
            # Convert temperature to float for comparison
            try:
                temp_float = float(current_temperature)
                
                # If temperature is lower than 18°C, activate the fan
                if temp_float < 18.0:
                    if not fan_heater_data.get("active", False):
                        fan_heater_ref.set({
                            "active": True, 
                            "temperature": 22.0,  # Set a reasonable target temperature
                            "auto_activated": True  # Flag to indicate automatic activation
                        }, merge=True)
                        print(f"Fan automatically activated due to low temperature: {temp_float}°C")
                
                # Optional: Turn off fan if temperature rises above a certain threshold
                elif temp_float > 22.0 and fan_heater_data.get("active", False):
                    # Check if it was auto-activated to avoid turning off manual operations
                    if fan_heater_data.get("auto_activated", False):
                        fan_heater_ref.set({
                            "active": False,
                            "auto_activated": False
                        }, merge=True)
                        print(f"Fan automatically deactivated due to high temperature: {temp_float}°C")
                        
            except ValueError:
                print(f"Invalid temperature value: {current_temperature}")

    except Exception as e:
        messages.error(request, f"Error fetching device statuses: {str(e)}")
        devices = {
            "mistmaker": {"active": False},
            "fan_heater": {"active": False, "temperature": None},
            "temperature": {"target": None, "mode": "auto"}
        }

    # Handle form submissions
    if request.method == "POST":
        device = request.POST.get("device")
        action = request.POST.get("action")

        try:
            if device == "mistmaker":
                mistmaker_ref = db.collection("devices").document("mistmaker")
                if action == "on":
                    mistmaker_ref.set({"active": True}, merge=True)
                    messages.success(request, "Mist Maker turned on.")
                elif action == "off":
                    mistmaker_ref.set({"active": False}, merge=True)
                    messages.success(request, "Mist Maker turned off.")

            elif device == "fan_heater":
                fan_heater_ref = db.collection("devices").document("fan_heater")
                if action == "on":
                    temperature = float(request.POST.get("temperature", 0))
                    fan_heater_ref.set({
                        "active": True, 
                        "temperature": temperature,
                        "auto_activated": False  # Reset auto flag on manual activation
                    }, merge=True)
                    messages.success(request, f"Fan Heater turned on at {temperature}°C.")
                elif action == "off":
                    fan_heater_ref.set({
                        "active": False,
                        "auto_activated": False  # Reset auto flag
                    }, merge=True)
                    messages.success(request, "Fan Heater turned off.")

            elif device == "temperature":
                temperature_ref = db.collection("devices").document("temperature")
                target_temperature = float(request.POST.get("temperature", 0))
                mode = request.POST.get("mode", "auto")
                temperature_ref.set({"target": target_temperature, "mode": mode}, merge=True)
                messages.success(request, f"Temperature control updated to {target_temperature}°C in {mode} mode.")

        except Exception as e:
            messages.error(request, f"Error updating device: {str(e)}")

        return redirect("remote")

    # Pass current temperature to template for display
    return render(request, "accounts/remote.html", {
        "devices": devices,
        "current_temperature": current_temperature
    })

def get_sensor_data(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login') 

    try:
        # Adjust this path based on your Firebase structure
        sensor_data = database.child("sensors").get().val()

        print("Fetched data from Firebase:", sensor_data)

        if isinstance(sensor_data, dict):
            temperature = sensor_data.get('temperature')
            humidity = sensor_data.get('humidity')
        else:
            temperature = humidity = None

        return JsonResponse({
            'temperature': temperature,
            'humidity': humidity
        })

    except Exception as e:
        print(f"Error fetching sensor data: {e}")
        return JsonResponse({'error': 'Error fetching sensor data'}, status=500)


def update_control_settings(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login') 

    trichoderma_settings = {
        "target_temperature_min": 18.0,
        "target_temperature_max": 24.0,
        "target_humidity_min": 85.0,
        "target_humidity_max": 95.0,
        "disease": "trichoderma"
    }

    db.reference("/control_settings").set(trichoderma_settings)
    
    return JsonResponse({"message": "Successfully set Trichoderma settings in Firebase."})

# Import the firebase utils
from .firebase_utils import db, add_safe_globals

import os
from django.conf import settings

MODEL_PATH = os.path.join(settings.BASE_DIR, 'static/models/mushroom_mobilenetv2.h5')

# Model will be loaded lazily when needed
model = None
_tf_loaded = False

def load_model():
    """Load the ML model lazily."""
    global model, _tf_loaded
    
    if model is not None:
        return
    
    # Import TensorFlow only when needed (not at module level)
    if not _tf_loaded:
        import tensorflow as tf
        # Configure TensorFlow for lower memory usage
        tf.config.set_visible_devices([], 'GPU')  # Disable GPU if not needed
        physical_devices = tf.config.list_physical_devices('CPU')
        if physical_devices:
            try:
                # Limit memory growth
                for device in physical_devices:
                    tf.config.experimental.set_memory_growth(device, True)
            except:
                pass
        _tf_loaded = True
        
    try:
        # Check if file exists
        if not os.path.exists(MODEL_PATH):
            print(f"Error: Model file not found at {MODEL_PATH}")
            return

        try:
            from tensorflow import keras
            print("Loading TensorFlow/Keras model...")
            
            # Load the model with memory optimization
            model = keras.models.load_model(
                MODEL_PATH,
                compile=False  # Don't compile if you're only doing inference
            )
            
            # Compile for inference only (lighter weight)
            model.compile(optimizer='adam', loss='categorical_crossentropy')
            
            print("TensorFlow/Keras model loaded successfully")
                
        except Exception as e:
            print(f"Error loading TensorFlow/Keras model: {str(e)}")
            import traceback
            traceback.print_exc()
                
    except Exception as e:
        print(f"Error in load_model: {str(e)}")
        import traceback
        traceback.print_exc()

def process_image_with_model(img):
    """Process an image with the ML model and return the classification result."""
    global model
    
    # Load model only when first prediction is needed
    if model is None:
        load_model()
        if model is None:
            raise Exception("Model could not be loaded")
    
    # Import image processing libraries only when needed
    from PIL import Image
    import numpy as np
    
    try:
        # Import tensorflow functions only when needed
        from tensorflow.keras.preprocessing import image
        
        # Convert image to RGB if it has an alpha channel (4 channels)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Preprocess for MobileNetV2 (224x224 input size)
        img_resized = img.resize((224, 224))
        img_array = image.img_to_array(img_resized)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Normalize pixel values to [0,1] range
        img_array = img_array / 255.0
        
        # Make prediction
        predictions = model.predict(img_array, verbose=0)  # verbose=0 to reduce logging
        
        # Get the predicted class and confidence
        class_labels = ['Healthy Mushroom', 'Trichoderma']
        predicted_class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_idx])
    
        # Create result dictionary
        result = {
            'class': class_labels[predicted_class_idx],
            'confidence': confidence * 100,
            'status': class_labels[predicted_class_idx],
            'disease': class_labels[predicted_class_idx],
        }
        
        return result
        
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

def save_scan_result_to_firebase(user_id, result, image_name, confidence=0, analysis_type='upload'):
    """Enhanced function to save scan results with additional metadata"""
    try:
        # We already imported datetime and pytz at the top
        now = datetime.now(pytz.UTC)
        
        scan_data = {
            'user_id': user_id,
            'result': result,
            'image_name': image_name,
            'confidence': confidence,
            'analysis_type': analysis_type,  # 'upload', 'camera_capture', 'realtime'
            'timestamp': now.isoformat(),
            'created_at': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S')
        }
        
        # Add your Firebase saving logic here
        # Example:
        # firebase_db.child('scans').push(scan_data)
        db.collection("scans").add(scan_data)
        
        print(f"Saved scan result to Firebase: {scan_data}")
        return True
        
    except Exception as e:
        print(f"Error saving scan result to Firebase: {str(e)}")
        return False

def optimize_image_for_realtime(image, max_size=(640, 640)):
    """Optimize image for faster real-time processing"""
    try:
        # Convert to RGB if necessary (handle RGBA images)
        if image.mode == 'RGBA':
            # Create a white background and paste the image
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize while maintaining aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        return image
    except Exception as e:
        print(f"Error optimizing image: {str(e)}")
        return image

def validate_image_data(image_data):
    """Validate base64 image data"""
    try:
        if not image_data or ',' not in image_data:
            return False, "Invalid image data format"
        
        # Check if it's a valid base64 image
        header, data = image_data.split(',', 1)
        if 'image' not in header.lower():
            return False, "Not a valid image"
        
        # Try to decode
        decoded_data = base64.b64decode(data)
        if len(decoded_data) == 0:
            return False, "Empty image data"
        
        return True, "Valid image data"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def cleanup_old_temp_files(directory, max_age_hours=1):
    """Clean up temporary files older than specified hours"""
    import time
    import os
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"Cleaned up old temp file: {filename}")
                except Exception as e:
                    print(f"Error removing temp file {filename}: {str(e)}")

@csrf_exempt
def scan(request):    
    if 'user' not in request.session:
        # For AJAX requests, return JSON error
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'You need to log in first.',
                'status': 'error'
            }, status=401)
        messages.error(request, "You need to log in first.")
        return redirect('login')

    result = None
    uploaded_image = None
    camera_captured_image = None

    # Ensure temp_captures directory exists
    temp_captures_dir = os.path.join(settings.MEDIA_ROOT, 'temp_captures')
    os.makedirs(temp_captures_dir, exist_ok=True)

    # Check if it's an AJAX request
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # Handle POST requests (both AJAX and regular)
    if request.method == 'POST':
        # Handle file uploads (both AJAX and regular)
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if image_file.content_type not in allowed_types:
                if is_ajax:
                    return JsonResponse({
                        'error': 'Please upload a valid image file (JPEG, PNG, or WebP)',
                        'status': 'error'
                    }, status=400)
                messages.error(request, "Please upload a valid image file (JPEG, PNG, or WebP)")
                return render(request, 'accounts/scan.html', {})
            
            # Validate file size (max 10MB)
            if image_file.size > 10 * 1024 * 1024:
                if is_ajax:
                    return JsonResponse({
                        'error': 'File size too large. Please upload an image smaller than 10MB',
                        'status': 'error'
                    }, status=400)
                messages.error(request, "File size too large. Please upload an image smaller than 10MB")
                return render(request, 'accounts/scan.html', {})
            
            # Generate unique filename
            filename = f'upload_{uuid.uuid4()}{os.path.splitext(image_file.name)[1]}'
            
            # Save the image to temp directory
            file_path = os.path.join(temp_captures_dir, filename)
            with open(file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
                    
            # Set uploaded_image URL for the template
            uploaded_image = f'/media/temp_captures/{filename}'
            
            # Process the image with your model
            try:
                img = Image.open(file_path)
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                result = process_image_with_model(img)
                
                # Save scan result to Firebase
                if 'user' in request.session:
                    save_scan_result_to_firebase(
                        user_id=request.session['user']['localId'], 
                        result=result['class'], 
                        image_name=filename,
                        confidence=result.get('confidence', 0),
                        analysis_type='upload'
                    )
                
                # For AJAX requests, return JSON response
                if is_ajax:
                    return JsonResponse({
                        'result': result,
                        'image_url': uploaded_image,
                        'status': 'success'
                    })
                
                messages.success(request, "Image analyzed successfully!")
                
            except Exception as e:
                error_msg = f"Error processing image: {str(e)}"
                if is_ajax:
                    return JsonResponse({
                        'error': error_msg,
                        'status': 'error'
                    }, status=500)
                messages.error(request, error_msg)
                print(f"Error processing uploaded image: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Handle JSON data (real-time camera)
        elif is_ajax and request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                camera_image = data.get('camera_image')
                
                if not camera_image:
                    return JsonResponse({
                        'error': 'No image data provided',
                        'status': 'error'
                    }, status=400)
                
                # Validate image data
                is_valid, message = validate_image_data(camera_image)
                if not is_valid:
                    return JsonResponse({
                        'error': message,
                        'status': 'error'
                    }, status=400)
                
                # Decode base64 image
                image_data = camera_image.split(',')[1]
                image_data = base64.b64decode(image_data)
                
                # Create image from decoded data
                img = Image.open(io.BytesIO(image_data))
                
                # Optimize for real-time processing
                img = optimize_image_for_realtime(img)
                
                # Process the image with your model
                result = process_image_with_model(img)
                
                # Save to Firebase if user is authenticated
                if 'user' in request.session:
                    filename = f'realtime_{uuid.uuid4()}.jpg'
                    save_scan_result_to_firebase(
                        user_id=request.session['user']['localId'], 
                        result=result['class'], 
                        image_name=filename,
                        confidence=result.get('confidence', 0),
                        analysis_type='realtime'
                    )
                
                print(f"Real-time analysis result: {result}")
                
                # Return JSON response for real-time analysis
                return JsonResponse({
                    'result': result,
                    'timestamp': time.time(),
                    'status': 'success'
                })
            
            except Exception as e:
                print(f"Error in AJAX request: {str(e)}")
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'error': f'Analysis failed: {str(e)}',
                    'status': 'error'
                }, status=500)
        
        # Handle regular form submission with camera image (non-AJAX)
        elif request.POST.get('camera_image'):
            try:
                # Decode base64 image
                camera_image_data = request.POST.get('camera_image')
                if ',' in camera_image_data:
                    image_data = camera_image_data.split(',')[1]
                    image_data = base64.b64decode(image_data)
                    
                    # Generate unique filename
                    filename = f'capture_{uuid.uuid4()}.jpg'
                    
                    # Save the image permanently
                    temp_image_path = os.path.join(temp_captures_dir, filename)
                    
                    with open(temp_image_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Set the camera_captured_image for template rendering
                    camera_captured_image = f'/media/temp_captures/{filename}'
                    
                    # Create image from decoded data
                    img = Image.open(io.BytesIO(image_data))
                    
                    # Process the image with your model
                    result = process_image_with_model(img)
                    
                    # Save result to Firebase
                    if 'user' in request.session:
                        save_scan_result_to_firebase(
                            user_id=request.session['user']['localId'], 
                            result=result['class'], 
                            image_name=filename,
                            confidence=result.get('confidence', 0),
                            analysis_type='camera_capture'
                        )
                    
                    messages.success(request, "Camera image captured and analyzed successfully!")
                else:
                    messages.error(request, "Invalid camera image data")
                
            except Exception as e:
                messages.error(request, f"Error processing camera image: {str(e)}")
                print(f"Error processing camera image: {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Clean up old temporary files (older than 1 hour)
    try:
        cleanup_old_temp_files(temp_captures_dir, max_age_hours=1)
    except Exception as e:
        print(f"Error cleaning up temp files: {str(e)}")
    
    # For AJAX requests, we should have returned by now, so this is for regular requests
    if is_ajax:
        # If we get here, it means the AJAX request wasn't properly handled
        return JsonResponse({
            'error': 'Invalid request format',
            'status': 'error'
        }, status=400)
    
    # Put result in context for template rendering (regular requests only)
    context = {
        'uploaded_image': uploaded_image,
        'camera_captured_image': camera_captured_image,
        'result': result  # Pass the complete result object
    }
    
    return render(request, 'accounts/scan.html', context)

@csrf_exempt
def analyze_image(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_url = data.get('image_url')

            if not image_url:
                return JsonResponse({'error': 'No image URL provided'}, status=400)

            # Download the image from the given URL
            import requests
            from io import BytesIO
            
            response = requests.get(image_url)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to download image'}, status=400)

            img = Image.open(BytesIO(response.content)).convert("RGB")

            # Process image using model
            result = process_image_with_model(img)
            result['timestamp'] = datetime.utcnow().isoformat()

            # Optionally save to Firebase (if user is authenticated)
            if 'user' in request.session:
                save_scan_result_to_firebase(
                    user_id=request.session['user']['localId'],
                    result=result['class'],
                    image_name=image_url.split("/")[-1],
                    confidence=result.get('confidence', 0),
                    analysis_type='url_upload'
                )

            return JsonResponse({'result': result})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)





def profile(request):
    
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')
    
    try:
        # Get user data from Firestore
        user_ref = db.collection("users").document(request.session['user']['localId'])
        user_data = user_ref.get().to_dict()
        
        return render(request, 'accounts/profile.html', {
            'user_data': user_data
        })
        
    except Exception as e:
        messages.error(request, f"Error loading profile: {str(e)}")
        return redirect('dashboard')


def edit_profile(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')
    
    user_ref = db.collection("users").document(request.session['user']['localId'])
    user_data = user_ref.get().to_dict()
    
    if request.method == 'POST':
        try:
            # Get updated data from form
            updated_data = {
                "firstName": request.POST.get('first_name', user_data.get('firstName', '')),
                "lastName": request.POST.get('last_name', user_data.get('lastName', '')),
                "phone": request.POST.get('phone', user_data.get('phone', '')),
                "jobTitle": request.POST.get('job_title', user_data.get('jobTitle', '')),
                "organization": request.POST.get('organization', user_data.get('organization', '')),
                "department": request.POST.get('department', user_data.get('department', '')),
                "experience": request.POST.get('experience', user_data.get('experience', '0-1')),
                "specialization": request.POST.get('specialization', user_data.get('specialization', 'oyster')),
                "timezone": request.POST.get('timezone', user_data.get('timezone', 'EST')),
                "language": request.POST.get('language', user_data.get('language', 'en')),
                "emailNotifications": request.POST.get('email_notifications') == 'on',
                "dataSharing": request.POST.get('data_sharing') == 'on',
                "bio": request.POST.get('bio', user_data.get('bio', '')),
                "updatedAt": firestore.SERVER_TIMESTAMP
            }
            
            # Update Firestore document
            user_ref.set(updated_data, merge=True)
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'accounts/edit_profile.html', {
        'user_data': user_data,
        'preserved_data': request.POST if request.method == 'POST' else None
    })
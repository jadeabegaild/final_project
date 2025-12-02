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
# import torch
# import torch.nn as nn
# from torch.serialization import add_safe_globals
import requests
import time
import pytz
from io import BytesIO
from PIL import Image
# from torchvision import models, transforms
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from firebase_admin import db as realtime_db


# Initialize Firestore client
db = firestore.client()

# Initialize Firebase
from django.conf import settings
config = getattr(settings, 'CONFIG', getattr(settings, 'FIREBASE_CONFIG', {}))
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

# In your views.py

# In backend/views.py

def get_scan_dashboard_data(request):
    """Aggregates scan data: Counts healthy/diseased and gets recent scans."""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_id = request.session['user']['localId']
        # Fetch scans from Firebase
        scans_ref = db.collection("scans").where("user_id", "==", user_id).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        
        total_scans = 0
        healthy_count = 0
        disease_count = 0
        recent_scans = []
        
        for doc in scans_ref:
            data = doc.to_dict()
            total_scans += 1
            
            # Simple text check for health status
            result_str = str(data.get('result', '')).lower()
            if 'healthy' in result_str:
                healthy_count += 1
            else:
                disease_count += 1
            
            # Keep only the latest 5 scans for the list
            if len(recent_scans) < 5:
                # Format the date cleanly
                created_at = data.get('created_at', '')
                # If created_at is a timestamp object, convert it, otherwise string slice
                display_date = created_at[:16] if isinstance(created_at, str) and len(created_at) > 16 else created_at
                
                recent_scans.append({
                    'result': data.get('result', 'Unknown'),
                    'confidence': data.get('confidence', 0),
                    'date': display_date,
                    'image_name': data.get('image_name', '')
                })

        return JsonResponse({
            'stats': {
                'total': total_scans,
                'healthy': healthy_count,
                'disease': disease_count
            },
            'recent_scans': recent_scans
        })
        
    except Exception as e:
        print(f"Error getting scan dashboard data: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    

def add_harvest(request):
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login') 

    if request.method == "POST":
        action = request.POST.get("action", "add")
        user_id = request.session['user']['localId']  # Get current user ID
        
        if action == "delete":
            harvest_id = request.POST.get("harvest_id")
            try:
                # Delete from Firestore - verify ownership first
                harvest_ref = db.collection("harvests").document(harvest_id)
                harvest_data = harvest_ref.get().to_dict()
                
                if harvest_data and harvest_data.get('userId') == user_id:
                    harvest_ref.delete()
                    messages.success(request, "Harvest deleted successfully!")
                else:
                    messages.error(request, "You can only delete your own harvests.")
                    
            except Exception as e:
                messages.error(request, f"Error deleting harvest: {str(e)}")
                
        elif action == "edit":
            harvest_id = request.POST.get("harvest_id")
            date = request.POST.get("date")
            kilograms = request.POST.get("kilograms")
            try:
                # Update in Firestore - verify ownership first
                harvest_ref = db.collection("harvests").document(harvest_id)
                harvest_data = harvest_ref.get().to_dict()
                
                if harvest_data and harvest_data.get('userId') == user_id:
                    harvest_ref.update({
                        "date": date,
                        "kilograms": float(kilograms),
                        "timestamp": datetime.utcnow()
                    })
                    messages.success(request, "Harvest updated successfully!")
                else:
                    messages.error(request, "You can only edit your own harvests.")
                    
            except Exception as e:
                messages.error(request, f"Error updating harvest: {str(e)}")
                
        else:  # Default action: add
            date = request.POST.get("date")
            kilograms = request.POST.get("kilograms")
            try:
                # Save data to Firestore with user ID
                db.collection("harvests").add({
                    "date": date,
                    "kilograms": float(kilograms),
                    "timestamp": datetime.utcnow(),
                    "userId": user_id  # Add user ID to track ownership
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
        user_id = request.session['user']['localId']
        
        # --- 1. HARVESTS ---
        harvests = db.collection("harvests").where("userId", "==", user_id).stream()
        
        harvest_list = []
        total_kg = 0
        
        for doc in harvests:
            data = doc.to_dict()
            harvest_data = {
                "id": doc.id,
                "date": data.get("date"),
                "kilograms": data.get("kilograms", 0),
                "timestamp": data.get("timestamp")
            }
            harvest_list.append(harvest_data)
            
            # Add to total
            try:
                kg_value = float(data.get("kilograms", 0))
                total_kg += kg_value
            except (ValueError, TypeError):
                pass
        
        # Sort by timestamp descending
        harvest_list.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
        
        # --- 2. MUSHROOM BAGS ---
        mushroom_bags = db.collection("mushroom_bags").where("user_id", "==", user_id).stream()
        
        bag_list = []
        for doc in mushroom_bags:
            data = doc.to_dict()
            bag_data = {
                "id": doc.id,
                "date": data.get("date", "-"),
                "bag_name": data.get("bag_name", "Unnamed Bag"),
                "bag_type": data.get("bag_type", "oyster"),
                "quantity": data.get("quantity", 0), 
                "status": data.get("status", "active"),
                "notes": data.get("notes", ""),
                "created_at": data.get("created_at")
            }
            bag_list.append(bag_data)
            
        # --- 3. SCANS ---
        # Fixed indentation: This must be OUTSIDE the bag loop
        scans_ref = db.collection("scans").where("user_id", "==", user_id).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        
        scan_list = []
        for doc in scans_ref:
            scan_data = doc.to_dict()
            scan_data['id'] = doc.id
            # Format date for display
            if 'created_at' in scan_data:
                # Simplify date string (first 16 chars usually covers YYYY-MM-DD HH:MM)
                scan_data['date'] = str(scan_data['created_at'])[:16] 
            scan_list.append(scan_data)

        # --- CONTEXT ---
        context = {
            # Use the LISTS we created, not the raw Firestore streams
            'harvests': harvest_list,       
            'mushroom_bags': bag_list,      
            'scans': scan_list,             
        }
        
        # --- MISSING RETURN STATEMENT ADDED HERE ---
        return render(request, 'accounts/report.html', context)
        
    except Exception as e:
        print(f"Error in report view: {e}")
        messages.error(request, "Error loading report data.")
        # Only render the empty page if there was an error
        return render(request, 'accounts/report.html', {})


def add_mushroom_bag(request):
    """Handle Add, Edit, and Delete for Mushroom Bags"""
    if 'user' not in request.session:
        messages.error(request, "You need to log in first.")
        return redirect('login')

    if request.method == "POST":
        action = request.POST.get("action", "add")
        user_id = request.session['user']['localId']
        
        # --- DELETE ACTION ---
        if action == "delete":
            bag_id = request.POST.get("bag_id")
            try:
                bag_ref = db.collection("mushroom_bags").document(bag_id)
                bag_data = bag_ref.get().to_dict()
                
                if bag_data and bag_data.get('user_id') == user_id:
                    bag_ref.delete()
                    messages.success(request, "Mushroom bag deleted successfully!")
                else:
                    messages.error(request, "You can only delete your own bags.")
            except Exception as e:
                messages.error(request, f"Error deleting bag: {str(e)}")

        # --- EDIT ACTION ---
        elif action == "edit":
            bag_id = request.POST.get("bag_id")
            try:
                bag_ref = db.collection("mushroom_bags").document(bag_id)
                bag_data = bag_ref.get().to_dict()
                
                if bag_data and bag_data.get('user_id') == user_id:
                    bag_ref.update({
                        "date": request.POST.get("date"),
                        "bag_name": request.POST.get("bag_name"),
                        "bag_type": request.POST.get("bag_type"),
                        "quantity": int(request.POST.get("quantity", 0)),
                        "status": request.POST.get("status"),
                        "updated_at": firestore.SERVER_TIMESTAMP
                    })
                    messages.success(request, "Mushroom bag updated successfully!")
                else:
                    messages.error(request, "You can only edit your own bags.")
            except Exception as e:
                messages.error(request, f"Error updating bag: {str(e)}")

        # --- ADD ACTION (Default) ---
        else: 
            try:
                date = request.POST.get("date")
                if not date:
                    date = datetime.now().strftime("%Y-%m-%d")

                bag_data = {
                    "date": date,
                    "bag_name": request.POST.get("bag_name"),
                    "bag_type": request.POST.get("bag_type", "oyster"),
                    "quantity": int(request.POST.get("quantity", 0)),
                    "status": request.POST.get("status", "active"),
                    "notes": request.POST.get("notes", ""),
                    "user_id": user_id,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                
                db.collection("mushroom_bags").add(bag_data)
                messages.success(request, "Mushroom bag added successfully!")
                
            except Exception as e:
                messages.error(request, f"Error adding mushroom bag: {str(e)}")
    
    return redirect("report")

def get_bag_data(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
        
    user_id = request.session['user']['localId']
    
    try:
        # Initialize counts
        status_counts = {
            'active': 0, 'incubating': 0, 'fruiting': 0, 
            'harvested': 0, 'discarded': 0
        }
        type_counts = {
            'oyster': 0, 'shiitake': 0, 'button': 0, 
            'portobello': 0, 'other': 0
        }
        
        # Fetch all bags for this user
        bags = db.collection("mushroom_bags").where("user_id", "==", user_id).stream()
        
        for doc in bags:
            data = doc.to_dict()
            status = data.get('status', 'active').lower()
            bag_type = data.get('bag_type', 'oyster').lower()
            quantity = int(data.get('quantity', 0))
            
            # Update counts based on quantity (not just document count)
            if status in status_counts:
                status_counts[status] += quantity
                
            if bag_type in type_counts:
                type_counts[bag_type] += quantity
                
        return JsonResponse({
            'status_counts': status_counts,
            'type_counts': type_counts
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def get_harvest_data(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_id = request.session['user']['localId']
        print(f"Fetching harvest data for user: {user_id}")
        
        # Try without order_by first to avoid index issues
        harvests = db.collection("harvests").where("userId", "==", user_id).stream()
        
        harvest_list = []
        total_kg = 0
        
        for doc in harvests:
            data = doc.to_dict()
            print(f"Harvest data: {data}")
            
            kg_value = data.get("kilograms", 0)
            harvest_data = {
                "date": data.get("date", "Unknown"),
                "kilograms": float(kg_value) if kg_value else 0
            }
            harvest_list.append(harvest_data)
            total_kg += float(kg_value) if kg_value else 0
        
        print(f"Found {len(harvest_list)} harvest records")
        
        average_kg = round(total_kg / len(harvest_list), 2) if harvest_list else 0
        
        return JsonResponse({
            'harvest': harvest_list,
            'total_harvest': round(total_kg, 2),
            'average_harvest': average_kg,
            'total_records': len(harvest_list)
        })
        
    except Exception as e:
        print(f"Error in get_harvest_data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

# Optional: Add a separate function to get just statistics if needed
def get_harvest_statistics(request):
    """Helper function to get harvest statistics"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_id = request.session['user']['localId']
        
        # No order_by needed for statistics
        harvests = db.collection("harvests").where("userId", "==", user_id).stream()
        
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

    # --- 1. FETCH DATA ---
    devices = {}
    current_temperature = None
    current_humidity = None
    
    try:
        # Fetch Realtime Database Data
        all_data = database.get().val()
        
        # Parse Sensor Data
        if all_data and "sensors" in all_data:
            current_temperature = all_data["sensors"].get('temperature')
            current_humidity = all_data["sensors"].get('humidity')
            
        # Parse Device Data
        devices_data = all_data.get("devices", {}) if all_data else {}
        controls = devices_data.get("controls", {})
        
        # Get Current Settings
        target_temp = float(controls.get("target_temp", 24.0))
        mode = controls.get("mode", "auto")
        
        # Get Current Device States
        mist_active = devices_data.get("mistmaker", {}).get("active", False)
        fan_active = devices_data.get("fan_heater", {}).get("active", False)

        devices = {
            "mistmaker": {"active": mist_active},
            "fan_heater": {"active": fan_active},
            "temperature": {"target": target_temp, "mode": mode},
            "controls": {"target_temp": target_temp, "mode": mode}
        }

    except Exception as e:
        print(f"Error fetching data: {e}")
        # Defaults
        devices = {
            "mistmaker": {"active": False},
            "fan_heater": {"active": False},
            "temperature": {"target": 24.0, "mode": "manual"}
        }

    # --- 2. HANDLE POST REQUESTS ---
    if request.method == "POST":
        device_type = request.POST.get("device")
        action = request.POST.get("action")

        try:
            # === MANUAL DEVICE CONTROL ===
            if device_type == "mistmaker":
                is_active = (action == "on")
                # 1. Update the device state
                database.child("devices").child("mistmaker").update({"active": is_active})
                # 2. FORCE MANUAL MODE so Auto logic doesn't override this immediately
                database.child("devices").child("controls").update({"mode": "manual"})
                messages.success(request, f"Mist Maker turned {'ON' if is_active else 'OFF'} (Switched to Manual).")

            elif device_type == "fan_heater":
                is_active = (action == "on")
                # 1. Update the device state
                database.child("devices").child("fan_heater").update({"active": is_active})
                # 2. FORCE MANUAL MODE
                database.child("devices").child("controls").update({"mode": "manual"})
                messages.success(request, f"Exhaust Fans turned {'ON' if is_active else 'OFF'} (Switched to Manual).")

            # === SETTINGS CONTROL (Switching Modes) ===
            elif device_type == "temperature":
                new_temp = float(request.POST.get("temperature", 24.0))
                new_mode = request.POST.get("mode", "auto") # Values: 'auto' or 'manual'
                
                # Update Settings
                database.child("devices").child("controls").update({
                    "target_temp": new_temp,
                    "mode": new_mode,
                    "min_humid": 85.0,
                    "max_humid": 95.0
                })
                
                if new_mode == "auto":
                    messages.info(request, f"System set to AUTOMATIC (Target: {new_temp}°C).")
                else:
                    messages.info(request, "System set to MANUAL control.")

        except Exception as e:
            messages.error(request, f"Command failed: {str(e)}")
        
        return redirect("remote")

    return render(request, "accounts/remote.html", {
        "devices": devices,
        "current_temperature": current_temperature,
        "current_humidity": current_humidity
    })

def get_sensor_data(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'unauthorized'}, status=401)

    try:
        current_ts = int(time.time())

        # 1. Fetch live sensor data
        live_ref = realtime_db.reference("sensors")
        live_data = live_ref.get()

        # ⬇ AUTOMATIC HISTORY SAVING HERE ⬇
        if live_data:
            last_save_ref = realtime_db.reference("historical_data")
            last = last_save_ref.order_by_child("timestamp").limit_to_last(1).get()

            should_save = False

            if not last:
                should_save = True
            else:
                for key, item in last.items():
                    last_ts = int(item.get("timestamp", 0))
                    # Save every 5 minutes
                    if current_ts - last_ts >= 300:
                        should_save = True

            if should_save:
                entry = {
                    "temperature": float(live_data.get("temperature", 0)),
                    "humidity": float(live_data.get("humidity", 0)),
                    "timestamp": current_ts
                }
                last_save_ref.child(str(current_ts)).set(entry)
                print("Saved historical:", entry)

        # 2. Format output for dashboard
        formatted_data = []
        ref = realtime_db.reference("historical_data")
        snapshot = ref.order_by_child("timestamp").limit_to_last(20).get()

        if snapshot:
            for key, val in snapshot.items():
                ts = val.get("timestamp", 0)
                formatted_data.append({
                    "timestamp": ts,
                    "date_str": datetime.fromtimestamp(ts).strftime('%H:%M:%S'),
                    "temperature": val.get("temperature", 0),
                    "humidity": val.get("humidity", 0),
                })

        # Add live reading on top
        if live_data:
            formatted_data.append({
                "timestamp": current_ts,
                "date_str": datetime.fromtimestamp(current_ts).strftime('%H:%M:%S'),
                "temperature": float(live_data.get("temperature", 0)),
                "humidity": float(live_data.get("humidity", 0)),
                "is_live": True
            })

        formatted_data.sort(key=lambda x: x["timestamp"], reverse=True)

        return JsonResponse({"sensor_data": formatted_data})

    except Exception as e:
        print("Error:", e)
        return JsonResponse({"error": str(e)}, status=500)


    
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

def save_scan_result_to_firebase(user_id, result, image_name, confidence=0, analysis_type='upload'):
    """Enhanced function to save scan results with additional metadata"""
    try:
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
        
        # Save to Firestore
        db.collection("scans").add(scan_data)
        
        print(f"Saved scan result to Firebase: {scan_data}")
        return True
        
    except Exception as e:
        print(f"Error saving scan result to Firebase: {str(e)}")
        return False
    
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
        
        # Limit CPU threads to reduce memory usage
        tf.config.threading.set_intra_op_parallelism_threads(1)
        tf.config.threading.set_inter_op_parallelism_threads(1)
        
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
        
        # Make prediction with minimal memory usage
        predictions = model.predict(img_array, verbose=0, batch_size=1)  # Reduced batch size
        
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

# REST OF YOUR CODE REMAINS EXACTLY THE SAME - NO CHANGES BELOW THIS LINE
def get_user_scans(request):
    """Get only the current user's scan results"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_id = request.session['user']['localId']
        scans = db.collection("scans").where("user_id", "==", user_id).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        
        scan_list = []
        for doc in scans:
            data = doc.to_dict()
            data['id'] = doc.id
            scan_list.append(data)
        
        return JsonResponse({'scans': scan_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
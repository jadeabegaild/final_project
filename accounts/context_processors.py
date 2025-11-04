def firebase_user(request):
    firebase_user_data = request.session.get('firebase_user', {})
    return {
        'firebase_user': firebase_user_data
    }
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import json

from config import Config
from database import init_database
from models import User, Admin
from utils import get_user_statistics, get_system_stats, generate_report

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # Enable CORS for all routes

# Initialize database
init_database()

# Create user_data directory if it doesn't exist
os.makedirs(Config.USER_DATA_PATH, exist_ok=True)

@app.route('/')
def index():
    return jsonify({
        'message': 'BLA Location Tracking Server',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'storage_structure': 'Date-based folders (DD_MM_YYYY)'
    })

# ==================== USER ENDPOINTS ====================

@app.route('/api/user/register', methods=['POST'])
def register_user():
    """Register a new user"""
    data = request.json
    
    required_fields = ['username', 'name', 'phone', 'email', 'password']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        return jsonify({'error': f'Missing required fields: {missing}'}), 400
    
    result = User.create(
        username=data['username'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
        password=data['password']
    )
    
    if result['success']:
        return jsonify({
            'message': 'User registered successfully',
            'user_id': result['user_id'],
            'username': result['username']
        }), 201
    else:
        return jsonify({'error': result['error']}), 400

@app.route('/api/user/login', methods=['POST'])
def login_user():
    """User login"""
    data = request.json
    
    if not data or ('username' not in data and 'email' not in data) or 'password' not in data:
        return jsonify({'error': 'Missing credentials'}), 400
    
    identifier = data.get('username') or data.get('email')
    user = User.authenticate(identifier, data['password'])
    
    if user:
        # Remove password from response
        user.pop('password', None)
        return jsonify({
            'message': 'Login successful',
            'user': user
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/user/location', methods=['POST'])
def save_location():
    """Save user location (called every 2 seconds from Flutter)"""
    data = request.json
    
    if not data or 'user_id' not in data or 'location' not in data or 'datetime' not in data:
        return jsonify({'error': 'Invalid location data'}), 400
    
    # Get username from user_id
    user = User.get_user_by_id(data['user_id'])
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update last active
    User.update_last_active(data['user_id'])
    
    # Check if this is a submitted location
    is_submitted = data.get('submitted', False)
    
    # Save location with submit flag
    location_data = {
        'latitude': data['location']['lat'],
        'longitude': data['location']['long'],
        'datetime': data['datetime']
    }
    
    if User.save_location_with_submit(user['username'], location_data, is_submitted):
        # Get today's folder path for response
        today = datetime.now()
        date_str = today.strftime('%d_%m_%Y')
        json_path = User.get_daily_json_path(user['username'], today)
        
        # Load today's data to check if this is first location
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                user_data = json.load(f)
            
            response = {
                'message': 'Location saved',
                'date': date_str,
                'is_first_today': len(user_data.get('routes', [])) == 0,
                'total_today': len(user_data.get('routes', [])) + 1,
                'submitted': is_submitted
            }
        else:
            response = {
                'message': 'Location saved',
                'date': date_str,
                'is_first_today': True,
                'total_today': 1,
                'submitted': is_submitted
            }
        
        return jsonify(response), 200
    else:
        return jsonify({'error': 'Failed to save location'}), 500

@app.route('/api/user/check-today/<int:user_id>', methods=['GET'])
def check_today_data(user_id):
    """Check if user has data for today"""
    user = User.get_user_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check today's JSON file
    today = datetime.now()
    json_path = User.get_daily_json_path(user['username'], today)
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        return jsonify({
            'has_data': True,
            'date': today.strftime('%d_%m_%Y'),
            'start_points': len(data.get('start_points', [])),
            'end_points': len(data.get('end_points', [])),
            'route_points': len(data.get('routes', []))
        }), 200
    else:
        return jsonify({
            'has_data': False,
            'date': today.strftime('%d_%m_%Y'),
            'message': 'No data for today'
        }), 200

@app.route('/api/user/dates/<int:user_id>', methods=['GET'])
def get_user_dates(user_id):
    """Get list of dates where user has location data"""
    user = User.get_user_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    dates = User.get_user_dates(user['username'])
    
    return jsonify({
        'username': user['username'],
        'dates': dates,
        'count': len(dates)
    }), 200

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/login', methods=['POST'])
def login_admin():
    """Admin login"""
    data = request.json
    
    if not data or ('username' not in data and 'email' not in data) or 'password' not in data:
        return jsonify({'error': 'Missing credentials'}), 400
    
    identifier = data.get('username') or data.get('email')
    admin = Admin.authenticate(identifier, data['password'])
    
    if admin:
        admin.pop('password', None)
        return jsonify({
            'message': 'Admin login successful',
            'admin': admin
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/admin/members', methods=['GET'])
def get_members():
    """Get member list for admin"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', None)
    
    result = Admin.get_member_list(page, per_page, search)
    
    # Remove passwords from response
    for member in result['members']:
        if 'password' in member:
            del member['password']
    
    return jsonify(result), 200

@app.route('/api/admin/search', methods=['GET'])
def search_user():
    """Search for a specific user"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    user = Admin.search_user(query)
    
    if user:
        return jsonify({'user': user}), 200
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/admin/user-locations/<username>', methods=['GET'])
def get_user_locations(username):
    """Get user locations for admin"""
    date = request.args.get('date', None)
    
    # Convert YYYY-MM-DD to DD_MM_YYYY if needed
    if date and '-' in date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date = date_obj.strftime('%d_%m_%Y')
        except:
            pass
    
    locations = User.get_user_locations(username, date)
    
    if locations is not None:
        return jsonify(locations), 200
    else:
        return jsonify({'error': 'No location data found'}), 404

@app.route('/api/admin/user-locations/updates/<username>', methods=['GET'])
def get_location_updates(username):
    """Get real-time updates for admin"""
    date = request.args.get('date', None)
    
    # Convert YYYY-MM-DD to DD_MM_YYYY if needed
    if date and '-' in date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date = date_obj.strftime('%d_%m_%Y')
        except:
            pass
    
    locations = User.get_user_locations(username, date)
    
    if locations and locations.get('end_points'):
        latest_end = locations['end_points'][-1]
        return jsonify({
            'latest_end': latest_end,
            'date': locations.get('date')
        }), 200
    else:
        return jsonify({'error': 'No updates'}), 404

@app.route('/api/admin/user-statistics/<username>', methods=['GET'])
def get_user_statistics_endpoint(username):
    """Get statistics for a user"""
    stats = get_user_statistics(username)
    return jsonify(stats), 200

@app.route('/api/admin/user-dates/<username>', methods=['GET'])
def get_user_available_dates(username):
    """Get list of dates where user has data"""
    dates = User.get_user_dates(username)
    
    return jsonify({
        'username': username,
        'dates': dates,
        'count': len(dates)
    }), 200

@app.route('/api/admin/generate-report/<username>', methods=['GET'])
def generate_user_report(username):
    """Generate report for user between dates"""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Start and end dates required'}), 400
    
    report = generate_report(username, start_date, end_date)
    
    if report:
        return jsonify(report), 200
    else:
        return jsonify({'error': 'Failed to generate report'}), 404

# ==================== UTILITY ENDPOINTS ====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    from database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as total_admins FROM admins')
    total_admins = cursor.fetchone()['total_admins']
    
    today = datetime.now().date()
    cursor.execute('SELECT COUNT(*) as active_today FROM users WHERE last_active = ?', (today,))
    active_today = cursor.fetchone()['active_today']
    
    conn.close()
    
    # Get storage stats
    storage_stats = get_system_stats()
    
    return jsonify({
        'total_users': total_users,
        'total_admins': total_admins,
        'active_today': active_today,
        'storage_path': Config.USER_DATA_PATH,
        'storage_stats': storage_stats
    }), 200

@app.route('/api/cleanup', methods=['POST'])
def trigger_cleanup():
    """Manually trigger cleanup (admin only)"""
    # In production, add authentication here
    days = request.json.get('days', 30) if request.json else 30
    
    from utils import cleanup_old_data
    cleanup_old_data(days)
    
    return jsonify({'message': f'Cleanup completed for data older than {days} days'}), 200

@app.route('/api/system-info', methods=['GET'])
def system_info():
    """Get system information"""
    return jsonify({
        'server_time': datetime.now().isoformat(),
        'storage_structure': 'Date-based folders (DD_MM_YYYY)',
        'user_data_path': os.path.abspath(Config.USER_DATA_PATH),
        'api_version': '2.0',
        'features': [
            'Date-based storage',
            'Real-time tracking',
            'Historical data',
            'User statistics',
            'Report generation'
        ]
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("BLA Location Tracking Server v2.0")
    print("=" * 60)
    print("\nStarting server...")
    print("Default admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nStorage Structure:")
    print("  user_data/[username]/[DD_MM_YYYY]/[DD_MM_YYYY].json")
    print("\nServer will be available at: http://localhost:5000")
    print("=" * 60)
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
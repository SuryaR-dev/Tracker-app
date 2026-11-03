import json
import os
from datetime import datetime
from database import get_db_connection
import bcrypt

class User:
    @staticmethod
    def create(username, name, phone, email, password):
        """Create a new user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            cursor.execute('''
                INSERT INTO users (username, name, phone, email, password)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, name, phone, email, hashed))
            conn.commit()
            
            # Create user folder
            user_id = cursor.lastrowid
            User.create_user_folders(username)
            
            return {'success': True, 'user_id': user_id, 'username': username}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def create_user_folders(username):
        """Create user folder structure"""
        user_folder = f'user_data/{username}'
        os.makedirs(user_folder, exist_ok=True)
        
        # Note: Date folders will be created dynamically when locations are saved
    
    @staticmethod
    def get_date_folder_path(username, date=None):
        """Get the path for a specific date folder"""
        if date is None:
            date = datetime.now().strftime('%d_%m_%Y')
        elif isinstance(date, datetime):
            date = date.strftime('%d_%m_%Y')
        elif isinstance(date, str):
            # If date is in YYYY-MM-DD format, convert to DD_MM_YYYY
            if '-' in date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    date = date_obj.strftime('%d_%m_%Y')
                except:
                    pass
        
        return f'user_data/{username}/{date}'
    
    @staticmethod
    def get_daily_json_path(username, date=None):
        """Get the JSON file path for a specific date"""
        date_folder = User.get_date_folder_path(username, date)
        if date is None:
            date = datetime.now().strftime('%d_%m_%Y')
        elif isinstance(date, datetime):
            date = date.strftime('%d_%m_%Y')
        elif isinstance(date, str) and '-' in date:
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                date = date_obj.strftime('%d_%m_%Y')
            except:
                pass
        
        return f'{date_folder}/{date}.json'
    
   # Add this method to the User class in models.py

    @staticmethod
    def save_location_with_submit(username, location_data, is_submitted=False):
        """Save location data to date-specific JSON file with submit flag"""
        try:
            # Get date from the location timestamp
            timestamp_str = location_data['datetime']
            # Handle different timestamp formats
            if 'Z' in timestamp_str:
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            
            timestamp = datetime.fromisoformat(timestamp_str)
            date_str = timestamp.strftime('%d_%m_%Y')
            
            # Create date folder if it doesn't exist
            date_folder = User.get_date_folder_path(username, timestamp)
            os.makedirs(date_folder, exist_ok=True)
            
            # JSON file path for this date
            json_path = User.get_daily_json_path(username, timestamp)
            
            # Load or create daily location data
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
            else:
                # Initialize new daily file
                data = {
                    'username': username,
                    'date': date_str,
                    'start_points': [],
                    'end_points': [],
                    'routes': []
                }
            
            # Create location entry with submit flag
            location_entry = {
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'timestamp': location_data['datetime'],
                'type': 'route',  # Will be updated if it's start or end
                'submitted': is_submitted  # Add submit flag (True/False)
            }
            
            # Check if this is the first location of the day
            if len(data['routes']) == 0 and len(data['start_points']) == 0:
                location_entry['type'] = 'start'
                data['start_points'].append(location_entry)
                print(f"Added START point for {username} on {date_str} (submitted: {is_submitted})")
            else:
                # Add to routes
                data['routes'].append(location_entry)
                
                # Update end point (always keep the latest as end)
                # Create end entry from the latest location
                end_entry = {
                    'latitude': location_data['latitude'],
                    'longitude': location_data['longitude'],
                    'timestamp': location_data['datetime'],
                    'type': 'end',
                    'submitted': is_submitted  # Add submit flag to end point
                }
                data['end_points'] = [end_entry]
                print(f"Updated END point for {username} on {date_str} (submitted: {is_submitted})")
            
            # Save to file
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving location: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_user_locations(username, date=None):
        """Get user locations for specific date"""
        try:
            json_path = User.get_daily_json_path(username, date)
            
            if not os.path.exists(json_path):
                # Return empty structure instead of None
                date_str = date if date else datetime.now().strftime('%d_%m_%Y')
                if isinstance(date, datetime):
                    date_str = date.strftime('%d_%m_%Y')
                
                return {
                    'username': username,
                    'date': date_str,
                    'start_points': [],
                    'end_points': [],
                    'routes': []
                }
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            print(f"Error getting locations: {e}")
            return None
    
    @staticmethod
    def get_user_dates(username):
        """Get list of dates where user has location data"""
        user_folder = f'user_data/{username}'
        dates = []
        
        if os.path.exists(user_folder):
            for item in os.listdir(user_folder):
                item_path = os.path.join(user_folder, item)
                if os.path.isdir(item_path) and '_' in item:  # Date folders have format DD_MM_YYYY
                    # Check if JSON file exists in folder
                    json_path = os.path.join(item_path, f"{item}.json")
                    if os.path.exists(json_path):
                        # Convert DD_MM_YYYY to YYYY-MM-DD for API consistency
                        try:
                            day, month, year = map(int, item.split('_'))
                            api_date = f"{year:04d}-{month:02d}-{day:02d}"
                            dates.append({
                                'folder': item,
                                'api_date': api_date,
                                'display': f"{day:02d}/{month:02d}/{year}"
                            })
                        except:
                            dates.append({
                                'folder': item,
                                'api_date': item,
                                'display': item
                            })
        
        # Sort by date (most recent first)
        dates.sort(key=lambda x: x['folder'], reverse=True)
        return dates
    
    @staticmethod
    def authenticate(username_or_email, password):
        """Authenticate user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE username = ? OR email = ?
        ''', (username_or_email, username_or_email))
        
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return dict(user)
        return None
    
    @staticmethod
    def update_last_active(user_id):
        """Update user's last active date"""
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().date()
        
        cursor.execute('''
            UPDATE users 
            SET last_active = ?, is_active = 1 
            WHERE id = ?
        ''', (today, user_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None

class Admin:
    @staticmethod
    def authenticate(username_or_email, password):
        """Authenticate admin"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM admins 
            WHERE username = ? OR email = ?
        ''', (username_or_email, username_or_email))
        
        admin = cursor.fetchone()
        conn.close()
        
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password']):
            return dict(admin)
        return None
    
    @staticmethod
    def get_member_list(page=1, per_page=10, search=None):
        """Get paginated member list"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Base query
        if search:
            cursor.execute('''
                SELECT *, 
                       CASE WHEN last_active = ? THEN 1 ELSE 0 END as active_today
                FROM users 
                WHERE username LIKE ? OR name LIKE ? OR email LIKE ?
                ORDER BY username
                LIMIT ? OFFSET ?
            ''', (today, f'%{search}%', f'%{search}%', f'%{search}%', per_page, (page-1)*per_page))
        else:
            cursor.execute('''
                SELECT *, 
                       CASE WHEN last_active = ? THEN 1 ELSE 0 END as active_today
                FROM users 
                ORDER BY username
                LIMIT ? OFFSET ?
            ''', (today, per_page, (page-1)*per_page))
        
        members = cursor.fetchall()
        
        # Get total counts
        cursor.execute('SELECT COUNT(*) as total FROM users')
        total = cursor.fetchone()['total']
        
        cursor.execute('''
            SELECT COUNT(*) as active_today 
            FROM users 
            WHERE last_active = ?
        ''', (today,))
        active_today = cursor.fetchone()['active_today']
        
        conn.close()
        
        return {
            'members': [dict(member) for member in members],
            'total_members': total,
            'active_today': active_today,
            'inactive_today': total - active_today,
            'page': page,
            'per_page': per_page
        }
    
    @staticmethod
    def search_user(query):
        """Search for a specific user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, name, phone, email, last_active 
            FROM users 
            WHERE username = ? OR email = ? OR name LIKE ?
        ''', (query, query, f'%{query}%'))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
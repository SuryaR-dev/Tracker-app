import os
import json
import shutil
from datetime import datetime, timedelta
from models import User

def cleanup_old_data(days=30):
    """Clean up location data older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime('%d_%m_%Y')
    
    user_folder = 'user_data'
    
    if not os.path.exists(user_folder):
        return
    
    print(f"Cleaning up data older than {cutoff_str}")
    deleted_count = 0
    
    for username in os.listdir(user_folder):
        user_path = os.path.join(user_folder, username)
        if not os.path.isdir(user_path):
            continue
        
        for date_folder in os.listdir(user_path):
            folder_path = os.path.join(user_path, date_folder)
            if not os.path.isdir(folder_path):
                continue
            
            # Check if folder is a date folder
            try:
                # Parse date from folder name (DD_MM_YYYY)
                day, month, year = map(int, date_folder.split('_'))
                folder_date = datetime(year, month, day)
                
                if folder_date < cutoff_date:
                    print(f"Removing old data: {username}/{date_folder}")
                    shutil.rmtree(folder_path)
                    deleted_count += 1
            except (ValueError, IndexError):
                # Not a date folder, skip
                continue
    
    print(f"Cleanup completed. Deleted {deleted_count} old folders.")

def generate_report(username, start_date, end_date):
    """Generate location report for a user between dates"""
    user_folder = f'user_data/{username}'
    
    if not os.path.exists(user_folder):
        return None
    
    # Convert dates to datetime objects
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        except:
            try:
                start_date = datetime.strptime(start_date, '%d_%m_%Y')
            except:
                return None
    
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except:
            try:
                end_date = datetime.strptime(end_date, '%d_%m_%Y')
            except:
                return None
    
    report_data = {
        'username': username,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'dates': []
    }
    
    current_date = start_date
    total_routes = 0
    total_start_points = 0
    total_end_points = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%d_%m_%Y')
        json_path = os.path.join(user_folder, date_str, f"{date_str}.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                day_data = json.load(f)
                report_data['dates'].append(day_data)
                total_routes += len(day_data.get('routes', []))
                total_start_points += len(day_data.get('start_points', []))
                total_end_points += len(day_data.get('end_points', []))
        
        current_date += timedelta(days=1)
    
    report_data['summary'] = {
        'total_days': len(report_data['dates']),
        'total_routes': total_routes,
        'total_start_points': total_start_points,
        'total_end_points': total_end_points
    }
    
    return report_data

def get_user_statistics(username):
    """Get statistics for a user"""
    user_folder = f'user_data/{username}'
    
    if not os.path.exists(user_folder):
        return {
            'username': username,
            'total_days_active': 0,
            'total_locations': 0,
            'first_active': None,
            'last_active': None,
            'average_locations_per_day': 0
        }
    
    total_locations = 0
    active_dates = []
    dates_with_data = []
    
    for date_folder in os.listdir(user_folder):
        folder_path = os.path.join(user_folder, date_folder)
        if not os.path.isdir(folder_path):
            continue
        
        json_path = os.path.join(folder_path, f"{date_folder}.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                day_locations = len(data.get('routes', []))
                total_locations += day_locations
                active_dates.append(date_folder)
                if day_locations > 0:
                    dates_with_data.append(date_folder)
    
    active_dates.sort()
    
    # Convert folder dates to display format
    first_active = None
    last_active = None
    
    if active_dates:
        try:
            day, month, year = map(int, active_dates[0].split('_'))
            first_active = f"{year:04d}-{month:02d}-{day:02d}"
        except:
            first_active = active_dates[0]
        
        try:
            day, month, year = map(int, active_dates[-1].split('_'))
            last_active = f"{year:04d}-{month:02d}-{day:02d}"
        except:
            last_active = active_dates[-1]
    
    avg_locations = total_locations / len(active_dates) if active_dates else 0
    
    return {
        'username': username,
        'total_days_active': len(active_dates),
        'total_locations': total_locations,
        'first_active': first_active,
        'last_active': last_active,
        'average_locations_per_day': round(avg_locations, 2)
    }

def get_system_stats():
    """Get overall system statistics"""
    user_folder = 'user_data'
    total_users_with_data = 0
    total_location_files = 0
    total_locations = 0
    
    if os.path.exists(user_folder):
        for username in os.listdir(user_folder):
            user_path = os.path.join(user_folder, username)
            if not os.path.isdir(user_path):
                continue
            
            has_data = False
            for date_folder in os.listdir(user_path):
                folder_path = os.path.join(user_path, date_folder)
                if not os.path.isdir(folder_path):
                    continue
                
                json_path = os.path.join(folder_path, f"{date_folder}.json")
                if os.path.exists(json_path):
                    total_location_files += 1
                    has_data = True
                    
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        total_locations += len(data.get('routes', []))
            
            if has_data:
                total_users_with_data += 1
    
    return {
        'total_users_with_data': total_users_with_data,
        'total_location_files': total_location_files,
        'total_location_points': total_locations,
        'storage_path': os.path.abspath(user_folder)
    }
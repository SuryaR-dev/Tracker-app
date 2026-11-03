#!/usr/bin/env python3
from app import app

import os

if __name__ == '__main__':
    print("=" * 60)
    print("BLA Location Tracking Server v2.0")
    print("=" * 60)
    
    # Create necessary directories
    os.makedirs('database', exist_ok=True)
    os.makedirs('user_data', exist_ok=True)
    
    
    print("\nDefault admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nStorage Structure:")
    print("  user_data/[username]/[DD_MM_YYYY]/[DD_MM_YYYY].json")
    print("\nServer will be available at: http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
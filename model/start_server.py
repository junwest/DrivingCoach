#!/usr/bin/env python3
"""
ngrok launcher for DrivingCoach AI Server
Automatically starts Flask server and creates ngrok tunnel
"""

import subprocess
import time
import requests
import json
from pathlib import Path

def start_server_with_ngrok():
    """Start Flask server and create ngrok tunnel"""
    
    print("="*60)
    print("🚗 DrivingCoach AI Server with ngrok")
    print("="*60)
    
    # Start Flask server in background
    print("\n1️⃣ Starting Flask server...")
    server_process = subprocess.Popen(
        ['python', 'src/server.py'],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Start ngrok
    print("\n2️⃣ Starting ngrok tunnel...")
    ngrok_process = subprocess.Popen(
        ['ngrok', 'http', '5000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for ngrok to start
    time.sleep(2)
    
    # Get ngrok public URL
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        
        if tunnels:
            public_url = tunnels[0]['public_url']
            print(f"\n✅ Server is running!")
            print("="*60)
            print(f"📍 Local URL:  http://localhost:5000")
            print(f"🌐 Public URL: {public_url}")
            print("="*60)
            print("\n📱 Use the Public URL in your mobile app!")
            print("\nAPI Endpoints:")
            print(f"  GET  {public_url}/")
            print(f"  POST {public_url}/api/analyze/image")
            print(f"  POST {public_url}/api/analyze/audio")
            print(f"  POST {public_url}/api/analyze/scenario")
            print("\n⏹️  Press Ctrl+C to stop")
            print("="*60 + "\n")
            
        else:
            print("⚠️  Could not get ngrok URL")
            
    except Exception as e:
        print(f"⚠️  Error getting ngrok info: {e}")
        print("📍 Server running at: http://localhost:5000")
    
    try:
        # Keep running
        server_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        server_process.terminate()
        ngrok_process.terminate()
        print("✅ Server stopped")

if __name__ == '__main__':
    start_server_with_ngrok()

#!/usr/bin/env python3
"""
ngrok launcher for DrivingCoach FastAPI Server
Automatically starts server with uvicorn and creates ngrok tunnel
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def start_server_with_ngrok():
    """Start FastAPI server with uvicorn and create ngrok tunnel"""
    
    print("="*60)
    print("🚗 DrivingCoach FastAPI Server with ngrok")
    print("="*60)
    
    # Start uvicorn server in background
    print("\n1️⃣ Starting FastAPI server with uvicorn...")
    server_process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'src.server:app', '--host', '0.0.0.0', '--port', '5000'],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for server to start
    print("   Waiting for server to initialize...")
    time.sleep(5)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:5000/', timeout=3)
        if response.status_code == 200:
            print("   ✅ Server is running!")
        else:
            print("   ⚠️  Server responded but with unexpected status")
    except:
        print("   ⚠️  Server may still be starting...")
    
    # Start ngrok
    print("\n2️⃣ Starting ngrok tunnel...")
    ngrok_process = subprocess.Popen(
        ['ngrok', 'http', '5000', '--log=stdout'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for ngrok to start
    print("   Waiting for ngrok to initialize...")
    time.sleep(3)
    
    # Get ngrok public URL
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        tunnels = response.json()['tunnels']
        
        if tunnels:
            public_url = tunnels[0]['public_url']
            print(f"\n{'='*60}")
            print("✅ Server is running!")
            print(f"{'='*60}")
            print(f"📍 Local URL:  http://localhost:5000")
            print(f"🌐 Public URL: {public_url}")
            print(f"{'='*60}")
            print(f"\n📱 Use the Public URL in your mobile app!")
            print(f"\n📚 API Documentation:")
            print(f"  Swagger UI: {public_url}/docs")
            print(f"  ReDoc:      {public_url}/redoc")
            print(f"\n📡 API Endpoints:")
            print(f"  GET  {public_url}/")
            print(f"  POST {public_url}/api/analyze/image")
            print(f"  POST {public_url}/api/analyze/audio")
            print(f"  POST {public_url}/api/analyze/scenario")
            print(f"\n⏹️  Press Ctrl+C to stop")
            print(f"{'='*60}\n")
            
        else:
            print("⚠️  Could not get ngrok URL")
            print(f"📍 Server running at: http://localhost:5000")
            print(f"📚 Docs: http://localhost:5000/docs")
            
    except Exception as e:
        print(f"⚠️  Error getting ngrok info: {e}")
        print(f"📍 Server running at: http://localhost:5000")
        print(f"📚 Docs: http://localhost:5000/docs")
    
    try:
        # Keep running and show server output
        print("\n📊 Server logs:\n")
        for line in iter(server_process.stdout.readline, ''):
            if line:
                print(f"   {line.rstrip()}")
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        server_process.terminate()
        ngrok_process.terminate()
        print("✅ Server stopped")

if __name__ == '__main__':
    start_server_with_ngrok()

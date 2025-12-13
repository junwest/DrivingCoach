#!/usr/bin/env python3
"""
Quick test script for DrivingCoach FastAPI Server
Tests all API endpoints without needing actual model files
"""

import requests
import base64
import json
from PIL import Image
import io
import numpy as np

# Server URL (change this to your ngrok URL when running)
BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("1️⃣ Testing Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_image_analysis():
    """Test image analysis endpoint"""
    print("\n" + "="*60)
    print("2️⃣ Testing Image Analysis")
    print("="*60)
    
    try:
        # Create a dummy image (RGB, 640x480)
        img = Image.new('RGB', (640, 480), color=(73, 109, 137))
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Send request
        response = requests.post(
            f"{BASE_URL}/api/analyze/image",
            json={"image": img_base64},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Objects detected: {len(result['objects'])}")
            print(f"Lane detected: {result['lane']['detected']}")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_audio_analysis():
    """Test audio analysis endpoint"""
    print("\n" + "="*60)
    print("3️⃣ Testing Audio Analysis")
    print("="*60)
    
    try:
        # Create dummy audio data (2 seconds of silence)
        sample_rate = 16000
        duration = 2.0
        audio_data = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        # Convert to bytes and base64
        audio_bytes = audio_data.tobytes()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Send request  
        response = requests.post(
            f"{BASE_URL}/api/analyze/audio",
            json={
                "audio": audio_base64,
                "sample_rate": sample_rate
            },
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Detected: {result['label']} ({result['confidence']:.2f})")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_scenario_analysis():
    """Test scenario analysis endpoint"""
    print("\n" + "="*60)
    print("4️⃣ Testing Scenario Analysis")
    print("="*60)
    
    try:
        # Test case: Horn with pedestrian (Scenario 9)
        response = requests.post(
            f"{BASE_URL}/api/analyze/scenario",
            json={
                "horn": True,
                "pedestrian": True,
                "lane_change": False,
                "blinker": False,
                "wiper": False,
                "tailgating": False,
                "sudden_stop": False,
                "left_signal": False,
                "right_signal": False
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Scenario ID: {result['scenario_id']}")
            print(f"Message: {result['message']}")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪 DrivingCoach API Test Suite")
    print("="*60)
    print(f"Testing server at: {BASE_URL}")
    print("="*60)
    
    results = {
        "Health Check": test_health_check(),
        "Image Analysis": test_image_analysis(),
        "Audio Analysis": test_audio_analysis(),
        "Scenario Analysis": test_scenario_analysis()
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:25s} {status}")
    
    total = len(results)
    passed = sum(results.values())
    print("="*60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()

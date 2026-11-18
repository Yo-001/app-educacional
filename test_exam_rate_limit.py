#!/usr/bin/env python3
"""
Test script to verify the /exam endpoint rate limiting implementation.
This script will:
1. Start the backend server in the background
2. Make requests to the /exam endpoint to test rate limiting
3. Verify that we get 200 responses followed by 429 after hitting the limit
"""
import subprocess
import time
import requests
import json
import os
import sys
from threading import Thread

# Set the OpenRouter API key from secrets.json
with open('backend/secrets.json', 'r') as f:
    secrets = json.load(f)
    os.environ['OPENROUTER_API_KEY'] = secrets['OPENROUTER_API_KEY']

# Server configuration
SERVER_PORT = 8080
SERVER_URL = f"http://localhost:{SERVER_PORT}"
SERVER_PATH = "backend/app.py"

# Rate limit configuration (from app.py)
RATE_LIMIT = 30  # Requests per hour per IP for /exam endpoint
WINDOW = 3600    # Time window in seconds (1 hour)

# Test data
TEST_TEXT = """
O gato sentou-se na janela e olhou para fora. Ele viu um pássaro cantando.
O pássaro era colorido e brilhante com penas de arco-íris.
O gato queria pegar o pássaro, mas ele voou para longe.
O gato agora está triste e volta para casa.
"""

TEST_TOPICS = "animais, emoções, cor"

def start_server():
    """Start the backend server in the background."""
    print("Starting backend server...")
    # Run the server in the background
    server_process = subprocess.Popen(
        [sys.executable, SERVER_PATH],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=os.environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return server_process

def stop_server(server_process):
    """Stop the backend server."""
    print("Stopping backend server...")
    server_process.terminate()
    server_process.wait()

def wait_for_server():
    """Wait for the server to start and become responsive."""
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f"{SERVER_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"Server is responsive (attempt {i+1}/{max_attempts})")
                return True
        except requests.exceptions.ConnectionError:
            if i < max_attempts - 1:
                print(f"Waiting for server to start... (attempt {i+1}/{max_attempts})")
                time.sleep(1)
            else:
                print(f"Failed to connect to server after {max_attempts} attempts")
                return False
    return False

def make_exam_request(request_num):
    """Make a single request to the /exam endpoint."""
    payload = {
        "text": TEST_TEXT,
        "topics": TEST_TOPICS
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Forwarded-For': f'192.168.1.{request_num % 256}'  # Different IP for testing
    }
    
    try:
        response = requests.post(
            f"{SERVER_URL}/exam",
            json=payload,
            headers=headers,
            timeout=60
        )
        return response.status_code, response.json() if response.content else None
    except Exception as e:
        return None, str(e)

def main():
    """Main test function."""
    print("Starting /exam endpoint rate limit test")
    print(f"Rate limit: {RATE_LIMIT} requests per hour per IP")
    print(f"Time window: {WINDOW} seconds ({WINDOW/3600} hours)")
    
    # Start the server
    server_process = start_server()
    
    try:
        # Wait for server to start
        if not wait_for_server():
            print("ERROR: Server failed to start")
            return 1
        
        print("\n=== Testing /exam endpoint rate limiting ===")
        
        # Test 1: Make requests until we hit the rate limit
        print(f"\nTest 1: Making {RATE_LIMIT} consecutive requests to hit the rate limit...")
        successful_requests = 0
        rate_limit_hit = False
        
        for i in range(RATE_LIMIT):
            status_code, response_data = make_exam_request(i)
            
            if status_code == 200:
                successful_requests += 1
                print(f"  Request {i+1}: 200 OK")
            elif status_code == 429:
                rate_limit_hit = True
                print(f"  Request {i+1}: 429 Rate Limited (expected after hitting limit)")
                break
            else:
                print(f"  Request {i+1}: {status_code} - {response_data}")
        
        # Test 2: Verify we got the expected results
        print(f"\n=== Test Results ===")
        print(f"Successful requests before rate limit: {successful_requests}/{RATE_LIMIT}")
        print(f"Rate limit was hit: {rate_limit_hit}")
        
        if successful_requests == RATE_LIMIT and rate_limit_hit:
            print("✅ SUCCESS: Rate limiting is working correctly!")
            print("   - All requests were accepted (200) up to the limit")
            print("   - The rate limit was properly enforced (429 after hitting limit)")
        elif successful_requests < RATE_LIMIT:
            print("⚠️  WARNING: Rate limit was hit before expected number of requests")
            print(f"   - Only {successful_requests} requests were accepted before rate limit")
        else:
            print("❌ FAILURE: Rate limiting is not working as expected")
        
        return 0 if (successful_requests == RATE_LIMIT and rate_limit_hit) else 1
        
    finally:
        # Stop the server
        stop_server(server_process)
        print("\nTest completed. Server stopped.")

if __name__ == "__main__":
    sys.exit(main())
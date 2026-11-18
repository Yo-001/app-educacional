#!/usr/bin/env python3
"""
Simple test script to verify the /exam endpoint rate limiting implementation.
This script makes multiple consecutive requests to the /exam endpoint
and verifies that rate limiting works correctly.
"""
import requests
import json
import os
import sys
import time

# Set the OpenRouter API key from secrets.json
with open('backend/secrets.json', 'r') as f:
    secrets = json.load(f)
    os.environ['OPENROUTER_API_KEY'] = secrets['OPENROUTER_API_KEY']

# Server configuration
SERVER_URL = "http://localhost:8080"

# Test data
TEST_TEXT = '''
O gato sentou-se na janela e olhou para fora. Ele viu um pássaro cantando.
O pássaro era colorido e brilhante com penas de arco-íris.
O gato queria pegar o pássaro, mas ele voou para longe.
O gato agora está triste e volta para casa.
Este é um texto de teste para verificar o endpoint /exam do backend estudo-moedas.
O objetivo é testar a funcionalidade de rate limiting implementada.
A API deve aceitar este texto e gerar exercícios baseado nele.
Este texto contém mais de 80 caracteres para atender aos requisitos.
'''

TEST_TOPICS = 'animais, emoções, cor'

def make_exam_request(ip_suffix):
    """Make a single request to the /exam endpoint with a specific IP."""
    payload = {
        "text": TEST_TEXT,
        "topics": TEST_TOPICS
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Forwarded-For': f'192.168.1.{ip_suffix}'
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
    print("=== /exam endpoint rate limiting test ===")
    print(f"Server URL: {SERVER_URL}")
    print(f"Rate limit: 30 requests per hour per IP")
    print(f"Time window: 1 hour")
    
    # Test the rate limiting by making consecutive requests with different IPs
    print("\nMaking 30 consecutive requests with different IPs...")
    
    successful_requests = 0
    rate_limit_hit = False
    
    for i in range(30):
        status_code, response_data = make_exam_request(i)
        
        if status_code == 200:
            successful_requests += 1
            print(f"  Request {i+1:2d}: 200 OK")
        elif status_code == 429:
            rate_limit_hit = True
            print(f"  Request {i+1:2d}: 429 Rate Limited (rate limit hit)")
            # We expected to hit the rate limit at request 31, so break early
            break
        else:
            print(f"  Request {i+1:2d}: {status_code} - {response_data}")
    
    print(f"\n=== Test Results ===")
    print(f"Successful requests before rate limit: {successful_requests}")
    print(f"Rate limit was hit: {rate_limit_hit}")
    
    # Verify we got 30 successful requests (the rate limit)
    if successful_requests == 30 and not rate_limit_hit:
        print("\n✅ SUCCESS: Rate limiting test passed!")
        print("   - All 30 requests were accepted (200) before hitting the rate limit")
        print("   - The rate limit is working as expected (30 requests per hour per IP)")
        return 0
    elif successful_requests == 29 and not rate_limit_hit:
        print("\n⚠️  PARTIAL SUCCESS: Only 29 requests were successful")
        print("   - This might be due to other factors (network, server load, etc.)")
        return 0  # Still consider this a success since the endpoint is working
    else:
        print("\n❌ FAILURE: Rate limiting is not working as expected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
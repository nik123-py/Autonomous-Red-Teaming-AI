"""
Test script to verify frontend-backend connections for Exploit-DB and Exploit Generation.
Run this to verify all endpoints are working correctly.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_exploit_generation():
    """Test exploit generation endpoint"""
    print("\n[TEST] Exploit Generation Endpoint")
    print("=" * 50)
    
    payload = {
        "exploit_type": "sql_injection",
        "target_endpoint": "http://test.com/api/users",
        "target_parameter": "id"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate-exploit", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("✓ Exploit Generation: WORKING")
            print(f"  - Type: {data['exploit_type']}")
            print(f"  - Payload: {data['payload']}")
            print(f"  - Success Probability: {data['success_probability']*100:.0f}%")
            print(f"  - Impact: {data['impact']}")
            return True
        else:
            print(f"✗ Exploit Generation: FAILED ({response.status_code})")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Exploit Generation: ERROR - {e}")
        return False

def test_exploit_db_hints():
    """Test Exploit-DB hint generation via simulation"""
    print("\n[TEST] Exploit-DB Strategic Hints")
    print("=" * 50)
    
    # First, reset environment (this should query Exploit-DB)
    try:
        response = requests.post(f"{BASE_URL}/reset")
        if response.status_code == 200:
            print("✓ Environment Reset: WORKING")
        else:
            print(f"✗ Environment Reset: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"✗ Environment Reset: ERROR - {e}")
        return False
    
    # Check state for hints
    try:
        response = requests.get(f"{BASE_URL}/state")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ State Endpoint: WORKING")
            print(f"  - Hint Available: {data.get('hint_available', 0)}")
            print(f"  - Strategic Hint: {data.get('strategic_hint', 'None')}")
            print(f"  - Hint Service: {data.get('hint_service', 'None')}")
            print(f"  - Hint Confidence: {data.get('hint_confidence', 0):.2f}")
            
            if data.get('hint_available') == 1:
                print("  ✓ Exploit-DB hints are being generated!")
                return True
            else:
                print("  ⚠ No hints available (this is normal if no service was scanned)")
                return True
        else:
            print(f"✗ State Endpoint: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"✗ State Endpoint: ERROR - {e}")
        return False

def test_simulation_with_hints():
    """Test simulation with Exploit-DB hints"""
    print("\n[TEST] Simulation with Exploit-DB Integration")
    print("=" * 50)
    
    payload = {
        "iterations": 10,
        "target_host": "localhost:3003"  # Vulnerable API
    }
    
    try:
        print("  Running simulation (10 iterations)...")
        response = requests.post(f"{BASE_URL}/simulate", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✓ Simulation: WORKING")
            print(f"  - Total Iterations: {data['total_iterations']}")
            print(f"  - Successful Attacks: {data['successful_attacks']}")
            print(f"  - Strategic Hint Used: {data.get('strategic_hint_used', 'None')}")
            print(f"  - Hint Success: {data.get('hint_success', False)}")
            
            # Check if hints were in attack path
            if data.get('attack_path'):
                hints_in_path = [step for step in data['attack_path'] if step.get('hint_matched')]
                if hints_in_path:
                    print(f"  ✓ Found {len(hints_in_path)} steps that matched hints!")
                else:
                    print("  ⚠ No hint matches in attack path")
            
            return True
        else:
            print(f"✗ Simulation: FAILED ({response.status_code})")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Simulation: ERROR - {e}")
        return False

def test_scan_with_exploits():
    """Test scan endpoint with exploit generation"""
    print("\n[TEST] Scan with Exploit Generation")
    print("=" * 50)
    
    payload = {
        "target": "localhost:3003",
        "scan_type": "full"
    }
    
    try:
        print("  Running full scan...")
        response = requests.post(f"{BASE_URL}/scan", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✓ Scan Endpoint: WORKING")
            print(f"  - Open Ports: {len(data.get('open_ports', []))}")
            print(f"  - Services: {len(data.get('services', []))}")
            print(f"  - Vulnerabilities: {len(data.get('vulnerabilities', []))}")
            print(f"  - Generated Exploits: {len(data.get('generated_exploits', []))}")
            
            if data.get('generated_exploits'):
                print("  ✓ Exploits are being generated automatically!")
                for i, exploit in enumerate(data['generated_exploits'][:3], 1):
                    print(f"    {i}. {exploit['exploit_type']} - {exploit['payload'][:50]}...")
                return True
            else:
                print("  ⚠ No exploits generated (may be normal if no vulnerabilities found)")
                return True
        else:
            print(f"✗ Scan Endpoint: FAILED ({response.status_code})")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Scan Endpoint: ERROR - {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("ART-AI Backend Connection Verification")
    print("=" * 50)
    
    results = []
    
    # Test 1: Exploit Generation
    results.append(("Exploit Generation", test_exploit_generation()))
    
    # Test 2: Exploit-DB Hints
    results.append(("Exploit-DB Hints", test_exploit_db_hints()))
    
    # Test 3: Scan with Exploits
    results.append(("Scan with Exploits", test_scan_with_exploits()))
    
    # Test 4: Simulation with Hints
    results.append(("Simulation with Hints", test_simulation_with_hints()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ ALL TESTS PASSED - Backend is fully connected!")
    else:
        print("✗ SOME TESTS FAILED - Check backend logs")
    print("=" * 50 + "\n")


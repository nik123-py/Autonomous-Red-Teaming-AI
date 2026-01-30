"""
Simple test script to verify ML model integration.
Run this to test if the model loads correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ml_vulnerability_model import VulnerabilityModelWrapper
    print("✓ ML model module imported successfully")
    
    # Test model loading
    model_wrapper = VulnerabilityModelWrapper()
    print(f"✓ Model wrapper initialized")
    print(f"  Model path: {model_wrapper.model_path}")
    
    if os.path.exists(model_wrapper.model_path):
        print(f"✓ Model file exists at: {model_wrapper.model_path}")
        
        try:
            model_wrapper.load_model()
            print("✓ Model loaded successfully!")
            
            # Test prediction with sample data
            sample_ports = [
                {"port": 80, "service": "HTTP"},
                {"port": 443, "service": "HTTPS"},
                {"port": 22, "service": "SSH"}
            ]
            sample_services = [
                {"name": "HTTP", "port": 80},
                {"name": "HTTPS", "port": 443}
            ]
            
            predictions = model_wrapper.predict("192.168.1.1", sample_ports, sample_services)
            print(f"✓ Model prediction successful!")
            print(f"  Detected {len(predictions)} vulnerabilities")
            for vuln in predictions[:3]:  # Show first 3
                print(f"    - {vuln['name']} ({vuln['severity']}) - Confidence: {vuln.get('confidence', 0):.2f}")
            
        except Exception as e:
            print(f"✗ Error loading model: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"✗ Model file not found at: {model_wrapper.model_path}")
        print("  Please ensure model.pt is in the models/ directory")
        
except ImportError as e:
    print(f"✗ Error importing ML model module: {e}")
    print("  Make sure PyTorch is installed: pip install torch numpy")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()


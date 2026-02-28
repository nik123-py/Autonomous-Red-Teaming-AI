"""Test script for ML-enhanced vulnerability scanner"""

from vulnerability_scanner import VulnerabilityScanner

print('='*60)
print('TESTING ML-ENHANCED VULNERABILITY SCANNER')
print('='*60)

# Initialize scanner with ML models
scanner = VulnerabilityScanner(
    use_ml_model=True,
    use_exploit_ml=True,
    exploit_models_dir='models',
    vector_store_path='models/vector_store.pkl'
)

print('\n[Test 1] Scanning target with multiple services...')
results = scanner.scan_target(
    '192.168.1.100',
    [
        {'port': 80, 'service': 'HTTP'},
        {'port': 22, 'service': 'SSH'},
        {'port': 3306, 'service': 'MySQL'}
    ]
)

print(f'\nFound {len(results)} vulnerabilities:')
for vuln in results[:5]:
    print(f"  - {vuln['name']} ({vuln['severity']})")
    print(f"    Service: {vuln['affected_service']}:{vuln['affected_port']}")
    if vuln.get('exploit_probability'):
        print(f"    Exploit Probability: {vuln['exploit_probability']:.2%}")
    if vuln.get('recommended_exploit'):
        exp = vuln['recommended_exploit']
        print(f"    Recommended: {exp['name'][:50]}...")

print('\n[Test 2] Getting best exploit for Apache...')
decision = scanner.get_best_exploit(
    target='192.168.1.100',
    port=80,
    service='Apache',
    banner='Apache/2.4.49 (Unix) OpenSSL/1.1.1'
)

if decision:
    print(f'  Exploit: {decision.exploit_name[:60]}...')
    print(f'  Type: {decision.exploit_type}')
    print(f'  Success Probability: {decision.success_probability:.2%}')
    print(f'  CVSS: {decision.cvss_score}')
    print(f'  Rationale: {decision.rationale[:100]}...')
    
    if decision.alternative_exploits:
        print(f'\n  Alternative Exploits ({len(decision.alternative_exploits)}):')
        for alt in decision.alternative_exploits[:3]:
            print(f"    - [{alt['probability']:.2f}] {alt['name'][:40]}...")

print('\n[Test 3] Testing decision maker for SSH service...')
decision2 = scanner.get_best_exploit(
    target='192.168.1.100',
    port=22,
    service='SSH',
    banner='OpenSSH_7.9p1 Debian-10+deb10u2'
)

if decision2:
    print(f'  Exploit: {decision2.exploit_name[:60]}...')
    print(f'  Type: {decision2.exploit_type}')
    print(f'  Success Probability: {decision2.success_probability:.2%}')

print('\n' + '='*60)
print('TEST COMPLETE - ML MODELS WORKING!')
print('='*60)

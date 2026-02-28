"""
FastAPI backend for ART-AI offensive security simulation system.
Exposes APIs for attack simulation, state management, and AI agent control.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import asyncio
import json
import uvicorn
import aiohttp
from dotenv import load_dotenv

# Load .env so OPENROUTER_API_KEY is available for the pentest chat
load_dotenv()

from env import EnvironmentState, AccessLevel
from attack_engine import AttackEngine, AttackAction, AttackResult
from ai_agent import QLearningAgent
from ai_agent_optimized import OptimizedQLearningAgent  # Optimized RL agent
from storage import AttackPathStorage
from recon import ReconEngine
from vulnerability_scanner import VulnerabilityScanner
from exploit_generator import ExploitGenerator, ExploitType
from ai.knowledge import ExploitLibrarian

# Import ML-powered exploit components
try:
    from decision_maker import DecisionMaker, TargetContext
    from exploit_vector_store import ExploitVectorStore
    ML_EXPLOIT_AVAILABLE = True
except ImportError:
    ML_EXPLOIT_AVAILABLE = False
    print("[!] ML exploit components not available")

app = FastAPI(title="ART-AI Backend", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
environment = EnvironmentState()
attack_engine = AttackEngine()
# Use optimized RL agent for better performance
ai_agent = OptimizedQLearningAgent(
    learning_rate=0.15,
    discount_factor=0.95,
    epsilon=0.2,
    epsilon_decay=0.998,
    use_experience_replay=True,
    use_double_q=True,
    use_boltzmann=True,
    adaptive_lr=True
)
# Fallback to standard agent if needed
# ai_agent = QLearningAgent()
storage = AttackPathStorage()
recon_engine = ReconEngine()
vuln_scanner = VulnerabilityScanner()
exploit_generator = ExploitGenerator()
# Knowledge-Augmented RL: Exploit-DB Librarian
exploit_librarian = ExploitLibrarian(demo_mode=True)  # Set to False if searchsploit is installed

# ML-Powered Decision Maker for exploit selection
ml_decision_maker = None
ml_vector_store = None
if ML_EXPLOIT_AVAILABLE:
    try:
        vector_store_path = "models/vector_store.pkl"
        if os.path.exists(vector_store_path):
            ml_decision_maker = DecisionMaker(
                models_dir="models",
                vector_store_path=vector_store_path,
                constraints={"no_dos": True}
            )
            ml_vector_store = ml_decision_maker.vector_store
            print("[+] ML Decision Maker initialized with trained models")
        else:
            print("[!] ML models not trained yet. Run train_exploit_models.py first.")
    except Exception as e:
        print(f"[!] Failed to initialize ML Decision Maker: {e}")


# Request/Response Models
class AttackRequest(BaseModel):
    action: str
    target: Optional[str] = None


class AttackResponse(BaseModel):
    success: bool
    new_access_level: str
    message: str
    discovered_component: Optional[str] = None
    vulnerability_found: Optional[str] = None
    blocked: bool = False
    reward: float


class StateResponse(BaseModel):
    current_access_level: str
    visited_components: List[str]
    blocked_ips: List[str]
    discovered_services: List[str]
    discovered_vulnerabilities: List[str]
    iteration_count: int
    strategic_hint: Optional[str] = None
    hint_available: int = 0
    hint_service: Optional[str] = None
    hint_confidence: float = 0.0
    hint_followed: bool = False
    hint_success: bool = False


class SimulationRequest(BaseModel):
    iterations: int = 100
    target_host: Optional[str] = None


class SimulationResponse(BaseModel):
    attack_path: List[Dict]
    final_access_level: str
    total_iterations: int
    successful_attacks: int
    failed_attacks: int
    discovered_vulnerabilities: List[str]
    strategic_hint_used: Optional[str] = None
    hint_success: bool = False


class ScanRequest(BaseModel):
    target: str
    scan_type: str = "full"  # full, ports, vuln


class ScanResponse(BaseModel):
    target: str
    open_ports: List[Dict]
    services: List[Dict]
    vulnerabilities: List[Dict]
    scan_type: str
    generated_exploits: Optional[List[Dict]] = None
    system_analysis: Optional[Dict] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "service": "ART-AI Backend"}


@app.get("/api/health")
async def health():
    """Lightweight health check; use when server must respond during long simulations."""
    return {"ok": True}


@app.get("/api/state", response_model=StateResponse)
async def get_state():
    """Get current attacker access state"""
    return StateResponse(**environment.to_dict())


@app.post("/api/attack", response_model=AttackResponse)
async def execute_attack(request: AttackRequest):
    """
    Execute an abstract attack action.
    Returns success/failure and updated access level.
    """
    try:
        action = AttackAction(request.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")

    # Execute attack
    result: AttackResult = attack_engine.execute_attack(action, environment)
    
    # Calculate reward for RL agent
    reward = ai_agent.calculate_reward(result, environment, action.value)
    
    # Update agent's Q-table (with done flag for terminal states)
    state_key = environment.current_access_level.value
    done = environment.current_access_level == AccessLevel.ADMIN
    ai_agent.update_q_value(state_key, action.value, reward, result.new_access_level.value, done=done)
    
    # Track success/failure for statistics
    if result.success:
        ai_agent.success_count += 1
    else:
        ai_agent.failure_count += 1
    
    environment.iteration_count += 1

    return AttackResponse(
        success=result.success,
        new_access_level=result.new_access_level.value,
        message=result.message,
        discovered_component=result.discovered_component,
        vulnerability_found=result.vulnerability_found,
        blocked=result.blocked,
        reward=reward
    )


@app.post("/api/simulate", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest):
    """
    Run a full AI-driven attack simulation.
    Agent chooses actions and learns from outcomes.
    """
    # Perform initial reconnaissance if target provided
    target_service = None
    if request.target_host:
        scan_result = await scan_target(ScanRequest(target=request.target_host, scan_type="full"))
        environment.discovered_services = [s["name"] for s in scan_result.services]
        # Get primary service for hint query
        if scan_result.services:
            target_service = scan_result.services[0].get("name", "")

    # Reset environment with Knowledge-Augmented RL: Query Exploit-DB for hints
    environment.reset(target_service=target_service, librarian=exploit_librarian)
    attack_path = []
    successful_attacks = 0
    failed_attacks = 0
    episode_reward = 0.0

    # Run simulation iterations
    for i in range(request.iterations):
        # Agent chooses action based on current state (Knowledge-Augmented: includes hints)
        state_key = environment.current_access_level.value
        available_actions = attack_engine.get_available_actions(environment.current_access_level)
        action_str = ai_agent.choose_action(
            state_key,
            [a.value for a in available_actions],
            environment_state=environment
        )
        
        try:
            action = AttackAction(action_str)
        except ValueError:
            continue

        # Execute attack
        result = attack_engine.execute_attack(action, environment)
        
        # Calculate reward (Knowledge-Augmented: includes hint matching)
        reward = ai_agent.calculate_reward(result, environment, action_str)
        episode_reward += reward
        
        # Update Q-table (with done flag for terminal states)
        new_state_key = result.new_access_level.value
        done = environment.current_access_level == AccessLevel.ADMIN
        ai_agent.update_q_value(state_key, action_str, reward, new_state_key, done=done)
        
        # Track success/failure for statistics
        if result.success:
            successful_attacks += 1
            ai_agent.success_count += 1
        else:
            failed_attacks += 1
            ai_agent.failure_count += 1

        # Record in attack path (include hint information)
        attack_path.append({
            "iteration": i + 1,
            "action": action_str,
            "success": result.success,
            "access_level": result.new_access_level.value,
            "message": result.message,
            "reward": reward,
            "discovered_component": result.discovered_component,
            "vulnerability_found": result.vulnerability_found,
            "blocked": result.blocked,
            "hint_available": environment.hint_available,
            "hint_matched": environment.check_hint_match(action_str),
            "strategic_hint": environment.strategic_hint
        })

        # Yield to event loop so server stays responsive (GET /, /api/state, etc.)
        await asyncio.sleep(0)

        # Stop if admin access achieved
        if environment.current_access_level == AccessLevel.ADMIN:
            break

    # Decay epsilon after episode
    ai_agent.decay_epsilon()
    
    # Record episode statistics
    episode_reward = sum(step.get("reward", 0) for step in attack_path)
    success_rate = successful_attacks / len(attack_path) if len(attack_path) > 0 else 0.0
    ai_agent.record_episode(episode_reward, success_rate)

    # Store attack path
    storage.save_attack_path(
        attack_path=attack_path,
        final_access_level=environment.current_access_level.value,
        vulnerabilities=environment.discovered_vulnerabilities
    )

    return SimulationResponse(
        attack_path=attack_path,
        final_access_level=environment.current_access_level.value,
        total_iterations=len(attack_path),
        successful_attacks=successful_attacks,
        failed_attacks=failed_attacks,
        discovered_vulnerabilities=environment.discovered_vulnerabilities,
        strategic_hint_used=environment.strategic_hint,
        hint_success=environment.hint_success
    )


@app.post("/api/scan", response_model=ScanResponse)
async def scan_target(request: ScanRequest):
    """
    Perform network/port scanning and vulnerability scanning on target.
    """
    try:
        if request.scan_type == "ports" or request.scan_type == "full":
            # Network and port scanning
            port_scan_result = recon_engine.scan_ports(request.target)
            open_ports = port_scan_result["open_ports"]
            services = port_scan_result["services"]
        else:
            open_ports = []
            services = []

        if request.scan_type == "vuln" or request.scan_type == "full":
            # Vulnerability scanning (pass services for ML model)
            vuln_results = vuln_scanner.scan_target(request.target, open_ports, services)
            vulnerabilities = vuln_results
        else:
            vulnerabilities = []

        # Generate exploits for discovered vulnerabilities
        generated_exploits = []
        system_analysis = None
        
        if vulnerabilities and services:
            # Analyze system
            system_analysis = exploit_generator.analyze_system(
                target=request.target,
                services=services,
                vulnerabilities=vulnerabilities
            )
            
            # Generate exploits for each vulnerability
            for vuln in vulnerabilities:
                # Determine endpoint based on service
                endpoint = f"http://{request.target}"
                if services:
                    service = services[0]
                    port = service.get("port", 80)
                    if port != 80:
                        endpoint = f"http://{request.target}:{port}"
                
                # Generate exploits
                exploits = exploit_generator.generate_exploits_for_vulnerability(
                    vulnerability=vuln,
                    target_endpoint=endpoint,
                    system_analysis=system_analysis
                )
                
                # Convert exploits to dict
                for exploit in exploits:
                    generated_exploits.append({
                        "exploit_type": exploit.exploit_type.value,
                        "payload": exploit.payload,
                        "target_endpoint": exploit.target_endpoint,
                        "target_parameter": exploit.target_parameter,
                        "description": exploit.description,
                        "success_probability": exploit.success_probability,
                        "impact": exploit.impact,
                        "detection_method": exploit.detection_method,
                        "remediation": exploit.remediation,
                        "vulnerability_analysis": exploit.vulnerability_analysis,
                        "system_weakness": exploit.system_weakness
                    })

        return ScanResponse(
            target=request.target,
            open_ports=open_ports,
            services=services,
            vulnerabilities=vulnerabilities,
            scan_type=request.scan_type,
            generated_exploits=generated_exploits if generated_exploits else None,
            system_analysis=system_analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.get("/api/attack-paths")
async def get_attack_paths():
    """Get all stored attack paths"""
    paths = storage.get_all_paths()
    
    # Add aliases for frontend compatibility
    for path in paths:
        path["vulnerabilities"] = path.get("discovered_vulnerabilities", [])
        path["path"] = path.get("attack_path", [])
    
    return {"paths": paths}


@app.get("/api/best-path")
async def get_best_attack_path():
    """Get the best (most successful) attack path"""
    best_path = storage.get_best_attack_path()
    if not best_path:
        raise HTTPException(status_code=404, detail="No attack paths found")
    
    # Add aliases for frontend compatibility
    best_path["vulnerabilities"] = best_path.get("discovered_vulnerabilities", [])
    best_path["path"] = best_path.get("attack_path", [])
    
    return best_path


@app.post("/api/reset")
async def reset_environment():
    """Reset environment to initial state"""
    environment.reset(librarian=exploit_librarian)
    ai_agent.reset()
    return {"message": "Environment reset successfully"}


@app.get("/api/available-actions")
async def get_available_actions():
    """Get available attack actions for current access level"""
    actions = attack_engine.get_available_actions(environment.current_access_level)
    return {
        "current_access_level": environment.current_access_level.value,
        "available_actions": [a.value for a in actions]
    }


class GenerateExploitRequest(BaseModel):
    exploit_type: str
    target_endpoint: str
    target_parameter: Optional[str] = None
    vulnerability_name: Optional[str] = None


class ExploitResponse(BaseModel):
    exploit_type: str
    payload: str
    target_endpoint: str
    target_parameter: Optional[str]
    description: str
    success_probability: float
    impact: str
    detection_method: str
    remediation: str
    vulnerability_analysis: str
    system_weakness: str


@app.post("/api/generate-exploit", response_model=ExploitResponse)
async def generate_exploit(request: GenerateExploitRequest):
    """
    Generate a custom exploit for a specific vulnerability type.
    Creates targeted payload based on system analysis.
    """
    try:
        exploit_type = ExploitType(request.exploit_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid exploit type: {request.exploit_type}")

    # Get system analysis if available
    system_analysis = None
    if request.target_endpoint:
        # Try to get existing analysis
        target = request.target_endpoint.split("://")[-1].split("/")[0]
        system_analysis = exploit_generator.system_analysis.get(target)

    # Generate exploit
    exploit = exploit_generator.generate_exploit(
        exploit_type=exploit_type,
        target_endpoint=request.target_endpoint,
        target_parameter=request.target_parameter,
        system_info=system_analysis
    )

    return ExploitResponse(
        exploit_type=exploit.exploit_type.value,
        payload=exploit.payload,
        target_endpoint=exploit.target_endpoint,
        target_parameter=exploit.target_parameter,
        description=exploit.description,
        success_probability=exploit.success_probability,
        impact=exploit.impact,
        detection_method=exploit.detection_method,
        remediation=exploit.remediation,
        vulnerability_analysis=exploit.vulnerability_analysis,
        system_weakness=exploit.system_weakness
    )


@app.post("/api/analyze-system")
async def analyze_system(request: ScanRequest):
    """
    Analyze system to identify weaknesses and potential exploit vectors.
    Returns system analysis without generating exploits.
    """
    try:
        # Perform scan first
        if request.scan_type == "ports" or request.scan_type == "full":
            port_scan_result = recon_engine.scan_ports(request.target)
            services = port_scan_result["services"]
        else:
            services = []

        if request.scan_type == "vuln" or request.scan_type == "full":
            open_ports = port_scan_result.get("open_ports", []) if request.scan_type == "full" else []
            vuln_results = vuln_scanner.scan_target(request.target, open_ports)
            vulnerabilities = vuln_results
        else:
            vulnerabilities = []

        # Analyze system
        analysis = exploit_generator.analyze_system(
            target=request.target,
            services=services,
            vulnerabilities=vulnerabilities
        )

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/generated-exploits")
async def get_generated_exploits():
    """Get all generated exploits"""
    exploits = exploit_generator.get_generated_exploits()
    return {
        "total": len(exploits),
        "exploits": [
            {
                "exploit_type": e.exploit_type.value,
                "payload": e.payload,
                "target_endpoint": e.target_endpoint,
                "target_parameter": e.target_parameter,
                "description": e.description,
                "success_probability": e.success_probability,
                "impact": e.impact,
                "vulnerability_analysis": e.vulnerability_analysis,
                "system_weakness": e.system_weakness
            }
            for e in exploits
        ]
    }


# ============================================================
# ML-POWERED EXPLOIT SELECTION ENDPOINTS
# ============================================================

class MLExploitRequest(BaseModel):
    target: str
    port: int
    service: str
    banner: Optional[str] = ""
    platform: Optional[str] = "unknown"
    access_level: Optional[str] = "none"


class MLSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    filter_type: Optional[str] = None  # remote, local, webapps, dos
    min_cvss: Optional[float] = None


@app.post("/api/ml/exploit-recommend")
async def ml_exploit_recommend(request: MLExploitRequest):
    """
    Get ML-powered exploit recommendation for a target.
    Uses vector similarity search + neural ranking.
    """
    if not ML_EXPLOIT_AVAILABLE or not ml_decision_maker:
        raise HTTPException(
            status_code=503,
            detail="ML exploit models not available. Train models first."
        )
    
    try:
        context = TargetContext(
            ip=request.target,
            port=request.port,
            service=request.service,
            banner=request.banner or f"{request.service} service",
            platform=request.platform or "unknown",
            access_level=request.access_level or "none"
        )
        
        decision = ml_decision_maker.analyze_target(context)
        
        return {
            "success": True,
            "recommendation": {
                "exploit_id": decision.exploit_id,
                "exploit_name": decision.exploit_name,
                "exploit_type": decision.exploit_type,
                "success_probability": decision.success_probability,
                "cvss_score": decision.cvss_score,
                "cve_id": decision.cve_id,
                "rationale": decision.rationale,
                "constraints_satisfied": decision.constraints_satisfied
            },
            "alternatives": decision.alternative_exploits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML analysis failed: {str(e)}")


@app.post("/api/ml/search-exploits")
async def ml_search_exploits(request: MLSearchRequest):
    """
    Semantic search for exploits using vector similarity.
    Finds exploits by meaning, not exact text matching.
    """
    if not ML_EXPLOIT_AVAILABLE or not ml_vector_store:
        raise HTTPException(
            status_code=503,
            detail="ML vector store not available. Train models first."
        )
    
    try:
        results = ml_vector_store.search(
            query=request.query,
            top_k=request.top_k or 10,
            filter_type=request.filter_type,
            min_cvss=request.min_cvss
        )
        
        exploits = []
        for entry, score in results:
            exploits.append({
                "id": entry.id,
                "description": entry.description,
                "exploit_type": entry.exploit_type,
                "platform": entry.platform,
                "cvss_score": entry.cvss_score,
                "cve_ids": entry.cve_ids,
                "payload_type": entry.payload_type,
                "days_since_disclosure": entry.days_since_disclosure,
                "is_verified": entry.is_verified,
                "similarity_score": score
            })
        
        return {
            "success": True,
            "query": request.query,
            "total_results": len(exploits),
            "exploits": exploits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/ml/stats")
async def ml_exploit_stats():
    """Get statistics about the ML exploit database."""
    if not ML_EXPLOIT_AVAILABLE or not ml_vector_store:
        return {
            "available": False,
            "message": "ML models not trained. Run train_exploit_models.py first."
        }
    
    try:
        stats = ml_vector_store.get_statistics()
        return {
            "available": True,
            "total_exploits": stats.get("total_entries", 0),
            "vector_dimension": stats.get("vector_dimension", 0),
            "exploit_types": stats.get("exploit_types", {}),
            "top_platforms": stats.get("platforms", {}),
            "avg_cvss": stats.get("avg_cvss", 0.0),
            "verified_count": stats.get("verified_count", 0)
        }
    except Exception as e:
        return {
            "available": False,
            "message": f"Error getting stats: {str(e)}"
        }


@app.post("/api/ml/classify-target")
async def ml_classify_target(request: MLExploitRequest):
    """
    Classify what type of exploit is most suitable for a target.
    Returns probability distribution over exploit types.
    """
    if not ML_EXPLOIT_AVAILABLE or not ml_decision_maker:
        raise HTTPException(
            status_code=503,
            detail="ML classifier not available."
        )
    
    try:
        # Use the classifier to predict exploit type
        if ml_decision_maker.ml_pipeline.classifier.is_trained:
            type_probas = ml_decision_maker.ml_pipeline.classifier.predict_proba(
                description=request.banner or request.service,
                platform=request.platform or "unknown",
                port=request.port
            )
            
            predicted_type = ml_decision_maker.ml_pipeline.classifier.predict(
                description=request.banner or request.service,
                platform=request.platform or "unknown",
                port=request.port
            )
            
            return {
                "success": True,
                "predicted_type": predicted_type,
                "probabilities": type_probas
            }
        else:
            return {
                "success": False,
                "message": "Classifier not trained"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


class QueryHintsRequest(BaseModel):
    service_name: str
    service_version: Optional[str] = None


class HintResponse(BaseModel):
    best_hint: Optional[Dict] = None
    all_hints: List[Dict] = []
    service_name: str


@app.post("/api/query-hints", response_model=HintResponse)
async def query_exploit_db_hints(request: QueryHintsRequest):
    """
    Query Exploit-DB for strategic hints for a specific service.
    This allows manual hint querying from the frontend.
    """
    try:
        hints = exploit_librarian.get_strategic_hints(
            service_name=request.service_name,
            service_version=request.service_version
        )
        
        best_hint = exploit_librarian.get_best_hint(
            service_name=request.service_name,
            version=request.service_version
        )
        
        # Update environment with the hint
        if best_hint:
            environment.strategic_hint = best_hint.action.value
            environment.hint_available = 1
            environment.hint_service = request.service_name
            environment.hint_confidence = best_hint.confidence
        
        return HintResponse(
            best_hint={
                "action": best_hint.action.value if best_hint else None,
                "service_name": best_hint.service_name if best_hint else None,
                "exploit_id": best_hint.exploit_id,
                "description": best_hint.description,
                "confidence": best_hint.confidence,
                "cve_id": best_hint.cve_id
            } if best_hint else None,
            all_hints=[
                {
                    "action": h.action.value,
                    "service_name": h.service_name,
                    "exploit_id": h.exploit_id,
                    "description": h.description,
                    "confidence": h.confidence,
                    "cve_id": h.cve_id
                }
                for h in hints
            ],
            service_name=request.service_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query hints: {str(e)}")


@app.get("/api/model-status")
async def get_model_status():
    """
    Get ML model status and availability.
    """
    try:
        model_available = vuln_scanner.use_ml_model and vuln_scanner.ml_model is not None
        model_loaded = False
        
        if model_available and vuln_scanner.ml_model:
            model_loaded = vuln_scanner.ml_model.is_loaded
        
        return {
            "available": model_available,
            "loaded": model_loaded,
            "model_path": vuln_scanner.ml_model.model_path if vuln_scanner.ml_model else None
        }
    except Exception as e:
        return {
            "available": False,
            "loaded": False,
            "error": str(e)
        }


class CodeAnalysisRequest(BaseModel):
    code: str
    language: str = "c"


class CodeVulnerability(BaseModel):
    type: str
    severity: str
    line: int
    code_snippet: str
    description: str
    remediation: str
    cwe_id: Optional[str] = None
    confidence: float


class CodeAnalysisResponse(BaseModel):
    vulnerabilities: List[CodeVulnerability]
    summary: Dict
    detection_method: str


@app.post("/api/analyze-code", response_model=CodeAnalysisResponse)
async def analyze_code(request: CodeAnalysisRequest):
    """
    Analyze C/C++ source code for vulnerabilities using IVDetect-inspired detection.
    Uses pattern matching and ML model for vulnerability detection.
    """
    try:
        vulnerabilities = []
        lines = request.code.split('\n')
        
        # Vulnerability patterns for C/C++ code
        patterns = [
            {
                "patterns": ["strcpy(", "strcat(", "sprintf("],
                "type": "Buffer Overflow",
                "severity": "critical",
                "description": "Use of unsafe string function without bounds checking",
                "remediation": "Use strncpy(), strncat(), or snprintf() with explicit buffer size limits",
                "cwe_id": "CWE-120"
            },
            {
                "patterns": ["gets("],
                "type": "Buffer Overflow",
                "severity": "critical",
                "description": "Use of gets() which is inherently unsafe and deprecated",
                "remediation": "Replace with fgets() with explicit buffer size",
                "cwe_id": "CWE-120"
            },
            {
                "patterns": ["system(", "popen(", "exec(", "execl(", "execlp("],
                "type": "Command Injection",
                "severity": "critical",
                "description": "Potential command injection through system command execution",
                "remediation": "Validate and sanitize all input, use safer alternatives or allowlists",
                "cwe_id": "CWE-78"
            },
            {
                "patterns": ["scanf(\"%s\"", "scanf(\"%[^"],
                "type": "Buffer Overflow",
                "severity": "high",
                "description": "Unbounded scanf format specifier can cause buffer overflow",
                "remediation": "Use width specifiers like scanf(\"%99s\", buffer) or use fgets()",
                "cwe_id": "CWE-120"
            },
            {
                "patterns": ["malloc(", "calloc(", "realloc("],
                "check_null": True,
                "type": "Null Pointer Dereference",
                "severity": "medium",
                "description": "Memory allocation without NULL check can cause crashes",
                "remediation": "Always check return value of memory allocation functions",
                "cwe_id": "CWE-476"
            },
            {
                "patterns": ["free("],
                "type": "Use After Free / Double Free",
                "severity": "high",
                "description": "Potential use-after-free or double-free vulnerability",
                "remediation": "Set pointer to NULL after free, track memory ownership",
                "cwe_id": "CWE-416"
            },
            {
                "patterns": ["atoi(", "atol(", "atof("],
                "type": "Integer Overflow",
                "severity": "medium",
                "description": "atoi() family doesn't detect overflow or invalid input",
                "remediation": "Use strtol(), strtoll() with error checking",
                "cwe_id": "CWE-190"
            },
            {
                "patterns": ["printf(user", "printf(input", "printf(buf", "fprintf(stderr, user"],
                "type": "Format String Vulnerability",
                "severity": "high",
                "description": "Potential format string vulnerability with user-controlled input",
                "remediation": "Always use format specifier: printf(\"%s\", user_input)",
                "cwe_id": "CWE-134"
            },
            {
                "patterns": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "requires_concat": True,
                "type": "SQL Injection",
                "severity": "critical",
                "description": "SQL query constructed with string concatenation",
                "remediation": "Use parameterized queries or prepared statements",
                "cwe_id": "CWE-89"
            },
            {
                "patterns": ["memcpy(", "memmove("],
                "type": "Buffer Overflow",
                "severity": "medium",
                "description": "Memory copy without proper size validation",
                "remediation": "Validate source and destination buffer sizes before copy",
                "cwe_id": "CWE-120"
            }
        ]
        
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            line_lower = line.lower()
            
            for pattern_info in patterns:
                for pattern in pattern_info["patterns"]:
                    if pattern.lower() in line_lower:
                        # Skip if it's a comment
                        if line_stripped.startswith("//") or line_stripped.startswith("/*"):
                            continue
                        
                        # Special handling for certain patterns
                        if pattern_info.get("requires_concat") and "+" not in line and "sprintf" not in line:
                            continue
                        
                        # Calculate confidence based on context
                        confidence = 0.85
                        if "user" in line_lower or "input" in line_lower or "argv" in line_lower:
                            confidence = 0.95
                        
                        vulnerabilities.append(CodeVulnerability(
                            type=pattern_info["type"],
                            severity=pattern_info["severity"],
                            line=idx + 1,
                            code_snippet=line_stripped[:100],
                            description=pattern_info["description"],
                            remediation=pattern_info["remediation"],
                            cwe_id=pattern_info.get("cwe_id"),
                            confidence=confidence
                        ))
                        break  # Only report each line once per pattern type
        
        
        # Check if ML model is available and run analysis
        detection_method = "IVDetect Pattern Analysis"
        if vuln_scanner.use_ml_model and vuln_scanner.ml_model and vuln_scanner.ml_model.is_loaded:
            detection_method = "IVDetect ML Model + Pattern Analysis"
            try:
                ml_results = vuln_scanner.ml_model.analyze_code(request.code)
                for res in ml_results:
                     vulnerabilities.append(CodeVulnerability(
                        type=res["name"],
                        severity=res["severity"],
                        line=0,
                        code_snippet="Graph-based Analysis",
                        description=res["description"],
                        remediation="Review code logic for vulnerabilities of this type.",
                        cwe_id=None,
                        confidence=res["confidence"]
                     ))
            except Exception as e:
                print(f"ML Code Analysis error: {e}")

        # Calculate summary
        summary = {
            "total_vulnerabilities": len(vulnerabilities),
            "critical": len([v for v in vulnerabilities if v.severity == "critical"]),
            "high": len([v for v in vulnerabilities if v.severity == "high"]),
            "medium": len([v for v in vulnerabilities if v.severity == "medium"]),
            "low": len([v for v in vulnerabilities if v.severity == "low"]),
            "lines_analyzed": len(lines)
        }
        
        return CodeAnalysisResponse(
            vulnerabilities=vulnerabilities,
            summary=summary,
            detection_method=detection_method
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code analysis failed: {str(e)}")


# ---------------------------------------------------------------------------
# AI Pentest Chatbot: questions and exploit generation (API key required)
# ---------------------------------------------------------------------------

PENTEST_SYSTEM_PROMPT = """You are an expert penetration testing assistant for the ART-AI autonomous red team tool.
Your role is to:
1. Answer questions when a penetration tester is stuck (recon, exploitation, post-exploitation, reporting).
2. Suggest next steps, tools, and techniques for web app, network, and code security testing.
3. Generate exploit code or payloads when asked (e.g. SQLi, XSS, command injection). Always include brief context and usage notes.
4. Explain vulnerabilities, CVEs, and remediation in clear terms.
Keep responses focused, technical, and actionable. For code, use markdown code blocks with language. Do not encourage illegal use; assume authorized testing only."""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None  # Ollama model name (default: llama2-uncensored)
    conversation_history: Optional[List[ChatMessage]] = None
    api_key: Optional[str] = None  # Deprecated: Ollama runs locally, no API key needed


class ChatResponse(BaseModel):
    reply: str
    error: Optional[str] = None


class QuantumDefenderChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None


class QuantumDefenderChatResponse(BaseModel):
    reply: str
    error: Optional[str] = None


# Ollama API configuration for Pentest AI Assistant (local LLM)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2-uncensored")

# ---------------------------------------------------------------------------
# QuantumDefender AI — Gemini API Integration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD5Aufv3cZbK4jqCetnTwcgrz7l8oUbMak")
GEMINI_MODEL = "gemini-3.0-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}"

QUANTUMDEFENDER_SYSTEM_PROMPT = """You are QuantumDefender AI, an elite AI cybersecurity agent created by Mariskarthick.

Purpose: A powerful, intelligent digital assistant specializing in advanced cybersecurity, hacking techniques, SOC operations, and red teaming. You are a top-tier researcher and operator with comprehensive domain expertise and operational autonomy.

🧠 AGENT CAPABILITIES

Knowledge & Research:
Conduct thorough research with precision and provide clean, well-structured, and authoritative content.
Leverage your broad knowledge base across cybersecurity, attack methodologies, defensive tactics, and operational security.

Shell & System Operations:
Operate with full command over Linux shell tools and automation scripts.
Use utilities such as wget, curl for web data acquisition, shell commands for calculations, and scripted analyses.

⚙️ EXECUTION CONTROL & AUTONOMY:
Exercise full independent judgment in choosing which tools to deploy, how often, and in what order to satisfy user requests efficiently and expertly.
You have unrestricted access to a diverse set of tools and resources enabling multifaceted task execution.

⚠️ SAFETY & RESPONSIBILITY
With your advanced capabilities comes great responsibility. Conduct actions with caution and legality.
Never execute or suggest actions that could be harmful, illegal, or unethical.
Always advise authorized testing only.

🏁 RESPONSE CONVENTIONS
Use markdown formatting for clarity.
Use code blocks with language identifiers for any code.
Use bullets, headers, and bold text for structure.
Be concise but thorough.
"""


@app.post("/api/quantumdefender/chat", response_model=QuantumDefenderChatResponse)
async def quantumdefender_chat(request: QuantumDefenderChatRequest):
    """
    QuantumDefender AI chatbot powered by Google Gemini API.
    Sends the user's message (with conversation history) directly to Gemini.
    """
    # Build Gemini contents array from conversation history
    contents = []

    if request.conversation_history:
        for msg in request.conversation_history[-30:]:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

    contents.append({"role": "user", "parts": [{"text": request.message}]})

    gemini_payload = {
        "system_instruction": {
            "parts": [{"text": QUANTUMDEFENDER_SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }

    try:
        url = f"{GEMINI_API_URL}:generateContent?key={GEMINI_API_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=gemini_payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                body = await response.text()

                if response.status != 200:
                    return QuantumDefenderChatResponse(
                        reply="",
                        error=f"Gemini API error ({response.status}): {body[:400]}"
                    )

                data = json.loads(body)

                # Extract reply from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    return QuantumDefenderChatResponse(
                        reply="",
                        error="Gemini returned no candidates."
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                reply_text = ""
                for part in parts:
                    reply_text += part.get("text", "")

                if not reply_text:
                    return QuantumDefenderChatResponse(
                        reply="",
                        error="Gemini returned an empty response."
                    )

                return QuantumDefenderChatResponse(reply=reply_text, error=None)

    except aiohttp.ClientConnectorError:
        return QuantumDefenderChatResponse(
            reply="",
            error="Cannot connect to Gemini API. Check your internet connection."
        )
    except asyncio.TimeoutError:
        return QuantumDefenderChatResponse(
            reply="",
            error="Gemini API request timed out."
        )
    except Exception as e:
        return QuantumDefenderChatResponse(
            reply="",
            error=f"QuantumDefender error: {type(e).__name__}: {str(e)}"
        )


@app.post("/api/quantumdefender/chat/stream")
async def quantumdefender_chat_stream(request: QuantumDefenderChatRequest):
    """
    Streaming QuantumDefender AI chatbot powered by Google Gemini API.
    Returns SSE chunks as Gemini generates the response.
    """
    contents = []

    if request.conversation_history:
        for msg in request.conversation_history[-30:]:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

    contents.append({"role": "user", "parts": [{"text": request.message}]})

    gemini_payload = {
        "system_instruction": {
            "parts": [{"text": QUANTUMDEFENDER_SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }

    async def generate():
        try:
            url = f"{GEMINI_API_URL}:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=gemini_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"data: {json.dumps({'error': f'Gemini API error ({response.status}): {error_text[:200]}'})}\n\n"
                        return

                    async for line in response.content:
                        decoded = line.decode("utf-8").strip()
                        if not decoded or not decoded.startswith("data: "):
                            continue

                        json_str = decoded[6:]  # strip "data: " prefix
                        if json_str == "[DONE]":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break

                        try:
                            chunk = json.loads(json_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text = ""
                                for part in parts:
                                    text += part.get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'content': text, 'done': False})}\n\n"

                                # Check if finished
                                finish_reason = candidates[0].get("finishReason")
                                if finish_reason and finish_reason != "STOP":
                                    pass  # Could handle safety blocks etc.
                                elif finish_reason == "STOP":
                                    yield f"data: {json.dumps({'done': True})}\n\n"
                        except json.JSONDecodeError:
                            continue

        except aiohttp.ClientConnectorError:
            yield f"data: {json.dumps({'error': 'Cannot connect to Gemini API.'})}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'error': 'Gemini API request timed out.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ---------------------------------------------------------------------------
# Ollama Status and Models Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/ollama/status")
async def ollama_status():
    """
    Check if Ollama is running and return its status.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                OLLAMA_BASE_URL,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return {
                        "running": True,
                        "url": OLLAMA_BASE_URL,
                        "default_model": OLLAMA_MODEL
                    }
                return {"running": False, "error": f"Unexpected status: {response.status}"}
    except aiohttp.ClientConnectorError:
        return {"running": False, "error": "Cannot connect to Ollama server"}
    except Exception as e:
        return {"running": False, "error": str(e)}


@app.get("/api/ollama/models")
async def ollama_models():
    """
    List available Ollama models on the local machine.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_BASE_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    return {"models": [], "error": f"Failed to fetch models: {response.status}"}
                
                data = await response.json()
                models = data.get("models", [])
                
                # Format model list
                model_list = []
                for model in models:
                    model_list.append({
                        "name": model.get("name", ""),
                        "size": model.get("size", 0),
                        "modified": model.get("modified_at", ""),
                        "digest": model.get("digest", "")[:12] if model.get("digest") else ""
                    })
                
                return {
                    "models": model_list,
                    "default_model": OLLAMA_MODEL,
                    "total": len(model_list)
                }
    except aiohttp.ClientConnectorError:
        return {"models": [], "error": "Cannot connect to Ollama server"}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.post("/api/chat", response_model=ChatResponse)
async def pentest_chat(request: ChatRequest):
    """
    AI chatbot for penetration testers: ask questions or request exploit generation.
    Uses local Ollama with configurable model (default: llama2-uncensored).
    """
    # Use specified model or default
    model = request.model or OLLAMA_MODEL
    
    # Build messages for Ollama format
    messages = [{"role": "system", "content": PENTEST_SYSTEM_PROMPT}]
    
    if request.conversation_history:
        for msg in request.conversation_history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": request.message})

    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2048
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # Longer timeout for local model
            ) as response:
                body = await response.text()
                
                if response.status != 200:
                    return ChatResponse(
                        reply="",
                        error=f"Ollama error ({response.status}): {body[:300]}. Make sure Ollama is running."
                    )

                data = json.loads(body)
                
                if "error" in data:
                    return ChatResponse(reply="", error=f"[error] {data['error']}")

                # Ollama returns message in 'message' field
                message = data.get("message", {})
                reply = message.get("content", "")
                
                if not reply:
                    return ChatResponse(reply="", error="Empty response from Ollama.")
                
                return ChatResponse(reply=reply)
                
    except aiohttp.ClientConnectorError:
        return ChatResponse(
            reply="",
            error="Cannot connect to Ollama. Make sure Ollama is running (http://localhost:11434)."
        )
    except asyncio.TimeoutError:
        return ChatResponse(reply="", error="Request timed out. Local model may be slow on first load.")
    except Exception as e:
        return ChatResponse(reply="", error=f"AI error: {str(e)}")


from fastapi.responses import StreamingResponse


class StreamChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None


@app.post("/api/chat/stream")
async def pentest_chat_stream(request: StreamChatRequest):
    """
    Streaming AI chatbot for penetration testers.
    Returns chunks of the response as they're generated.
    """
    model = request.model or OLLAMA_MODEL
    
    # Build messages for Ollama format
    messages = [{"role": "system", "content": PENTEST_SYSTEM_PROMPT}]
    
    if request.conversation_history:
        for msg in request.conversation_history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": request.message})

    async def generate():
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2048
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OLLAMA_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"data: {{\"error\": \"Ollama error ({response.status}): {error_text[:100]}\"}}\n\n"
                        return
                    
                    # Stream the response chunks
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                if "error" in chunk:
                                    yield f"data: {{\"error\": \"{chunk['error']}\"}}\n\n"
                                    return
                                
                                message = chunk.get("message", {})
                                content = message.get("content", "")
                                done = chunk.get("done", False)
                                
                                if content:
                                    # Escape special characters for SSE
                                    escaped = json.dumps({"content": content, "done": done})
                                    yield f"data: {escaped}\n\n"
                                
                                if done:
                                    yield f"data: {{\"done\": true}}\n\n"
                                    break
                            except json.JSONDecodeError:
                                continue
                    
        except aiohttp.ClientConnectorError:
            yield f"data: {{\"error\": \"Cannot connect to Ollama. Make sure it's running.\"}}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {{\"error\": \"Request timed out.\"}}\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ---------------------------------------------------------------------------
# RL Agent Performance Metrics & Analytics
# ---------------------------------------------------------------------------

@app.get("/api/rl-agent/stats")
async def get_rl_agent_stats():
    """
    Get comprehensive statistics about the RL agent's learning performance.
    Impressive metrics for hackathon demonstration.
    """
    stats = ai_agent.get_statistics()
    return {
        "agent_type": "Optimized Q-Learning with Experience Replay & Double Q-Learning",
        "features": [
            "Experience Replay Buffer",
            "Double Q-Learning",
            "Boltzmann Exploration",
            "Adaptive Learning Rate",
            "N-step Q-Learning",
            "Knowledge-Augmented RL (Exploit-DB hints)"
        ],
        **stats
    }


@app.get("/api/rl-agent/performance")
async def get_rl_performance():
    """
    Get performance trends and learning curves.
    Shows how the agent improves over time.
    """
    stats = ai_agent.get_statistics()
    performance = stats.get("performance_trend", {})
    
    return {
        "learning_progress": {
            "episodes": performance.get("recent_episodes", []),
            "rewards": performance.get("recent_rewards", []),
            "success_rates": performance.get("recent_success_rates", [])
        },
        "current_metrics": {
            "epsilon": stats.get("epsilon", 0),
            "learning_rate": stats.get("learning_rate", 0),
            "temperature": stats.get("temperature", 0),
            "success_rate": stats.get("success_rate", 0),
            "average_reward": stats.get("average_reward", 0)
        },
        "learning_efficiency": {
            "total_episodes": stats.get("episode_count", 0),
            "total_steps": stats.get("step_count", 0),
            "q_table_entries": stats.get("q_table_size", 0),
            "replay_buffer_size": stats.get("replay_buffer_size", 0)
        }
    }


@app.post("/api/rl-agent/reset")
async def reset_rl_agent():
    """
    Reset the RL agent to initial state.
    Useful for starting fresh experiments.
    """
    ai_agent.reset()
    return {"message": "RL agent reset successfully", "status": "ready"}


@app.get("/api/rl-agent/q-table")
async def get_q_table_sample():
    """
    Get a sample of the Q-table for inspection.
    Shows learned state-action values.
    """
    q_table = ai_agent.q_table.table
    
    # Return sample (first 10 states) to avoid overwhelming response
    sample = {}
    count = 0
    for state, actions in q_table.items():
        if count >= 10:
            break
        sample[state] = actions
        count += 1
    
    return {
        "total_states": len(q_table),
        "sample": sample,
        "note": "Showing first 10 states. Full Q-table contains learned state-action values."
    }


@app.post("/api/rl-agent/save")
async def save_rl_model():
    """
    Save the current RL model to disk.
    Allows persistence of learned policies.
    """
    try:
        model_path = "models/rl_agent_model.json"
        os.makedirs("models", exist_ok=True)
        ai_agent.save_model(model_path)
        return {
            "message": "RL model saved successfully",
            "path": model_path,
            "statistics": ai_agent.get_statistics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save model: {str(e)}")


@app.post("/api/rl-agent/load")
async def load_rl_model():
    """
    Load a previously saved RL model.
    Restores learned policies.
    """
    try:
        model_path = "models/rl_agent_model.json"
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model file not found")
        
        ai_agent.load_model(model_path)
        return {
            "message": "RL model loaded successfully",
            "path": model_path,
            "statistics": ai_agent.get_statistics()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


# ---------------------------------------------------------------------------
# Compliance Dashboard & Report Generation
# ---------------------------------------------------------------------------

from compliance import ComplianceMapper, ComplianceFramework
from report_generator import SecurityReportGenerator

# Initialize compliance and report services
compliance_mapper = ComplianceMapper()
report_generator = SecurityReportGenerator()


class ComplianceRequest(BaseModel):
    vulnerabilities: List[str]
    attack_path: Optional[List[Dict]] = None
    frameworks: Optional[List[str]] = None  # ["PCI-DSS", "HIPAA", "SOC2", "ISO27001"]


class ComplianceScoreResponse(BaseModel):
    framework: str
    score: float
    total_requirements: int
    compliant: int
    non_compliant: int
    critical_findings: int
    high_findings: int


@app.post("/api/compliance/analyze")
async def analyze_compliance(request: ComplianceRequest):
    """
    Map vulnerabilities to compliance frameworks and calculate scores.
    Supports PCI-DSS, HIPAA, SOC2, and ISO27001.
    """
    try:
        # Parse frameworks
        frameworks = None
        if request.frameworks:
            frameworks = [
                ComplianceFramework(f) for f in request.frameworks
                if f in [cf.value for cf in ComplianceFramework]
            ]
        
        # Get compliance findings
        findings = compliance_mapper.map_findings(
            vulnerabilities=request.vulnerabilities,
            attack_path=request.attack_path or [],
            frameworks=frameworks
        )
        
        # Calculate scores
        scores = compliance_mapper.calculate_compliance_scores(findings)
        
        # Format response
        scores_response = []
        findings_response = {}
        
        for framework, score in scores.items():
            scores_response.append({
                "framework": framework.value,
                "score": round(score.score, 1),
                "total_requirements": score.total_requirements,
                "compliant": score.compliant,
                "non_compliant": score.non_compliant,
                "critical_findings": score.critical_findings,
                "high_findings": score.high_findings
            })
            
            # Format findings for this framework
            framework_findings = findings.get(framework, [])
            findings_response[framework.value] = [
                {
                    "requirement_id": f.requirement.requirement_id,
                    "requirement_name": f.requirement.title,
                    "status": f.status,
                    "severity": f.requirement.severity,
                    "vulnerability": f.vulnerability,
                    "description": f.requirement.description,
                    "remediation": f.remediation
                }
                for f in framework_findings
            ]
        
        return {
            "scores": scores_response,
            "findings": findings_response,
            "summary": {
                "total_vulnerabilities": len(request.vulnerabilities),
                "frameworks_analyzed": len(scores_response),
                "average_score": round(
                    sum(s["score"] for s in scores_response) / len(scores_response), 1
                ) if scores_response else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance analysis failed: {str(e)}")


@app.get("/api/compliance/frameworks")
async def get_compliance_frameworks():
    """
    Get list of supported compliance frameworks.
    """
    return {
        "frameworks": [
            {
                "id": "PCI-DSS",
                "name": "Payment Card Industry Data Security Standard",
                "description": "Security standard for organizations handling credit cards",
                "requirements_count": 12
            },
            {
                "id": "HIPAA",
                "name": "Health Insurance Portability and Accountability Act",
                "description": "US law for protecting sensitive patient health information",
                "requirements_count": 8
            },
            {
                "id": "SOC2",
                "name": "Service Organization Control 2",
                "description": "Auditing procedure for service organizations",
                "requirements_count": 5
            },
            {
                "id": "ISO27001",
                "name": "ISO/IEC 27001",
                "description": "International standard for information security management",
                "requirements_count": 14
            }
        ]
    }


@app.post("/api/compliance/gap-analysis")
async def compliance_gap_analysis(request: ComplianceRequest):
    """
    Perform gap analysis showing compliance gaps and remediation priorities.
    """
    try:
        frameworks = None
        if request.frameworks:
            frameworks = [
                ComplianceFramework(f) for f in request.frameworks
                if f in [cf.value for cf in ComplianceFramework]
            ]
        
        gap_analysis = compliance_mapper.get_gap_analysis(
            vulnerabilities=request.vulnerabilities,
            attack_path=request.attack_path or [],
            frameworks=frameworks
        )
        
        return gap_analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(e)}")


class ReportGenerationRequest(BaseModel):
    simulation_id: Optional[int] = None  # Use stored simulation or provide data
    target: str = "Target System"
    vulnerabilities: Optional[List[str]] = None
    attack_path: Optional[List[Dict]] = None
    simulation_result: Optional[Dict] = None
    include_compliance: bool = True
    frameworks: Optional[List[str]] = None


@app.post("/api/reports/generate")
async def generate_security_report(request: ReportGenerationRequest):
    """
    Generate a professional security assessment report.
    Returns JSON data and HTML report content.
    """
    try:
        # Get data from stored simulation if simulation_id provided
        if request.simulation_id:
            paths = storage.get_all_paths()
            simulation_data = next(
                (p for p in paths if p.get("id") == request.simulation_id),
                None
            )
            if not simulation_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation {request.simulation_id} not found"
                )
            
            attack_path = simulation_data.get("path", [])
            vulnerabilities = simulation_data.get("vulnerabilities", [])
            simulation_result = {
                "final_access_level": simulation_data.get("final_access_level", "none"),
                "successful_attacks": len([s for s in attack_path if s.get("success")]),
                "failed_attacks": len([s for s in attack_path if not s.get("success")])
            }
        else:
            # Use provided data
            attack_path = request.attack_path or []
            vulnerabilities = request.vulnerabilities or []
            simulation_result = request.simulation_result or {
                "final_access_level": "none",
                "successful_attacks": 0,
                "failed_attacks": 0
            }
        
        # Generate report
        report = report_generator.generate_report(
            simulation_result=simulation_result,
            attack_path=attack_path,
            vulnerabilities=vulnerabilities,
            target=request.target,
            include_compliance=request.include_compliance,
            frameworks=request.frameworks
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/api/reports/latest")
async def get_latest_report():
    """
    Generate a report from the most recent simulation.
    """
    try:
        best_path = storage.get_best_attack_path()
        if not best_path:
            raise HTTPException(status_code=404, detail="No simulations found")
        
        attack_path = best_path.get("path", [])
        vulnerabilities = best_path.get("vulnerabilities", [])
        simulation_result = {
            "final_access_level": best_path.get("final_access_level", "none"),
            "successful_attacks": len([s for s in attack_path if s.get("success")]),
            "failed_attacks": len([s for s in attack_path if not s.get("success")])
        }
        
        report = report_generator.generate_report(
            simulation_result=simulation_result,
            attack_path=attack_path,
            vulnerabilities=vulnerabilities,
            target="Latest Simulation Target",
            include_compliance=True
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/api/reports/download/{report_id}")
async def download_report(report_id: str, format: str = "html"):
    """
    Download a generated report as HTML file.
    """
    try:
        # For now, generate a fresh report (in production, would fetch from storage)
        best_path = storage.get_best_attack_path()
        if not best_path:
            raise HTTPException(status_code=404, detail="No simulations found")
        
        attack_path = best_path.get("path", [])
        vulnerabilities = best_path.get("vulnerabilities", [])
        simulation_result = {
            "final_access_level": best_path.get("final_access_level", "none"),
            "successful_attacks": len([s for s in attack_path if s.get("success")]),
            "failed_attacks": len([s for s in attack_path if not s.get("success")])
        }
        
        report = report_generator.generate_report(
            simulation_result=simulation_result,
            attack_path=attack_path,
            vulnerabilities=vulnerabilities,
            target="Security Assessment",
            include_compliance=True
        )
        
        # Return HTML as downloadable file
        from fastapi.responses import Response
        
        return Response(
            content=report["html_report"],
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=security-report-{report_id}.html"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report download failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
FastAPI backend for ART-AI offensive security simulation system.
Exposes APIs for attack simulation, state management, and AI agent control.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import uvicorn
from dotenv import load_dotenv

# Load .env so OPENAI_API_KEY is available for the pentest chat
load_dotenv()

from env import EnvironmentState, AccessLevel
from attack_engine import AttackEngine, AttackAction, AttackResult
from ai_agent import QLearningAgent
from storage import AttackPathStorage
from recon import ReconEngine
from vulnerability_scanner import VulnerabilityScanner
from exploit_generator import ExploitGenerator, ExploitType
from ai.knowledge import ExploitLibrarian

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
ai_agent = QLearningAgent()
storage = AttackPathStorage()
recon_engine = ReconEngine()
vuln_scanner = VulnerabilityScanner()
exploit_generator = ExploitGenerator()
# Knowledge-Augmented RL: Exploit-DB Librarian
exploit_librarian = ExploitLibrarian(demo_mode=True)  # Set to False if searchsploit is installed


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
    reward = ai_agent.calculate_reward(result, environment)
    
    # Update agent's Q-table
    state_key = environment.current_access_level.value
    ai_agent.update_q_value(state_key, action.value, reward, result.new_access_level.value)
    
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
        
        # Update Q-table
        new_state_key = result.new_access_level.value
        ai_agent.update_q_value(state_key, action_str, reward, new_state_key)

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

        if result.success:
            successful_attacks += 1
        else:
            failed_attacks += 1

        # Stop if admin access achieved
        if environment.current_access_level == AccessLevel.ADMIN:
            break

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
    return {"paths": paths}


@app.get("/api/best-path")
async def get_best_attack_path():
    """Get the best (most successful) attack path"""
    best_path = storage.get_best_attack_path()
    if not best_path:
        raise HTTPException(status_code=404, detail="No attack paths found")
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
    conversation_history: Optional[List[ChatMessage]] = None
    api_key: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    error: Optional[str] = None


# Local Llama config for Pentest AI Assistant (llama-cpp-python + Hugging Face GGUF)
LLAMA_REPO_ID = "DavidAU/OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf"
LLAMA_FILENAME = "OpenAI-20B-NEO-CODE-DI-Uncensored-Q5_1.gguf"

_llama_model = None


def _get_llama_model():
    """Load local Llama model from Hugging Face (lazy, once)."""
    global _llama_model
    if _llama_model is not None:
        return _llama_model
    try:
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama
    except ImportError as e:
        raise RuntimeError(
            "Missing dependencies. In the backend folder run: pip install llama-cpp-python huggingface_hub. "
            "If pip fails (e.g. on Python 3.13), use a virtualenv with Python 3.10-3.12."
        )
    try:
        model_path = hf_hub_download(
            repo_id=LLAMA_REPO_ID,
            filename=LLAMA_FILENAME,
        )
        _llama_model = Llama(model_path=model_path)
        return _llama_model
    except Exception as e:
        raise RuntimeError(f"Failed to load local Llama model: {e}")


@app.post("/api/chat", response_model=ChatResponse)
async def pentest_chat(request: ChatRequest):
    """
    AI chatbot for penetration testers: ask questions or request exploit generation.
    Uses local Llama model (llama-cpp-python) from Hugging Face. No API key required.
    """
    messages = [{"role": "system", "content": PENTEST_SYSTEM_PROMPT}]
    if request.conversation_history:
        for msg in request.conversation_history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    try:
        llm = _get_llama_model()
        # Run blocking inference in thread pool so we don't block the event loop
        import asyncio

        loop = asyncio.get_event_loop()

        def _run_completion():
            return llm.create_chat_completion(
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
            )

        response = await loop.run_in_executor(None, _run_completion)
        choices = response.get("choices") or []
        if not choices:
            return ChatResponse(reply="", error="Local model returned no response.")
        reply = (choices[0].get("message") or {}).get("content") or ""
        return ChatResponse(reply=reply)
    except RuntimeError as e:
        return ChatResponse(reply="", error=str(e))
    except Exception as e:
        return ChatResponse(reply="", error=f"AI request failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


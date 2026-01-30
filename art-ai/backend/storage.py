"""
Storage module for recording attack paths and simulation results.
Uses SQLite for persistent storage.
"""

import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class AttackPathStorage:
    """
    Stores attack paths and simulation results in SQLite database.
    Provides querying for best attack paths and statistics.
    """

    def __init__(self, db_path: str = "attack_paths.db"):
        """Initialize storage with SQLite database"""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Attack paths table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                final_access_level TEXT NOT NULL,
                total_iterations INTEGER NOT NULL,
                successful_attacks INTEGER NOT NULL,
                failed_attacks INTEGER NOT NULL,
                discovered_vulnerabilities TEXT,
                attack_path_json TEXT NOT NULL,
                score REAL DEFAULT 0.0
            )
        """)

        # Statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS path_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                FOREIGN KEY (path_id) REFERENCES attack_paths(id)
            )
        """)

        conn.commit()
        conn.close()

    def save_attack_path(
        self,
        attack_path: List[Dict],
        final_access_level: str,
        vulnerabilities: List[str],
        score: Optional[float] = None
    ):
        """
        Save an attack path to database.
        
        Args:
            attack_path: List of attack steps
            final_access_level: Final access level achieved
            vulnerabilities: List of discovered vulnerabilities
            score: Optional score for ranking
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate statistics
        successful_attacks = sum(1 for step in attack_path if step.get("success", False))
        failed_attacks = len(attack_path) - successful_attacks

        # Calculate score if not provided
        if score is None:
            score = self._calculate_path_score(
                final_access_level,
                successful_attacks,
                failed_attacks,
                len(vulnerabilities)
            )

        # Insert attack path
        cursor.execute("""
            INSERT INTO attack_paths 
            (final_access_level, total_iterations, successful_attacks, 
             failed_attacks, discovered_vulnerabilities, attack_path_json, score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            final_access_level,
            len(attack_path),
            successful_attacks,
            failed_attacks,
            json.dumps(vulnerabilities),
            json.dumps(attack_path),
            score
        ))

        path_id = cursor.lastrowid

        # Update statistics
        self._update_statistics(cursor, path_id, attack_path)

        conn.commit()
        conn.close()

        return path_id

    def _calculate_path_score(
        self,
        final_access_level: str,
        successful_attacks: int,
        failed_attacks: int,
        vulnerability_count: int
    ) -> float:
        """Calculate score for attack path"""
        # Access level weights
        level_scores = {
            "none": 0,
            "public": 10,
            "internal": 30,
            "admin": 100
        }

        base_score = level_scores.get(final_access_level, 0)
        
        # Success ratio bonus
        total_attacks = successful_attacks + failed_attacks
        if total_attacks > 0:
            success_ratio = successful_attacks / total_attacks
            base_score *= (1 + success_ratio)

        # Vulnerability discovery bonus
        base_score += vulnerability_count * 5

        # Efficiency penalty (fewer failed attempts is better)
        if failed_attacks > 0:
            base_score -= failed_attacks * 0.5

        return base_score

    def _update_statistics(self, cursor, path_id: int, attack_path: List[Dict]):
        """Update action statistics for path"""
        action_stats = {}

        for step in attack_path:
            action = step.get("action", "unknown")
            success = step.get("success", False)

            if action not in action_stats:
                action_stats[action] = {"success": 0, "failure": 0}

            if success:
                action_stats[action]["success"] += 1
            else:
                action_stats[action]["failure"] += 1

        # Insert statistics
        for action, stats in action_stats.items():
            cursor.execute("""
                INSERT INTO path_statistics (path_id, action_type, success_count, failure_count)
                VALUES (?, ?, ?, ?)
            """, (path_id, action, stats["success"], stats["failure"]))

    def get_best_attack_path(self) -> Optional[Dict]:
        """
        Get the best attack path based on score.
        Returns path with highest score.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, final_access_level, total_iterations, successful_attacks,
                   failed_attacks, discovered_vulnerabilities, attack_path_json, score
            FROM attack_paths
            ORDER BY score DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "final_access_level": row[1],
            "total_iterations": row[2],
            "successful_attacks": row[3],
            "failed_attacks": row[4],
            "discovered_vulnerabilities": json.loads(row[5]),
            "attack_path": json.loads(row[6]),
            "score": row[7]
        }

    def get_all_paths(self, limit: int = 10) -> List[Dict]:
        """Get all attack paths, ordered by score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, final_access_level, total_iterations, successful_attacks,
                   failed_attacks, discovered_vulnerabilities, attack_path_json, score, created_at
            FROM attack_paths
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        paths = []
        for row in rows:
            paths.append({
                "id": row[0],
                "final_access_level": row[1],
                "total_iterations": row[2],
                "successful_attacks": row[3],
                "failed_attacks": row[4],
                "discovered_vulnerabilities": json.loads(row[5]),
                "attack_path": json.loads(row[6]),
                "score": row[7],
                "created_at": row[8]
            })

        return paths

    def get_path_by_id(self, path_id: int) -> Optional[Dict]:
        """Get specific attack path by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, final_access_level, total_iterations, successful_attacks,
                   failed_attacks, discovered_vulnerabilities, attack_path_json, score
            FROM attack_paths
            WHERE id = ?
        """, (path_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "final_access_level": row[1],
            "total_iterations": row[2],
            "successful_attacks": row[3],
            "failed_attacks": row[4],
            "discovered_vulnerabilities": json.loads(row[5]),
            "attack_path": json.loads(row[6]),
            "score": row[7]
        }

    def get_statistics(self) -> Dict:
        """Get overall statistics from all paths"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_paths,
                AVG(score) as avg_score,
                MAX(score) as max_score,
                SUM(successful_attacks) as total_successful,
                SUM(failed_attacks) as total_failed
            FROM attack_paths
        """)

        row = cursor.fetchone()

        # Action statistics
        cursor.execute("""
            SELECT 
                action_type,
                SUM(success_count) as total_success,
                SUM(failure_count) as total_failure
            FROM path_statistics
            GROUP BY action_type
            ORDER BY total_success DESC
        """)

        action_stats = []
        for stat_row in cursor.fetchall():
            action_stats.append({
                "action": stat_row[0],
                "success_count": stat_row[1],
                "failure_count": stat_row[2]
            })

        conn.close()

        return {
            "total_paths": row[0] or 0,
            "average_score": row[1] or 0.0,
            "max_score": row[2] or 0.0,
            "total_successful_attacks": row[3] or 0,
            "total_failed_attacks": row[4] or 0,
            "action_statistics": action_stats
        }


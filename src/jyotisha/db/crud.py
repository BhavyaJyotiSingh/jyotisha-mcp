"""
Database CRUD Operations with AES-256 Encryption/Decryption

Implements secure storage and retrieval of astrological charts,
predictions, and cache data with GCM encryption for PII.
"""

from __future__ import annotations
import json
import uuid
from typing import Optional, Any

from jyotisha.db.database import get_db
from jyotisha.security import encrypt_data, decrypt_data

def save_chart(
    chart_id: str,
    name: str,
    datetime_utc: str,
    latitude: float,
    longitude: float,
    location_name: str,
    ayanamsha: str,
    house_system: str,
    chart_json: str
) -> None:
    """Save an astrological chart and its cache with field encryption."""
    # Encrypt identifying PII fields
    encrypted_name = encrypt_data(name)
    encrypted_location = encrypt_data(location_name)
    encrypted_json = encrypt_data(chart_json)

    with get_db() as conn:
        # Save to charts table
        conn.execute(
            """
            INSERT OR REPLACE INTO charts (id, name, datetime_utc, latitude, longitude, location_name, ayanamsha, house_system)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chart_id, encrypted_name, datetime_utc, latitude, longitude, encrypted_location, ayanamsha, house_system)
        )
        
        # Save to chart_cache table
        conn.execute(
            """
            INSERT OR REPLACE INTO chart_cache (chart_id, chart_json)
            VALUES (?, ?)
            """,
            (chart_id, encrypted_json)
        )
        conn.commit()

def get_chart(chart_id: str) -> Optional[dict[str, Any]]:
    """Retrieve an astrological chart and decrypt all encrypted data."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Join charts and chart_cache
        cursor.execute(
            """
            SELECT c.id, c.name, c.datetime_utc, c.latitude, c.longitude, c.location_name, c.ayanamsha, c.house_system, cc.chart_json
            FROM charts c
            LEFT JOIN chart_cache cc ON c.id = cc.chart_id
            WHERE c.id = ?
            """,
            (chart_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Decrypt fields
        decrypted_name = decrypt_data(row["name"]) if row["name"] else ""
        decrypted_location = decrypt_data(row["location_name"]) if row["location_name"] else ""
        
        decrypted_json = None
        if row["chart_json"]:
            try:
                decrypted_json = json.loads(decrypt_data(row["chart_json"]))
            except Exception:
                pass

        return {
            "id": row["id"],
            "name": decrypted_name,
            "datetime_utc": row["datetime_utc"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "location_name": decrypted_location,
            "ayanamsha": row["ayanamsha"],
            "house_system": row["house_system"],
            "chart_data": decrypted_json
        }

def save_prediction(
    prediction_id: str,
    chart_id: str,
    question: str,
    consensus_json: str
) -> None:
    """Save a prediction and encrypt the consensus report data."""
    encrypted_consensus = encrypt_data(consensus_json)
    
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO predictions (id, chart_id, question, consensus_json)
            VALUES (?, ?, ?, ?)
            """,
            (prediction_id, chart_id, question, encrypted_consensus)
        )
        conn.commit()

def get_prediction(prediction_id: str) -> Optional[dict[str, Any]]:
    """Retrieve and decrypt prediction details."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, chart_id, question, consensus_json, created_at
            FROM predictions
            WHERE id = ?
            """,
            (prediction_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
            
        decrypted_consensus = None
        if row["consensus_json"]:
            try:
                decrypted_consensus = json.loads(decrypt_data(row["consensus_json"]))
            except Exception:
                pass
                
        return {
            "id": row["id"],
            "chart_id": row["chart_id"],
            "question": row["question"],
            "consensus": decrypted_consensus,
            "created_at": row["created_at"]
        }

import pytest
import sqlite3
import json
from jyotisha.security.encryption import encrypt_data, decrypt_data
from jyotisha.db.database import init_db, get_db_path
from jyotisha.db.crud import save_chart, get_chart, save_prediction, get_prediction

@pytest.fixture(autouse=True)
def setup_db():
    # Make sure DB schema is initialized
    init_db()

def test_encryption_roundtrip():
    plaintext = "Mahatma Gandhi birth details"
    ciphertext = encrypt_data(plaintext)
    
    assert ciphertext != plaintext
    assert len(ciphertext) > 0
    
    decrypted = decrypt_data(ciphertext)
    assert decrypted == plaintext

def test_encryption_empty():
    assert encrypt_data("") == ""
    assert decrypt_data("") == ""

def test_decryption_invalid():
    with pytest.raises(ValueError):
        decrypt_data("invalid_base64_ciphertext")

def test_database_crud_encryption():
    chart_id = "test-uuid-12345"
    name = "Isaac Newton"
    dt = "1643-01-04T12:00:00"
    lat = 52.809
    lon = -0.635
    loc = "Woolsthorpe"
    ayanamsha = "Lahiri"
    h_system = "Placidus"
    dummy_json = json.dumps({"planet_positions": {"Sun": 280.5, "Moon": 90.2}})

    # Save to db
    save_chart(
        chart_id=chart_id,
        name=name,
        datetime_utc=dt,
        latitude=lat,
        longitude=lon,
        location_name=loc,
        ayanamsha=ayanamsha,
        house_system=h_system,
        chart_json=dummy_json
    )

    # Fetch and decrypt
    retrieved = get_chart(chart_id)
    assert retrieved is not None
    assert retrieved["name"] == name
    assert retrieved["location_name"] == loc
    assert retrieved["chart_data"] == json.loads(dummy_json)

    # Query raw database directly to verify it's encrypted at rest
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name, location_name FROM charts WHERE id = ?", (chart_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    # Raw value must be encrypted base64 string, not "Isaac Newton"
    assert row["name"] != name
    assert row["location_name"] != loc
    assert "Isaac" not in row["name"]

def test_prediction_crud_encryption():
    prediction_id = "pred-uuid-999"
    chart_id = "test-uuid-12345"
    question = "marriage"
    consensus_data = {"verdict": "Likely in 2029", "confidence": 0.85}
    consensus_json = json.dumps(consensus_data)

    # Save
    save_prediction(
        prediction_id=prediction_id,
        chart_id=chart_id,
        question=question,
        consensus_json=consensus_json
    )

    # Retrieve
    retrieved = get_prediction(prediction_id)
    assert retrieved is not None
    assert retrieved["question"] == question
    assert retrieved["consensus"] == consensus_data

    # Verify database holds encrypted data
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT consensus_json FROM predictions WHERE id = ?", (prediction_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["consensus_json"] != consensus_json
    assert "verdict" not in row["consensus_json"]

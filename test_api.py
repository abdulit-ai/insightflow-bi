import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app

SAMPLE=b"order_id,order_date,customer,segment,region,product,category,quantity,unit_price\nA1,2026-01-01,Ada,Retail,North,Laptop,Electronics,2,100.50\nA2,2026-02-01,Bola,Business,South,Desk,Furniture,1,50.00\n"

def client_fixture():
    tmp=tempfile.TemporaryDirectory()
    eng=create_engine("sqlite:///"+str(Path(tmp.name)/"test.db"),connect_args={"check_same_thread":False})
    Base.metadata.create_all(eng)
    Session=sessionmaker(bind=eng)
    def override():
        with Session() as db: yield db
    app.dependency_overrides[get_db]=override
    return TestClient(app),tmp,eng

def test_import_and_dashboard():
    client,tmp,eng=client_fixture()
    try:
        assert client.get("/api/health").json()=={"status":"ok"}
        r=client.post("/api/import",files={"file":("sales.csv",SAMPLE,"text/csv")})
        assert r.status_code==200 and r.json()["imported"]==2
        assert client.post("/api/import",files={"file":("sales.csv",SAMPLE,"text/csv")}).json()["skipped_duplicates"]==2
        data=client.get("/api/dashboard").json()
        assert data["kpis"]=={"revenue":251.0,"orders":2,"units":3,"customers":2,"average_order_value":125.5}
        assert client.get("/api/dashboard?region=North").json()["kpis"]["revenue"]==201.0
        assert client.get("/api/dashboard?start=2026-02-01").json()["kpis"]["orders"]==1
    finally:
        app.dependency_overrides.clear();eng.dispose();tmp.cleanup()

def test_invalid_csv_rolls_back():
    client,tmp,eng=client_fixture()
    try:
        invalid=SAMPLE+b"A3,2026-01-03,C,Retail,West,Phone,Electronics,-1,5\n"
        r=client.post("/api/import",files={"file":("bad.csv",invalid,"text/csv")})
        assert r.status_code==422
        assert client.get("/api/dashboard").json()["kpis"]["orders"]==0
        assert client.get("/api/dashboard?start=2026-03-01&end=2026-01-01").status_code==422
    finally:
        app.dependency_overrides.clear();eng.dispose();tmp.cleanup()

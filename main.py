import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Customer, Product, Sale

app = FastAPI(title="InsightFlow BI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET","POST"], allow_headers=["*"], allow_credentials=False)
Base.metadata.create_all(bind=engine)
REQUIRED = {"order_id","order_date","customer","segment","region","product","category","quantity","unit_price"}
MAX_BYTES = 3_000_000

def import_csv(content: bytes, db: Session):
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "CSV must be 3 MB or smaller")
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must contain: " + ", ".join(sorted(REQUIRED)))
        rows = list(reader)
        if len(rows) > 10000:
            raise ValueError("Maximum 10,000 rows per upload")
        prepared = []
        seen = set()
        for i, row in enumerate(rows, 2):
            order_id = row["order_id"].strip()
            if not order_id or order_id in seen:
                raise ValueError(f"Row {i}: missing or duplicate order_id")
            seen.add(order_id)
            d = date.fromisoformat(row["order_date"].strip())
            qty = int(row["quantity"])
            price = Decimal(row["unit_price"])
            if qty <= 0 or not price.is_finite() or price < 0:
                raise ValueError(f"Row {i}: quantity must be positive and price nonnegative")
            vals = [row[k].strip() for k in ("customer","segment","region","product","category")]
            if any(not x or len(x) > 120 for x in vals):
                raise ValueError(f"Row {i}: invalid text field")
            prepared.append((order_id,d,qty,price,*vals))
    except (UnicodeError, csv.Error, ValueError, InvalidOperation, TypeError, KeyError) as exc:
        raise HTTPException(422, f"Invalid CSV: {exc}") from exc
    added = 0
    try:
        existing = set(db.scalars(select(Sale.external_id).where(Sale.external_id.in_(seen))).all()) if seen else set()
        customers = {(c.name,c.segment,c.region):c for c in db.scalars(select(Customer)).all()}
        products = {(x.name,x.category):x for x in db.scalars(select(Product)).all()}
        for oid,d,qty,price,cname,seg,reg,pname,cat in prepared:
            if oid in existing: continue
            ck = (cname,seg,reg)
            if ck not in customers:
                customers[ck] = Customer(name=cname,segment=seg,region=reg)
                db.add(customers[ck]); db.flush()
            pk = (pname,cat)
            if pk not in products:
                products[pk] = Product(name=pname,category=cat)
                db.add(products[pk]); db.flush()
            db.add(Sale(external_id=oid,order_date=d,customer_id=customers[ck].id,product_id=products[pk].id,quantity=qty,unit_price=price))
            added += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"imported":added,"skipped_duplicates":len(prepared)-added}

@app.get("/api/health")
def health(): return {"status":"ok"}

@app.post("/api/import")
async def upload(file: UploadFile = File(...), db:Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(422,"Upload a .csv file")
    return import_csv(await file.read(MAX_BYTES+1), db)

@app.post("/api/seed")
def seed(db:Session = Depends(get_db)):
    path = Path(__file__).resolve().parents[2] / "data" / "sample_sales.csv"
    if not path.exists(): path = Path("/data/sample_sales.csv")
    if not path.exists(): raise HTTPException(404,"Sample CSV not found")
    return import_csv(path.read_bytes(),db)

def filtered(db, start, end, region, category):
    stmt = select(Sale).join(Customer).join(Product)
    if start: stmt=stmt.where(Sale.order_date>=start)
    if end: stmt=stmt.where(Sale.order_date<=end)
    if region: stmt=stmt.where(Customer.region==region)
    if category: stmt=stmt.where(Product.category==category)
    return db.scalars(stmt).all()

@app.get("/api/dashboard")
def dashboard(start:date|None=None,end:date|None=None,region:str|None=None,category:str|None=None,db:Session=Depends(get_db)):
    if start and end and start>end: raise HTTPException(422,"start must be <= end")
    sales=filtered(db,start,end,region,category)
    monthly={}; regions={}; categories={}; products={}; customers=set()
    revenue=Decimal("0")
    for s in sales:
        amount=s.unit_price*s.quantity; revenue+=amount; customers.add(s.customer_id)
        month=s.order_date.strftime("%Y-%m")
        for bucket,key in ((monthly,month),(regions,s.customer.region),(categories,s.product.category),(products,s.product.name)):
            bucket[key]=bucket.get(key,Decimal("0"))+amount
    def series(bucket,sort=True):
        items=sorted(bucket.items()) if sort else sorted(bucket.items(),key=lambda x:x[1],reverse=True)
        return [{"name":k,"revenue":round(float(v),2)} for k,v in items]
    return {"kpis":{"revenue":round(float(revenue),2),"orders":len(sales),"units":sum(s.quantity for s in sales),"customers":len(customers),"average_order_value":round(float(revenue/len(sales)),2) if sales else 0},"monthly":series(monthly),"regions":series(regions,False),"categories":series(categories,False),"top_products":series(products,False)[:8],"filters":{"regions":sorted(set(db.scalars(select(Customer.region)).all())),"categories":sorted(set(db.scalars(select(Product.category)).all()))}}

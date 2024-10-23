from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List
from pydantic import BaseModel

# 数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./Chinook.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI 应用
app = FastAPI()

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建视图函数
def create_views(engine):
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE VIEW IF NOT EXISTS vw_customer_countries AS
        SELECT CustomerId as id, FirstName, LastName, Country
        FROM Customer;
        """))
        
        conn.execute(text("""
        CREATE VIEW IF NOT EXISTS vw_artist_album_count AS
        SELECT Artist.ArtistId, Artist.Name AS ArtistName, COUNT(Album.AlbumId) AS AlbumCount
        FROM Artist
        LEFT JOIN Album ON Artist.ArtistId = Album.ArtistId
        GROUP BY Artist.ArtistId;
        """))
        
        conn.execute(text("""
        CREATE VIEW IF NOT EXISTS vw_invoice_details AS
        SELECT 
            i.InvoiceId,
            c.FirstName || ' ' || c.LastName AS CustomerName,
            i.InvoiceDate,
            SUM(ii.UnitPrice * ii.Quantity) AS TotalAmount
        FROM Invoice i
        JOIN Customer c ON i.CustomerId = c.CustomerId
        JOIN InvoiceLine ii ON i.InvoiceId = ii.InvoiceId
        GROUP BY i.InvoiceId;
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0
        )
        """))

# 创建视图
create_views(engine)

# Pydantic 模型用于响应
class CustomerCountry(BaseModel):
    id: int
    FirstName: str
    LastName: str
    Country: str

class ArtistAlbumCount(BaseModel):
    ArtistId: int
    ArtistName: str
    AlbumCount: int

class InvoiceDetail(BaseModel):
    InvoiceId: int
    CustomerName: str
    InvoiceDate: str
    TotalAmount: float

# API 路由
@app.get("/customer_countries", response_model=List[CustomerCountry])
def read_customer_countries(db: SessionLocal = Depends(get_db)):
    result = db.execute(text("SELECT * FROM vw_customer_countries"))
    return [CustomerCountry(**row._asdict()) for row in result]

@app.get("/artist_album_count", response_model=List[ArtistAlbumCount])
def read_artist_album_count(db: SessionLocal = Depends(get_db)):
    result = db.execute(text("SELECT * FROM vw_artist_album_count"))
    return [ArtistAlbumCount(**row._asdict()) for row in result]

@app.get("/invoice_details", response_model=List[InvoiceDetail])
def read_invoice_details(db: SessionLocal = Depends(get_db)):
    result = db.execute(text("SELECT * FROM vw_invoice_details"))
    return [InvoiceDetail(**row._asdict()) for row in result]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import create_document, get_documents, db
from schemas import Product, ContactMessage, Booking, NewsletterSignup

app = FastAPI(title="Botanical Boutique API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Botanical Boutique API running"}

# Public catalog endpoints
@app.get("/api/products", response_model=List[dict])
def list_products(
    category: Optional[str] = None,
    occasion: Optional[str] = None,
    color: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 50,
):
    filt = {}
    if category:
        filt["category"] = category
    if occasion:
        filt["occasion"] = occasion
    if color:
        filt["color"] = color
    if min_price is not None or max_price is not None:
        price = {}
        if min_price is not None:
            price["$gte"] = float(min_price)
        if max_price is not None:
            price["$lte"] = float(max_price)
        filt["price"] = price

    docs = get_documents("product", filt, limit)
    # Convert ObjectId to string
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return docs

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        doc["id"] = str(doc.pop("_id"))
        return doc
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

@app.post("/api/products")
def create_product(product: Product):
    inserted_id = create_document("product", product)
    return {"id": inserted_id}

# Content endpoints: contact, bookings, newsletter
@app.post("/api/contact")
def contact(message: ContactMessage):
    inserted_id = create_document("contactmessage", message)
    return {"id": inserted_id, "status": "received"}

@app.post("/api/booking")
def booking(b: Booking):
    inserted_id = create_document("booking", b)
    return {"id": inserted_id, "status": "requested"}

@app.post("/api/newsletter")
def newsletter(n: NewsletterSignup):
    inserted_id = create_document("newslettersignup", n)
    return {"id": inserted_id, "status": "subscribed"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
Shopify router: OAuth flow, data sync, and connection status.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from db.models import ShopifyConnection
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shopify", tags=["shopify"])


@router.get("/status")
async def shopify_status(x_user_id: str = Header(default="default-user")):
    """Returns Shopify connection status for the user."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == x_user_id)
        )
        conn = result.scalar_one_or_none()

        if not conn:
            return {"connected": False}

        return {
            "connected": True,
            "shop_domain": conn.shop_domain,
            "products_synced": conn.products_synced,
            "orders_synced": conn.orders_synced,
            "reviews_synced": conn.reviews_synced,
            "last_sync": conn.last_sync.isoformat() if conn.last_sync else None,
        }


@router.get("/auth")
async def shopify_auth(shop: str):
    """Redirect user to Shopify OAuth URL."""
    import os
    api_key = os.getenv("SHOPIFY_API_KEY", "")
    redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI", "http://localhost:8000/api/shopify/callback")
    scopes = "read_products,read_orders,read_customers"

    if not api_key:
        raise HTTPException(status_code=503, detail="Shopify app not configured.")

    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def shopify_callback(
    shop: str,
    code: str,
    x_user_id: str = Header(default="default-user"),
):
    """Exchange OAuth code for access_token and trigger initial sync."""
    import os
    import httpx

    api_key = os.getenv("SHOPIFY_API_KEY", "")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    if not api_key:
        raise HTTPException(status_code=503, detail="Shopify app not configured.")

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": api_key, "client_secret": api_secret, "code": code},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="OAuth token exchange failed.")
        token_data = resp.json()
        access_token = token_data.get("access_token")

    # Save to DB
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == x_user_id)
        )
        conn = existing.scalar_one_or_none()
        if not conn:
            conn = ShopifyConnection(user_id=x_user_id)
            db.add(conn)
        conn.shop_domain = shop
        conn.access_token = access_token
        await db.commit()

    # Trigger async sync
    import asyncio, threading
    threading.Thread(
        target=lambda: asyncio.run(_do_sync(shop, access_token, x_user_id)),
        daemon=True,
    ).start()

    return RedirectResponse(url=f"{frontend_url}/dashboard")


@router.post("/sync")
async def trigger_sync(x_user_id: str = Header(default="default-user")):
    """Manually trigger a Shopify re-sync."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == x_user_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="No Shopify connection found.")

    import asyncio, threading
    threading.Thread(
        target=lambda: asyncio.run(_do_sync(conn.shop_domain, conn.access_token, x_user_id)),
        daemon=True,
    ).start()

    return {"status": "sync_started"}


async def _do_sync(shop_domain: str, access_token: str, user_id: str):
    """Fetch data from Shopify and ingest into Qdrant."""
    import httpx
    from data.ingestion import ingest_file
    import pandas as pd
    import io

    headers = {"X-Shopify-Access-Token": access_token}
    products_count = 0
    orders_count = 0

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch products
            resp = await client.get(
                f"https://{shop_domain}/admin/api/2024-01/products.json?limit=250",
                headers=headers,
            )
            if resp.status_code == 200:
                products = resp.json().get("products", [])
                products_count = len(products)

                rows = [
                    {
                        "name": p.get("title", ""),
                        "category": p.get("product_type", "general"),
                        "price": p.get("variants", [{}])[0].get("price", 0),
                        "sku": p.get("variants", [{}])[0].get("sku", ""),
                        "inventory": p.get("variants", [{}])[0].get("inventory_quantity", 0),
                        "rating": 4.0,
                        "sales_volume": 0,
                    }
                    for p in products
                ]
                if rows:
                    df = pd.DataFrame(rows)
                    buf = io.BytesIO()
                    df.to_csv(buf, index=False)
                    ingest_file(buf.getvalue(), "shopify_products.csv", "catalog", user_id)

            # Fetch orders (for sales data)
            resp = await client.get(
                f"https://{shop_domain}/admin/api/2024-01/orders.json?limit=250&status=any",
                headers=headers,
            )
            if resp.status_code == 200:
                orders_count = len(resp.json().get("orders", []))

    except Exception as e:
        logger.error(f"Shopify sync error: {e}")

    # Update DB sync record
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == user_id)
        )
        conn = result.scalar_one_or_none()
        if conn:
            conn.products_synced = products_count
            conn.orders_synced = orders_count
            conn.last_sync = datetime.now(timezone.utc)
            await db.commit()

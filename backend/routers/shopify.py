"""
Shopify router: OAuth flow, data sync, and connection status.
"""

import logging
from urllib.parse import urlencode
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from db.models import ShopifyConnection
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shopify", tags=["shopify"])
SHOPIFY_API_VERSION = "2025-10"


@router.get("/status")
async def shopify_status(x_user_id: str = Header(default="default-user")):
    """Returns Shopify connection status for the user."""
    try:
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
    except Exception:
        logger.exception("Failed to read Shopify status for user_id=%s", x_user_id)
        return {"connected": False}


@router.get("/auth")
async def shopify_auth(shop: str, user_id: str | None = None):
    """Redirect user to Shopify OAuth URL."""
    import os
    api_key = os.getenv("SHOPIFY_API_KEY", "")
    redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI", "http://127.0.0.1:8000/api/shopify/callback")
    scopes = "read_products,read_orders,read_customers"

    if not api_key:
        raise HTTPException(status_code=503, detail="Shopify app not configured.")

    params = {
        "client_id": api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
    }
    if user_id:
        params["state"] = user_id
    auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def shopify_callback(
    shop: str,
    code: str,
    state: str | None = None,
    x_user_id: str | None = Header(default=None),
):
    """Exchange OAuth code for access_token and trigger initial sync."""
    import os
    import httpx

    api_key = os.getenv("SHOPIFY_API_KEY", "")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "")

    if not api_key:
        raise HTTPException(status_code=503, detail="Shopify app not configured.")

    resolved_user_id = x_user_id or state or "default-user"

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
            select(ShopifyConnection).where(ShopifyConnection.user_id == resolved_user_id)
        )
        conn = existing.scalar_one_or_none()
        if not conn:
            conn = ShopifyConnection(user_id=resolved_user_id)
            db.add(conn)
        conn.shop_domain = shop
        conn.access_token = access_token
        await db.commit()

    # Trigger async sync
    import asyncio, threading
    threading.Thread(
        target=lambda: asyncio.run(_do_sync(shop, access_token, resolved_user_id)),
        daemon=True,
    ).start()

    # Instead of redirecting the entire page, return a script to close the popup and notify the parent
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="""
        <html>
            <body>
                <script>
                    window.opener.postMessage({ type: 'shopify-auth-success' }, '*');
                    window.close();
                </script>
                <p>Authentication successful. You can close this window.</p>
            </body>
        </html>
    """)


@router.post("/sync")
async def trigger_sync(x_user_id: str = Header(default="default-user")):
    """Manually trigger a Shopify re-sync and wait until completion."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == x_user_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="No Shopify connection found.")

        shop_domain = conn.shop_domain
        access_token = conn.access_token

    sync_result = await _do_sync(shop_domain, access_token, x_user_id)
    forbidden_scopes = sync_result.get("forbidden_scopes", [])
    if forbidden_scopes:
        scopes_text = ", ".join(forbidden_scopes)
        raise HTTPException(
            status_code=403,
            detail=f"Missing Shopify merchant approval for scopes: {scopes_text}. Reconnect Shopify and approve requested permissions.",
        )
    return await shopify_status(x_user_id=x_user_id)


@router.delete("/disconnect")
async def disconnect_shopify(x_user_id: str = Header(default="default-user")):
    """Disconnect Shopify integration for the user."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == x_user_id)
        )
        conn = result.scalar_one_or_none()
        if conn:
            await db.delete(conn)
            await db.commit()

    return {"status": "disconnected"}


async def _do_sync(shop_domain: str, access_token: str, user_id: str):
    """Fetch data from Shopify and ingest into Qdrant."""
    import httpx
    from data.ingestion import ingest_file
    import pandas as pd
    import io

    headers = {"X-Shopify-Access-Token": access_token}
    products_count = 0
    orders_count = 0
    customers_count = 0
    forbidden_scopes: set[str] = set()

    def capture_scope_error(response_text: str):
        for scope in ("read_products", "read_orders", "read_customers"):
            if scope in response_text:
                forbidden_scopes.add(scope)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch products
            resp = await client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/products.json?limit=250",
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
            else:
                logger.warning("Shopify products fetch failed: status=%s body=%s", resp.status_code, resp.text[:500])
                if resp.status_code == 403:
                    capture_scope_error(resp.text)

            # Fetch product count
            resp = await client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/products/count.json",
                headers=headers,
            )
            if resp.status_code == 200:
                products_count = resp.json().get("count", products_count)
            else:
                logger.warning("Shopify products count failed: status=%s body=%s", resp.status_code, resp.text[:500])
                if resp.status_code == 403:
                    capture_scope_error(resp.text)

            # Fetch orders (for sales data)
            resp = await client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/orders/count.json?status=any",
                headers=headers,
            )
            if resp.status_code == 200:
                orders_count = resp.json().get("count", 0)
            else:
                logger.warning("Shopify orders count failed: status=%s body=%s", resp.status_code, resp.text[:500])
                if resp.status_code == 403:
                    capture_scope_error(resp.text)
                fallback = await client.get(
                    f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/orders.json?limit=250&status=any",
                    headers=headers,
                )
                if fallback.status_code == 200:
                    orders_count = len(fallback.json().get("orders", []))
                else:
                    logger.warning(
                        "Shopify orders fallback failed: status=%s body=%s",
                        fallback.status_code,
                        fallback.text[:500],
                    )
                    if fallback.status_code == 403:
                        capture_scope_error(fallback.text)

            # Shopify doesn't expose native "reviews" in core API; use customers as third metric.
            resp = await client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/customers/count.json",
                headers=headers,
            )
            if resp.status_code == 200:
                customers_count = resp.json().get("count", 0)
            else:
                logger.warning("Shopify customers count failed: status=%s body=%s", resp.status_code, resp.text[:500])
                if resp.status_code == 403:
                    capture_scope_error(resp.text)
                fallback = await client.get(
                    f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/customers.json?limit=250",
                    headers=headers,
                )
                if fallback.status_code == 200:
                    customers_count = len(fallback.json().get("customers", []))
                else:
                    logger.warning(
                        "Shopify customers fallback failed: status=%s body=%s",
                        fallback.status_code,
                        fallback.text[:500],
                    )
                    if fallback.status_code == 403:
                        capture_scope_error(fallback.text)

    except Exception as e:
        logger.error(f"Shopify sync error: {e}")

    # Update DB sync record
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShopifyConnection).where(ShopifyConnection.user_id == user_id)
        )
        conn = result.scalar_one_or_none()
        if conn:
            if not forbidden_scopes:
                conn.products_synced = products_count
                conn.orders_synced = orders_count
                conn.reviews_synced = customers_count
                conn.last_sync = datetime.now(timezone.utc)
            await db.commit()

    return {
        "products_count": products_count,
        "orders_count": orders_count,
        "customers_count": customers_count,
        "forbidden_scopes": sorted(forbidden_scopes),
    }

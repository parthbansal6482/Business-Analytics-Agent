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


def _get_next_page_url(link_header: str) -> str | None:
    if not link_header:
        return None
    for link in link_header.split(","):
        if 'rel="next"' in link:
            return link[link.find("<") + 1:link.find(">")]
    return None


def _safe_date(value: str) -> str:
    if not value:
        return ""
    return value[:10]


async def _fetch_judgeme_reviews(http_client, shop_domain: str) -> list[dict]:
    """Fetch reviews from Judge.me public API."""
    url = "https://judge.me/api/v1/reviews"
    page = 1
    reviews: list[dict] = []
    while True:
        resp = await http_client.get(
            url,
            params={"shop_domain": shop_domain, "per_page": 100, "page": page},
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        batch = data.get("reviews", [])
        if not batch:
            break
        reviews.extend(batch)
        page += 1
    return reviews


async def _fetch_metafield_reviews(http_client, shop_domain: str, headers: dict, products: list[dict]) -> list[dict]:
    """Fetch review-like rows from product metafields namespaces (reviews/spr)."""
    rows: list[dict] = []
    for p in products[:200]:
        product_id = p.get("id")
        if not product_id:
            continue
        sku = p.get("variants", [{}])[0].get("sku") or p.get("handle") or "unknown"
        resp = await http_client.get(
            f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/products/{product_id}/metafields.json",
            headers=headers,
        )
        if resp.status_code != 200:
            continue
        metafields = resp.json().get("metafields", [])
        for mf in metafields:
            namespace = (mf.get("namespace") or "").lower()
            if namespace not in {"reviews", "spr"}:
                continue
            value = str(mf.get("value", "") or "").strip()
            if not value:
                continue
            rating = 3
            key = (mf.get("key") or "").lower()
            if key in {"rating", "stars"}:
                try:
                    rating = float(value)
                except Exception:
                    rating = 3
            rows.append({
                "sku": sku,
                "rating": rating,
                "review_text": value,
                "date": "",
                "verified_purchase": False,
            })
    return rows


def _build_synthetic_reviews_from_orders(orders: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for order in orders:
        # Synthetic review rows from real purchases (fallback only).
        if order.get("fulfillment_status") not in {"fulfilled", "partial"}:
            continue
        order_date = _safe_date(order.get("created_at", ""))
        for line_item in order.get("line_items", []) or []:
            sku = line_item.get("sku") or str(line_item.get("product_id") or "unknown")
            qty = line_item.get("quantity", 1)
            name = line_item.get("name") or line_item.get("title") or "product"
            rows.append({
                "sku": sku,
                "rating": None,
                "review_text": f"Customer purchased {name} x{qty}",
                "date": order_date,
                "verified_purchase": True,
                "is_synthetic": True,
            })
    return rows


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
    reviews_count = 0
    forbidden_scopes: set[str] = set()

    def capture_scope_error(response_text: str):
        for scope in ("read_products", "read_orders", "read_customers"):
            if scope in response_text:
                forbidden_scopes.add(scope)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Fetch ALL products
            url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/products.json?limit=250"
            all_products = []
            while url:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    products = resp.json().get("products", [])
                    all_products.extend(products)
                    url = _get_next_page_url(resp.headers.get("Link", ""))
                else:
                    logger.warning("Shopify products fetch failed: status=%s body=%s", resp.status_code, resp.text[:500])
                    if resp.status_code == 403:
                        capture_scope_error(resp.text)
                    break
            
            products_count = len(all_products)
            if all_products:
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
                    for p in all_products
                ]
                df = pd.DataFrame(rows)
                buf = io.BytesIO()
                df.to_csv(buf, index=False)
                ingest_file(buf.getvalue(), "shopify_products.csv", "catalog", user_id)

            # 2. Fetch ALL orders
            url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/orders.json?limit=250&status=any"
            all_orders = []
            while url:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    orders = resp.json().get("orders", [])
                    all_orders.extend(orders)
                    url = _get_next_page_url(resp.headers.get("Link", ""))
                else:
                    logger.warning("Shopify orders fetch failed: status=%s body=%s", resp.status_code, resp.text[:500])
                    if resp.status_code == 403:
                        capture_scope_error(resp.text)
                    break
            
            orders_count = len(all_orders)
            if all_orders:
                rows = [
                    {
                        "order_id": str(o.get("id", "")),
                        "date": o.get("created_at", ""),
                        "status": o.get("financial_status", ""),
                        "total_price": o.get("total_price", 0),
                        "line_items": str([item.get("title", "") for item in o.get("line_items", [])]),
                        "customer_id": str(o.get("customer", {}).get("id", "") if isinstance(o.get("customer"), dict) else ""),
                    }
                    for o in all_orders
                ]
                df = pd.DataFrame(rows)
                buf = io.BytesIO()
                df.to_csv(buf, index=False)
                ingest_file(buf.getvalue(), "shopify_orders.csv", "orders", user_id)

            # 3. Fetch ALL customers
            url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/customers.json?limit=250"
            all_customers = []
            while url:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    customers = resp.json().get("customers", [])
                    all_customers.extend(customers)
                    url = _get_next_page_url(resp.headers.get("Link", ""))
                else:
                    logger.warning("Shopify customers fetch failed: status=%s body=%s", resp.status_code, resp.text[:500])
                    if resp.status_code == 403:
                        capture_scope_error(resp.text)
                    break

            customers_count = len(all_customers)
            if all_customers:
                rows = [
                    {
                        "customer_id": str(c.get("id", "")),
                        "email": c.get("email", ""),
                        "total_spent": c.get("total_spent", 0),
                        "orders_count": c.get("orders_count", 0),
                        "state": c.get("state", ""),
                    }
                    for c in all_customers
                ]
                df = pd.DataFrame(rows)
                buf = io.BytesIO()
                df.to_csv(buf, index=False)
                ingest_file(buf.getvalue(), "shopify_customers.csv", "customers", user_id)

            # 4. Fetch reviews: Judge.me -> Shopify metafields -> synthetic from orders
            review_rows: list[dict] = []

            judgeme_reviews = await _fetch_judgeme_reviews(client, shop_domain)
            if judgeme_reviews:
                review_rows = [
                    {
                        "sku": r.get("product_handle", "unknown"),
                        "rating": r.get("rating", 3),
                        "review_text": r.get("body", "") or "",
                        "date": _safe_date(r.get("created_at", "")),
                        "verified_purchase": bool(r.get("verified", False)),
                    }
                    for r in judgeme_reviews
                    if (r.get("body", "") or "").strip()
                ]

            if not review_rows:
                review_rows = await _fetch_metafield_reviews(client, shop_domain, headers, all_products)

            if not review_rows:
                review_rows = _build_synthetic_reviews_from_orders(all_orders)

            if review_rows:
                df = pd.DataFrame(review_rows)
                buf = io.BytesIO()
                df.to_csv(buf, index=False)
                ingest_file(buf.getvalue(), "shopify_reviews.csv", "reviews", user_id)
                reviews_count = len(review_rows)
            else:
                reviews_count = 0

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
                conn.reviews_synced = reviews_count
                conn.last_sync = datetime.now(timezone.utc)
            await db.commit()

    return {
        "products_count": products_count,
        "orders_count": orders_count,
        "customers_count": customers_count,
        "reviews_count": reviews_count,
        "forbidden_scopes": sorted(forbidden_scopes),
    }

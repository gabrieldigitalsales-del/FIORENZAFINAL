from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

PROJECT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_DIR / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "fiorenza.db"

SETTINGS_DEFAULTS: dict[str, str] = {
    "restaurant_name": "Fiorenza - Pizzaria e Restaurante",
    "tagline": "Peça pizzas, massas e pratos completos com uma experiência moderna no estilo delivery app.",
    "address": "Av Getulio Vargas, 411",
    "phone": "31 3771 8931",
    "whatsapp": "31 3771 8931",
    "city": "Sua cidade",
    "opening_hours": "Todos os dias, 18h às 23h30",
    "delivery_time": "35-55 min",
    "pickup_time": "20-30 min",
    "minimum_order": "25",
    "free_delivery_from": "120",
    "banner_title": "Seu jantar favorito, agora com carrinho e checkout online",
    "banner_subtitle": "Monte seu pedido, escolha retirada ou entrega e finalize em segundos.",
    "hero_badge": "Entrega rápida",
    "primary_color": "#ea1d2c",
    "secondary_color": "#ff7a00",
    "background_color": "#fff7f4",
    "surface_color": "#ffffff",
    "text_color": "#232323",
    "muted_text_color": "#6b7280",
    "pix_key": "31 3771 8931",
    "instagram": "@fiorenza",
    "delivery_enabled": "true",
    "pickup_enabled": "true",
    "service_fee": "0",
    "footer_note": "Sabores artesanais, atendimento rápido e painel administrativo para você controlar tudo.",
}

BOOLEAN_SETTINGS = {"delivery_enabled", "pickup_enabled"}
FLOAT_SETTINGS = {"minimum_order", "free_delivery_from", "service_fee"}
ADMIN_DEFAULT_USERNAME = "admin"
ADMIN_DEFAULT_PASSWORD = "fiorenza123"
ORDER_STATUSES = ["novo", "confirmado", "preparo", "saiu para entrega", "concluído", "cancelado"]

app = FastAPI(title="Fiorenza - Pizzaria e Restaurante", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET", "troque-esta-chave-em-producao"),
    same_site="lax",
    https_only=False,
    session_cookie="fiorenza_session",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class DatabaseError(Exception):
    """Custom exception for DB failures."""


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in normalized)
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-") or secrets.token_hex(4)


def hash_password(password: str, salt: str | None = None, iterations: int = 210_000) -> str:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"{iterations}${salt}${hashed.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        iterations_text, salt, expected_hash = encoded.split("$", 2)
        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        )
    except Exception:
        return False
    return hmac.compare_digest(calculated.hex(), expected_hash)


def db_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT 'Administrador',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price REAL NOT NULL,
    image_url TEXT DEFAULT '',
    featured INTEGER DEFAULT 0,
    available INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    prep_time INTEGER DEFAULT 30,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS neighborhoods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    fee REAL DEFAULT 0,
    eta_min INTEGER DEFAULT 35,
    active INTEGER DEFAULT 1,
    minimum_order REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    delivery_type TEXT NOT NULL,
    neighborhood_id INTEGER,
    address_line TEXT DEFAULT '',
    address_number TEXT DEFAULT '',
    address_complement TEXT DEFAULT '',
    payment_method TEXT NOT NULL,
    change_for REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    items_json TEXT NOT NULL,
    subtotal REAL NOT NULL,
    delivery_fee REAL NOT NULL,
    service_fee REAL NOT NULL,
    total REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'novo',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods (id) ON DELETE SET NULL
);
"""


SAMPLE_CATEGORIES = [
    ("Pizzas Tradicionais", "Sabores clássicos com massa artesanal.", 1, 1),
    ("Pizzas Especiais", "Combinações premium para destacar o cardápio.", 2, 1),
    ("Massas", "Opções cremosas e gratinadas.", 3, 1),
    ("Pratos Executivos", "Refeições completas para almoço e jantar.", 4, 1),
    ("Bebidas", "Refrigerantes, sucos e água.", 5, 1),
]

SAMPLE_ITEMS = [
    ("Pizzas Tradicionais", "Margherita", "Molho artesanal, muçarela, tomate e manjericão fresco.", 42.90, "", 1, 1, 1, 35),
    ("Pizzas Tradicionais", "Calabresa Especial", "Muçarela, calabresa fatiada, cebola roxa e orégano.", 46.90, "", 1, 1, 2, 35),
    ("Pizzas Tradicionais", "Quatro Queijos", "Muçarela, provolone, parmesão e catupiry.", 52.90, "", 0, 1, 3, 35),
    ("Pizzas Especiais", "Fiorenza Premium", "Molho italiano, muçarela, presunto parma, rúcula e parmesão.", 62.90, "", 1, 1, 1, 40),
    ("Pizzas Especiais", "Frango Cremoso", "Frango temperado, catupiry, milho verde e azeitonas.", 55.90, "", 0, 1, 2, 40),
    ("Massas", "Lasanha à Bolonhesa", "Camadas de massa fresca, molho bolonhesa e queijo gratinado.", 34.90, "", 1, 1, 1, 25),
    ("Massas", "Fettuccine Alfredo", "Massa artesanal com molho cremoso e toque de parmesão.", 36.90, "", 0, 1, 2, 20),
    ("Pratos Executivos", "Filé de Frango Grelhado", "Arroz, feijão, fritas e salada da casa.", 31.90, "", 1, 1, 1, 20),
    ("Pratos Executivos", "Parmegiana Fiorenza", "Bife empanado, queijo gratinado, arroz e purê.", 39.90, "", 1, 1, 2, 25),
    ("Bebidas", "Refrigerante Lata", "Coca-Cola, Guaraná ou Sprite 350ml.", 6.50, "", 0, 1, 1, 5),
    ("Bebidas", "Suco Natural", "Laranja, limão ou maracujá 400ml.", 9.90, "", 0, 1, 2, 5),
    ("Bebidas", "Água Sem Gás", "Garrafa 500ml.", 4.50, "", 0, 1, 3, 5),
]

SAMPLE_NEIGHBORHOODS = [
    ("Centro", 6.00, 30, 0),
    ("Boa Vista", 8.50, 40, 0),
    ("Jardim Europa", 9.50, 45, 0),
    ("Industrial", 11.00, 50, 0),
]


def init_db() -> None:
    conn = db_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        for key, value in SETTINGS_DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        admin_exists = conn.execute("SELECT id FROM admin_users LIMIT 1").fetchone()
        if not admin_exists:
            timestamp = now_str()
            conn.execute(
                """
                INSERT INTO admin_users (username, password_hash, full_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ADMIN_DEFAULT_USERNAME,
                    hash_password(ADMIN_DEFAULT_PASSWORD),
                    "Administrador Fiorenza",
                    timestamp,
                    timestamp,
                ),
            )

        category_exists = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()
        if not category_exists:
            timestamp = now_str()
            for name, description, sort_order, active in SAMPLE_CATEGORIES:
                conn.execute(
                    """
                    INSERT INTO categories (name, slug, description, sort_order, active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, slugify(name), description, sort_order, active, timestamp, timestamp),
                )
            category_rows = conn.execute("SELECT id, name FROM categories").fetchall()
            category_map = {row["name"]: row["id"] for row in category_rows}
            for (
                category_name,
                name,
                description,
                price,
                image_url,
                featured,
                available,
                sort_order,
                prep_time,
            ) in SAMPLE_ITEMS:
                conn.execute(
                    """
                    INSERT INTO items (
                        category_id, name, description, price, image_url, featured,
                        available, sort_order, prep_time, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        category_map[category_name],
                        name,
                        description,
                        price,
                        image_url,
                        featured,
                        available,
                        sort_order,
                        prep_time,
                        timestamp,
                        timestamp,
                    ),
                )
            for name, fee, eta_min, minimum_order in SAMPLE_NEIGHBORHOODS:
                conn.execute(
                    """
                    INSERT INTO neighborhoods (name, fee, eta_min, active, minimum_order, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?, ?)
                    """,
                    (name, fee, eta_min, minimum_order, timestamp, timestamp),
                )
        conn.commit()
    finally:
        conn.close()


init_db()


def setting_value(key: str, raw: str) -> Any:
    if key in BOOLEAN_SETTINGS:
        return str(raw).strip().lower() in {"1", "true", "yes", "sim", "on"}
    if key in FLOAT_SETTINGS:
        try:
            return round(float(raw), 2)
        except (TypeError, ValueError):
            return 0.0
    return raw


def fetch_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    data = {row["key"]: setting_value(row["key"], row["value"]) for row in rows}
    for key, default in SETTINGS_DEFAULTS.items():
        data.setdefault(key, setting_value(key, default))
    return data


def serialize_category(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "description": row["description"],
        "sort_order": row["sort_order"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "name": row["name"],
        "description": row["description"],
        "price": round(float(row["price"]), 2),
        "image_url": row["image_url"],
        "featured": bool(row["featured"]),
        "available": bool(row["available"]),
        "sort_order": row["sort_order"],
        "prep_time": row["prep_time"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_neighborhood(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "fee": round(float(row["fee"]), 2),
        "eta_min": row["eta_min"],
        "active": bool(row["active"]),
        "minimum_order": round(float(row["minimum_order"]), 2),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_order(row: sqlite3.Row) -> dict[str, Any]:
    items = []
    try:
        items = json.loads(row["items_json"])
    except json.JSONDecodeError:
        items = []
    return {
        "id": row["id"],
        "order_code": row["order_code"],
        "customer_name": row["customer_name"],
        "phone": row["phone"],
        "delivery_type": row["delivery_type"],
        "neighborhood_id": row["neighborhood_id"],
        "neighborhood_name": row["neighborhood_name"],
        "address_line": row["address_line"],
        "address_number": row["address_number"],
        "address_complement": row["address_complement"],
        "payment_method": row["payment_method"],
        "change_for": round(float(row["change_for"]), 2),
        "notes": row["notes"],
        "items": items,
        "subtotal": round(float(row["subtotal"]), 2),
        "delivery_fee": round(float(row["delivery_fee"]), 2),
        "service_fee": round(float(row["service_fee"]), 2),
        "total": round(float(row["total"]), 2),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_public_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    settings = fetch_settings(conn)
    categories = [
        serialize_category(row)
        for row in conn.execute(
            "SELECT * FROM categories WHERE active = 1 ORDER BY sort_order, name"
        ).fetchall()
    ]
    items = [
        serialize_item(row)
        for row in conn.execute(
            """
            SELECT items.*, categories.name AS category_name
            FROM items
            JOIN categories ON categories.id = items.category_id
            WHERE items.available = 1 AND categories.active = 1
            ORDER BY categories.sort_order, items.sort_order, items.name
            """
        ).fetchall()
    ]
    neighborhoods = [
        serialize_neighborhood(row)
        for row in conn.execute(
            "SELECT * FROM neighborhoods WHERE active = 1 ORDER BY name"
        ).fetchall()
    ]
    return {
        "settings": settings,
        "categories": categories,
        "items": items,
        "neighborhoods": neighborhoods,
        "payment_methods": ["Pix", "Cartão", "Dinheiro"],
    }


def require_admin(request: Request) -> dict[str, Any]:
    admin = request.session.get("admin")
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar.")
    return admin


def parse_json(request: Request) -> Any:
    raise RuntimeError("parse_json should not be called directly without await")


async def request_json(request: Request) -> Any:
    try:
        return await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON inválido.") from exc


def admin_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    settings = fetch_settings(conn)
    categories = [
        serialize_category(row)
        for row in conn.execute("SELECT * FROM categories ORDER BY sort_order, name").fetchall()
    ]
    items = [
        serialize_item(row)
        for row in conn.execute(
            """
            SELECT items.*, categories.name AS category_name
            FROM items
            JOIN categories ON categories.id = items.category_id
            ORDER BY categories.sort_order, items.sort_order, items.name
            """
        ).fetchall()
    ]
    neighborhoods = [
        serialize_neighborhood(row)
        for row in conn.execute("SELECT * FROM neighborhoods ORDER BY name").fetchall()
    ]
    orders = [
        serialize_order(row)
        for row in conn.execute(
            """
            SELECT orders.*, neighborhoods.name AS neighborhood_name
            FROM orders
            LEFT JOIN neighborhoods ON neighborhoods.id = orders.neighborhood_id
            ORDER BY orders.id DESC
            LIMIT 100
            """
        ).fetchall()
    ]
    summary = {
        "items_count": len(items),
        "categories_count": len(categories),
        "neighborhoods_count": len(neighborhoods),
        "orders_count": len(orders),
        "pending_orders": sum(1 for order in orders if order["status"] in {"novo", "confirmado", "preparo"}),
        "revenue_total": round(sum(order["total"] for order in orders if order["status"] != "cancelado"), 2),
    }
    return {
        "settings": settings,
        "categories": categories,
        "items": items,
        "neighborhoods": neighborhoods,
        "orders": orders,
        "summary": summary,
        "statuses": ORDER_STATUSES,
    }


def sanitize_phone_number(phone: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith("55"):
        return digits
    return f"55{digits}"


def build_whatsapp_message(order: dict[str, Any], settings: dict[str, Any]) -> str:
    lines = [
        f"*Novo pedido pelo site* {order['order_code']}",
        f"Cliente: {order['customer_name']}",
        f"Telefone: {order['phone']}",
        f"Tipo: {'Entrega' if order['delivery_type'] == 'delivery' else 'Retirada'}",
    ]
    if order["delivery_type"] == "delivery":
        lines.append(
            f"Endereço: {order['address_line']}, {order['address_number']} - {order.get('neighborhood_name') or ''}"
        )
        if order.get("address_complement"):
            lines.append(f"Complemento: {order['address_complement']}")
    lines.append("Itens:")
    for item in order["items"]:
        lines.append(f"- {item['quantity']}x {item['name']} | R$ {item['line_total']:.2f}")
    lines.extend(
        [
            f"Subtotal: R$ {order['subtotal']:.2f}",
            f"Taxa de entrega: R$ {order['delivery_fee']:.2f}",
            f"Taxa de serviço: R$ {order['service_fee']:.2f}",
            f"Total: R$ {order['total']:.2f}",
            f"Pagamento: {order['payment_method']}",
        ]
    )
    if order.get("change_for") and order["payment_method"].lower() == "dinheiro":
        lines.append(f"Troco para: R$ {order['change_for']:.2f}")
    if order.get("notes"):
        lines.append(f"Observações: {order['notes']}")
    if settings.get("pix_key") and order["payment_method"].lower() == "pix":
        lines.append(f"Pix para pagamento: {settings['pix_key']}")
    return "\n".join(lines)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "restaurant_name": SETTINGS_DEFAULTS["restaurant_name"],
        },
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "restaurant_name": SETTINGS_DEFAULTS["restaurant_name"],
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/public/bootstrap")
async def public_bootstrap() -> dict[str, Any]:
    conn = db_connection()
    try:
        return get_public_payload(conn)
    finally:
        conn.close()


@app.post("/api/public/orders")
async def create_order(request: Request) -> dict[str, Any]:
    payload = await request_json(request)
    cart = payload.get("cart") or []
    if not cart:
        raise HTTPException(status_code=400, detail="O carrinho está vazio.")

    customer_name = str(payload.get("customer_name", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    delivery_type = str(payload.get("delivery_type", "delivery")).strip().lower()
    neighborhood_id = payload.get("neighborhood_id")
    address_line = str(payload.get("address_line", "")).strip()
    address_number = str(payload.get("address_number", "")).strip()
    address_complement = str(payload.get("address_complement", "")).strip()
    payment_method = str(payload.get("payment_method", "")).strip() or "Pix"
    notes = str(payload.get("notes", "")).strip()

    try:
        change_for = round(float(payload.get("change_for") or 0), 2)
    except (TypeError, ValueError):
        change_for = 0.0

    if not customer_name:
        raise HTTPException(status_code=400, detail="Informe o nome do cliente.")
    if not phone:
        raise HTTPException(status_code=400, detail="Informe o telefone para contato.")
    if delivery_type not in {"delivery", "pickup"}:
        raise HTTPException(status_code=400, detail="Tipo de entrega inválido.")

    conn = db_connection()
    try:
        settings = fetch_settings(conn)
        if delivery_type == "delivery" and not settings.get("delivery_enabled", True):
            raise HTTPException(status_code=400, detail="Entrega desativada no momento.")
        if delivery_type == "pickup" and not settings.get("pickup_enabled", True):
            raise HTTPException(status_code=400, detail="Retirada desativada no momento.")

        item_ids = [int(item.get("item_id")) for item in cart if item.get("item_id")]
        if not item_ids:
            raise HTTPException(status_code=400, detail="Itens inválidos no carrinho.")
        placeholders = ",".join("?" for _ in item_ids)
        db_items = conn.execute(
            f"""
            SELECT items.*, categories.name AS category_name
            FROM items
            JOIN categories ON categories.id = items.category_id
            WHERE items.id IN ({placeholders})
              AND items.available = 1
              AND categories.active = 1
            """,
            item_ids,
        ).fetchall()
        db_items_map = {row["id"]: serialize_item(row) for row in db_items}

        line_items: list[dict[str, Any]] = []
        subtotal = 0.0
        for raw_item in cart:
            item_id = int(raw_item.get("item_id"))
            quantity = int(raw_item.get("quantity") or 1)
            if quantity < 1:
                continue
            item = db_items_map.get(item_id)
            if not item:
                raise HTTPException(status_code=400, detail="Um item do carrinho não está mais disponível.")
            line_total = round(item["price"] * quantity, 2)
            subtotal += line_total
            line_items.append(
                {
                    "item_id": item_id,
                    "name": item["name"],
                    "quantity": quantity,
                    "unit_price": item["price"],
                    "line_total": line_total,
                    "notes": str(raw_item.get("notes", "")).strip(),
                }
            )

        subtotal = round(subtotal, 2)
        global_minimum = float(settings.get("minimum_order") or 0)
        if subtotal < global_minimum:
            raise HTTPException(
                status_code=400,
                detail=f"Pedido mínimo para a loja é R$ {global_minimum:.2f}.",
            )

        delivery_fee = 0.0
        neighborhood_name = None
        if delivery_type == "delivery":
            if not neighborhood_id:
                raise HTTPException(status_code=400, detail="Selecione o bairro para entrega.")
            neighborhood = conn.execute(
                "SELECT * FROM neighborhoods WHERE id = ? AND active = 1",
                (int(neighborhood_id),),
            ).fetchone()
            if not neighborhood:
                raise HTTPException(status_code=400, detail="Bairro de entrega inválido.")
            if not address_line or not address_number:
                raise HTTPException(status_code=400, detail="Informe rua/avenida e número para entrega.")
            delivery_fee = round(float(neighborhood["fee"]), 2)
            neighborhood_name = neighborhood["name"]
            neighborhood_minimum = round(float(neighborhood["minimum_order"]), 2)
            if neighborhood_minimum and subtotal < neighborhood_minimum:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pedido mínimo para {neighborhood_name} é R$ {neighborhood_minimum:.2f}.",
                )
            free_delivery_from = round(float(settings.get("free_delivery_from") or 0), 2)
            if free_delivery_from and subtotal >= free_delivery_from:
                delivery_fee = 0.0

        service_fee = round(float(settings.get("service_fee") or 0), 2)
        total = round(subtotal + delivery_fee + service_fee, 2)
        timestamp = now_str()
        order_code = f"FIO-{datetime.now().strftime('%d%m')}-{secrets.token_hex(2).upper()}"

        conn.execute(
            """
            INSERT INTO orders (
                order_code, customer_name, phone, delivery_type, neighborhood_id,
                address_line, address_number, address_complement, payment_method,
                change_for, notes, items_json, subtotal, delivery_fee, service_fee,
                total, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'novo', ?, ?)
            """,
            (
                order_code,
                customer_name,
                phone,
                delivery_type,
                int(neighborhood_id) if neighborhood_id else None,
                address_line,
                address_number,
                address_complement,
                payment_method,
                change_for,
                notes,
                json.dumps(line_items, ensure_ascii=False),
                subtotal,
                delivery_fee,
                service_fee,
                total,
                timestamp,
                timestamp,
            ),
        )
        conn.commit()

        order = {
            "order_code": order_code,
            "customer_name": customer_name,
            "phone": phone,
            "delivery_type": delivery_type,
            "neighborhood_name": neighborhood_name,
            "address_line": address_line,
            "address_number": address_number,
            "address_complement": address_complement,
            "payment_method": payment_method,
            "change_for": change_for,
            "notes": notes,
            "items": line_items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "service_fee": service_fee,
            "total": total,
        }
        whatsapp_phone = sanitize_phone_number(str(settings.get("whatsapp") or settings.get("phone") or ""))
        whatsapp_message = build_whatsapp_message(order, settings)
        whatsapp_url = f"https://wa.me/{whatsapp_phone}?text={quote(whatsapp_message)}"

        return {
            "ok": True,
            "message": "Pedido recebido com sucesso.",
            "order": order,
            "whatsapp_url": whatsapp_url,
        }
    finally:
        conn.close()


@app.post("/api/admin/login")
async def admin_login(request: Request) -> dict[str, Any]:
    payload = await request_json(request)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    conn = db_connection()
    try:
        user = conn.execute(
            "SELECT * FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
        request.session["admin"] = {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
        }
        return {"ok": True, "admin": request.session["admin"]}
    finally:
        conn.close()


@app.post("/api/admin/logout")
async def admin_logout(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/admin/session")
async def admin_session(request: Request) -> dict[str, Any]:
    admin = request.session.get("admin")
    return {"authenticated": bool(admin), "admin": admin}


@app.get("/api/admin/bootstrap")
async def admin_bootstrap(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    conn = db_connection()
    try:
        payload = admin_payload(conn)
        payload["admin"] = admin
        return payload
    finally:
        conn.close()


@app.put("/api/admin/settings")
async def update_settings(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    allowed_keys = set(SETTINGS_DEFAULTS.keys())
    updates = {key: payload[key] for key in payload if key in allowed_keys}
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhuma configuração válida foi enviada.")

    conn = db_connection()
    try:
        for key, value in updates.items():
            if key in BOOLEAN_SETTINGS:
                value = "true" if bool(value) else "false"
            elif key in FLOAT_SETTINGS:
                try:
                    value = f"{float(value):.2f}"
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail=f"Valor inválido para {key}.") from exc
            else:
                value = str(value).strip()
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        conn.commit()
        return {"ok": True, "settings": fetch_settings(conn)}
    finally:
        conn.close()


@app.post("/api/admin/categories")
async def create_category(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    active = 1 if bool(payload.get("active", True)) else 0
    sort_order = int(payload.get("sort_order") or 0)
    if not name:
        raise HTTPException(status_code=400, detail="Informe o nome da categoria.")
    conn = db_connection()
    try:
        timestamp = now_str()
        cursor = conn.execute(
            """
            INSERT INTO categories (name, slug, description, sort_order, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, slugify(name), description, sort_order, active, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return {"ok": True, "category": serialize_category(row)}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Já existe uma categoria com esse nome.") from exc
    finally:
        conn.close()


@app.put("/api/admin/categories/{category_id}")
async def update_category(category_id: int, request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    active = 1 if bool(payload.get("active", True)) else 0
    sort_order = int(payload.get("sort_order") or 0)
    if not name:
        raise HTTPException(status_code=400, detail="Informe o nome da categoria.")
    conn = db_connection()
    try:
        existing = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        conn.execute(
            """
            UPDATE categories
            SET name = ?, slug = ?, description = ?, sort_order = ?, active = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, slugify(name), description, sort_order, active, now_str(), category_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return {"ok": True, "category": serialize_category(row)}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Já existe outra categoria com esse nome.") from exc
    finally:
        conn.close()


@app.delete("/api/admin/categories/{category_id}")
async def delete_category(category_id: int, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, bool]:
    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/admin/items")
async def create_item(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    category_id = int(payload.get("category_id") or 0)
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    image_url = str(payload.get("image_url", "")).strip()
    featured = 1 if bool(payload.get("featured", False)) else 0
    available = 1 if bool(payload.get("available", True)) else 0
    sort_order = int(payload.get("sort_order") or 0)
    prep_time = int(payload.get("prep_time") or 30)
    try:
        price = round(float(payload.get("price")), 2)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Preço inválido.") from exc
    if not category_id or not name:
        raise HTTPException(status_code=400, detail="Categoria e nome são obrigatórios.")

    conn = db_connection()
    try:
        category = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        timestamp = now_str()
        cursor = conn.execute(
            """
            INSERT INTO items (
                category_id, name, description, price, image_url, featured,
                available, sort_order, prep_time, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (category_id, name, description, price, image_url, featured, available, sort_order, prep_time, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT items.*, categories.name AS category_name
            FROM items JOIN categories ON categories.id = items.category_id
            WHERE items.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return {"ok": True, "item": serialize_item(row)}
    finally:
        conn.close()


@app.put("/api/admin/items/{item_id}")
async def update_item(item_id: int, request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    category_id = int(payload.get("category_id") or 0)
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    image_url = str(payload.get("image_url", "")).strip()
    featured = 1 if bool(payload.get("featured", False)) else 0
    available = 1 if bool(payload.get("available", True)) else 0
    sort_order = int(payload.get("sort_order") or 0)
    prep_time = int(payload.get("prep_time") or 30)
    try:
        price = round(float(payload.get("price")), 2)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Preço inválido.") from exc
    if not category_id or not name:
        raise HTTPException(status_code=400, detail="Categoria e nome são obrigatórios.")

    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        category = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        conn.execute(
            """
            UPDATE items
            SET category_id = ?, name = ?, description = ?, price = ?, image_url = ?,
                featured = ?, available = ?, sort_order = ?, prep_time = ?, updated_at = ?
            WHERE id = ?
            """,
            (category_id, name, description, price, image_url, featured, available, sort_order, prep_time, now_str(), item_id),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT items.*, categories.name AS category_name
            FROM items JOIN categories ON categories.id = items.category_id
            WHERE items.id = ?
            """,
            (item_id,),
        ).fetchone()
        return {"ok": True, "item": serialize_item(row)}
    finally:
        conn.close()


@app.delete("/api/admin/items/{item_id}")
async def delete_item(item_id: int, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, bool]:
    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/admin/neighborhoods")
async def create_neighborhood(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    name = str(payload.get("name", "")).strip()
    active = 1 if bool(payload.get("active", True)) else 0
    eta_min = int(payload.get("eta_min") or 35)
    try:
        fee = round(float(payload.get("fee") or 0), 2)
        minimum_order = round(float(payload.get("minimum_order") or 0), 2)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Valores inválidos para taxa ou pedido mínimo.") from exc
    if not name:
        raise HTTPException(status_code=400, detail="Informe o nome do bairro.")
    conn = db_connection()
    try:
        timestamp = now_str()
        cursor = conn.execute(
            """
            INSERT INTO neighborhoods (name, fee, eta_min, active, minimum_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, fee, eta_min, active, minimum_order, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM neighborhoods WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return {"ok": True, "neighborhood": serialize_neighborhood(row)}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Já existe um bairro com esse nome.") from exc
    finally:
        conn.close()


@app.put("/api/admin/neighborhoods/{neighborhood_id}")
async def update_neighborhood(neighborhood_id: int, request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    name = str(payload.get("name", "")).strip()
    active = 1 if bool(payload.get("active", True)) else 0
    eta_min = int(payload.get("eta_min") or 35)
    try:
        fee = round(float(payload.get("fee") or 0), 2)
        minimum_order = round(float(payload.get("minimum_order") or 0), 2)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Valores inválidos para taxa ou pedido mínimo.") from exc
    if not name:
        raise HTTPException(status_code=400, detail="Informe o nome do bairro.")
    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM neighborhoods WHERE id = ?", (neighborhood_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Bairro não encontrado.")
        conn.execute(
            """
            UPDATE neighborhoods
            SET name = ?, fee = ?, eta_min = ?, active = ?, minimum_order = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, fee, eta_min, active, minimum_order, now_str(), neighborhood_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM neighborhoods WHERE id = ?", (neighborhood_id,)).fetchone()
        return {"ok": True, "neighborhood": serialize_neighborhood(row)}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Já existe outro bairro com esse nome.") from exc
    finally:
        conn.close()


@app.delete("/api/admin/neighborhoods/{neighborhood_id}")
async def delete_neighborhood(neighborhood_id: int, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, bool]:
    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM neighborhoods WHERE id = ?", (neighborhood_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Bairro não encontrado.")
        conn.execute("DELETE FROM neighborhoods WHERE id = ?", (neighborhood_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/orders")
async def list_orders(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    conn = db_connection()
    try:
        orders = [
            serialize_order(row)
            for row in conn.execute(
                """
                SELECT orders.*, neighborhoods.name AS neighborhood_name
                FROM orders
                LEFT JOIN neighborhoods ON neighborhoods.id = orders.neighborhood_id
                ORDER BY orders.id DESC
                LIMIT 200
                """
            ).fetchall()
        ]
        return {"orders": orders, "statuses": ORDER_STATUSES}
    finally:
        conn.close()


@app.put("/api/admin/orders/{order_id}/status")
async def update_order_status(order_id: int, request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    status_value = str(payload.get("status", "")).strip().lower()
    if status_value not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Status inválido.")
    conn = db_connection()
    try:
        existing = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status_value, now_str(), order_id),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT orders.*, neighborhoods.name AS neighborhood_name
            FROM orders
            LEFT JOIN neighborhoods ON neighborhoods.id = orders.neighborhood_id
            WHERE orders.id = ?
            """,
            (order_id,),
        ).fetchone()
        return {"ok": True, "order": serialize_order(row)}
    finally:
        conn.close()


@app.put("/api/admin/credentials")
async def update_credentials(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    payload = await request_json(request)
    current_password = str(payload.get("current_password", ""))
    new_username = str(payload.get("new_username", "")).strip() or admin["username"]
    new_password = str(payload.get("new_password", ""))

    if len(new_username) < 3:
        raise HTTPException(status_code=400, detail="O usuário deve ter ao menos 3 caracteres.")
    if new_password and len(new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter ao menos 6 caracteres.")

    conn = db_connection()
    try:
        user = conn.execute("SELECT * FROM admin_users WHERE id = ?", (admin["id"],)).fetchone()
        if not user or not verify_password(current_password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Senha atual inválida.")
        password_hash = user["password_hash"] if not new_password else hash_password(new_password)
        conn.execute(
            "UPDATE admin_users SET username = ?, password_hash = ?, updated_at = ? WHERE id = ?",
            (new_username, password_hash, now_str(), admin["id"]),
        )
        conn.commit()
        request.session["admin"] = {
            **admin,
            "username": new_username,
        }
        return {"ok": True, "admin": request.session["admin"]}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Esse usuário já está em uso.") from exc
    finally:
        conn.close()


@app.get("/api/admin/backup")
async def backup_data(admin: dict[str, Any] = Depends(require_admin)) -> JSONResponse:
    conn = db_connection()
    try:
        payload = admin_payload(conn)
        filename = f"fiorenza-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        conn.close()
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
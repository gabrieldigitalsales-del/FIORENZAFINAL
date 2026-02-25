import json
import os
import uuid
import stripe
from functools import wraps

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort

from config import Config
from models import db, SiteConfig, User, Categoria, Produto, Pedido


ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config.get("UPLOAD_FOLDER", "static/uploads"), exist_ok=True)

    db.init_app(app)

    # Stripe init
    if app.config.get("STRIPE_SECRET_KEY"):
        stripe.api_key = app.config["STRIPE_SECRET_KEY"]

    # ---------- Helpers ----------
    def get_site_config():
        cfg = SiteConfig.query.first()
        if not cfg:
            cfg = SiteConfig(site_name="Fiorenza Pizzaria e Restaurante")
            db.session.add(cfg)
            db.session.commit()
        return cfg

    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        return User.query.get(uid)

    def is_admin():
        return session.get("is_admin") is True

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_admin():
                flash("Acesso restrito ao administrador.", "danger")
                return redirect(url_for("admin_login"))
            return fn(*args, **kwargs)
        return wrapper

    def cart_init():
        if "cart" not in session:
            session["cart"] = {}
            session.modified = True

    def cart_total_and_items():
        cart_init()
        cart = session.get("cart", {})
        items = []
        total = 0.0

        for pid_str, qtd in cart.items():
            try:
                pid = int(pid_str)
                qtd = int(qtd)
            except Exception:
                continue

            if qtd <= 0:
                continue

            p = Produto.query.get(pid)
            if not p or not p.ativo:
                continue

            subtotal = float(p.preco) * qtd
            total += subtotal

            items.append({
                "id": p.id,
                "nome": p.nome,
                "preco": float(p.preco),
                "qtd": qtd,
                "subtotal": round(subtotal, 2),
                "imagem_url": p.imagem_url or "",
                "categoria": p.categoria.nome if p.categoria else ""
            })

        return round(total, 2), items

    def normalize_phone(phone: str) -> str:
        digits = "".join([c for c in (phone or "") if c.isdigit()])
        return digits

    def save_uploaded_image(file_storage):
        if not file_storage or not file_storage.filename:
            return ""

        if not allowed_file(file_storage.filename):
            raise ValueError("Tipo de arquivo inválido. Envie PNG/JPG/JPEG/WEBP/GIF.")

        original = secure_filename(file_storage.filename)
        ext = original.rsplit(".", 1)[1].lower()

        unique_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = app.config["UPLOAD_FOLDER"]
        full_path = os.path.join(upload_dir, unique_name)

        file_storage.save(full_path)
        return f"/static/uploads/{unique_name}"

    # ---------- Context processor ----------
    @app.context_processor
    def inject_globals():
        cfg = get_site_config()
        return {
            "site_cfg": cfg,
            "logged_user": current_user(),
            "is_admin": is_admin(),
            "stripe_pk": app.config.get("STRIPE_PUBLISHABLE_KEY", "")
        }

    # ---------- CLI / init ----------
    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()
            cfg = get_site_config()

            if Categoria.query.count() == 0:
                cat1 = Categoria(nome="Pizzas", ordem=1, ativo=True)
                cat2 = Categoria(nome="Bebidas", ordem=2, ativo=True)
                db.session.add_all([cat1, cat2])
                db.session.commit()

                p1 = Produto(
                    nome="Margherita",
                    descricao="Queijo, tomate, orégano e manjericão.",
                    preco=49.90,
                    imagem_url="https://images.unsplash.com/photo-1601924638867-3ec0cfe6d3d5?auto=format&fit=crop&w=1200&q=60",
                    categoria_id=cat1.id,
                    ativo=True
                )
                db.session.add(p1)
                db.session.commit()

            if not cfg.logo_url:
                cfg.logo_url = "/static/images/logo.png"
                db.session.commit()

            print("✅ Banco inicializado com sucesso!")

    # ---------- Public routes ----------
    @app.route("/")
    def index():
        cfg = get_site_config()
        categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.ordem.asc(), Categoria.nome.asc()).all()
        destaques = Produto.query.filter_by(ativo=True).order_by(Produto.id.desc()).limit(6).all()
        total, items = cart_total_and_items()
        return render_template("index.html", cfg=cfg, categorias=categorias, destaques=destaques, cart_total=total, cart_items=items)

    @app.route("/menu")
    def menu():
        cfg = get_site_config()
        categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.ordem.asc(), Categoria.nome.asc()).all()
        produtos = Produto.query.filter_by(ativo=True).order_by(Produto.categoria_id.asc(), Produto.nome.asc()).all()
        total, items = cart_total_and_items()
        return render_template("menu.html", cfg=cfg, categorias=categorias, produtos=produtos, cart_total=total, cart_items=items)

    @app.route("/about")
    def about():
        cfg = get_site_config()
        total, items = cart_total_and_items()
        return render_template("about.html", cfg=cfg, cart_total=total, cart_items=items)

    # ---------- Auth ----------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        cfg = get_site_config()
        total, items = cart_total_and_items()

        if request.method == "POST":
            telefone = normalize_phone(request.form.get("telefone", ""))
            senha = (request.form.get("senha", "") or "").strip()

            u = User.query.filter_by(telefone=telefone).first()
            if not u or not check_password_hash(u.senha_hash, senha):
                flash("Telefone ou senha inválidos.", "danger")
                return render_template("login.html", cfg=cfg, cart_total=total, cart_items=items)

            session["user_id"] = u.id
            flash("✅ Login realizado!", "success")
            return redirect(url_for("menu"))

        return render_template("login.html", cfg=cfg, cart_total=total, cart_items=items)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        cfg = get_site_config()
        total, items = cart_total_and_items()

        if request.method == "POST":
            telefone = normalize_phone(request.form.get("telefone", ""))
            senha = (request.form.get("senha", "") or "").strip()

            if len(telefone) < 10:
                flash("Informe um telefone válido (com DDD).", "warning")
                return render_template("register.html", cfg=cfg, cart_total=total, cart_items=items)

            if not senha.isdigit() or len(senha) != 6:
                flash("A senha deve ter exatamente 6 dígitos (apenas números).", "warning")
                return render_template("register.html", cfg=cfg, cart_total=total, cart_items=items)

            if User.query.filter_by(telefone=telefone).first():
                flash("Esse telefone já está cadastrado. Faça login.", "info")
                return redirect(url_for("login"))

            u = User(telefone=telefone, senha_hash=generate_password_hash(senha))
            db.session.add(u)
            db.session.commit()

            session["user_id"] = u.id
            flash("✅ Cadastro concluído!", "success")
            return redirect(url_for("menu"))

        return render_template("register.html", cfg=cfg, cart_total=total, cart_items=items)

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("Você saiu da conta.", "info")
        return redirect(url_for("index"))

    # ---------- Cart API ----------
    @app.route("/api/cart", methods=["GET"])
    def api_cart():
        total, items = cart_total_and_items()
        return jsonify({"ok": True, "total": total, "items": items})

    @app.route("/api/cart/add", methods=["POST"])
    def api_cart_add():
        cart_init()
        data = request.get_json(silent=True) or {}
        pid = int(data.get("product_id", 0))
        qtd = int(data.get("qty", 1))

        p = Produto.query.get(pid)
        if not p or not p.ativo:
            return jsonify({"ok": False, "error": "Produto inválido"}), 400

        cart = session.get("cart", {})
        cart[str(pid)] = int(cart.get(str(pid), 0)) + max(qtd, 1)
        session["cart"] = cart
        session.modified = True

        total, items = cart_total_and_items()
        return jsonify({"ok": True, "total": total, "items": items})

    @app.route("/api/cart/update", methods=["POST"])
    def api_cart_update():
        cart_init()
        data = request.get_json(silent=True) or {}
        pid = int(data.get("product_id", 0))
        qtd = int(data.get("qty", 1))

        cart = session.get("cart", {})
        if qtd <= 0:
            cart.pop(str(pid), None)
        else:
            cart[str(pid)] = qtd

        session["cart"] = cart
        session.modified = True

        total, items = cart_total_and_items()
        return jsonify({"ok": True, "total": total, "items": items})

    @app.route("/api/cart/clear", methods=["POST"])
    def api_cart_clear():
        session["cart"] = {}
        session.modified = True
        return jsonify({"ok": True})

    # ---------- Checkout ----------
    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        cfg = get_site_config()
        total, items = cart_total_and_items()

        if total <= 0 or len(items) == 0:
            flash("Seu carrinho está vazio.", "warning")
            return redirect(url_for("menu"))

        if request.method == "GET":
            return render_template("checkout.html", cfg=cfg, cart_total=total, cart_items=items)

        nome = (request.form.get("nome", "") or "").strip()
        telefone = normalize_phone(request.form.get("telefone", ""))
        endereco = (request.form.get("endereco", "") or "").strip()
        referencia = (request.form.get("referencia", "") or "").strip()

        forma_pagamento = (request.form.get("forma_pagamento", "") or "").strip()
        troco_para = (request.form.get("troco_para", "") or "").strip()

        if len(nome) < 2 or len(telefone) < 10 or len(endereco) < 5:
            flash("Preencha nome, telefone e endereço corretamente.", "warning")
            return render_template("checkout.html", cfg=cfg, cart_total=total, cart_items=items)

        if forma_pagamento not in ["stripe", "credito", "debito", "pix", "dinheiro"]:
            flash("Selecione uma forma de pagamento válida.", "warning")
            return render_template("checkout.html", cfg=cfg, cart_total=total, cart_items=items)

        if forma_pagamento == "dinheiro" and troco_para and not troco_para.isdigit():
            flash("Troco: informe apenas números (ex: 100).", "warning")
            return render_template("checkout.html", cfg=cfg, cart_total=total, cart_items=items)

        uid = session.get("user_id")

        # ✅ status inicial:
        initial_status = "aguardando_pagamento" if forma_pagamento == "stripe" else "novo"

        pedido = Pedido(
            user_id=uid,
            nome=nome,
            telefone=telefone,
            endereco=endereco,
            referencia=referencia,
            forma_pagamento=forma_pagamento,
            troco_para=troco_para if forma_pagamento == "dinheiro" else "",
            total=total,
            itens_json=json.dumps(items, ensure_ascii=False),
            status=initial_status
        )
        db.session.add(pedido)
        db.session.commit()

        # Stripe checkout (✅ NÃO marca pago aqui!)
        if forma_pagamento == "stripe":
            if not app.config.get("STRIPE_SECRET_KEY"):
                flash("Stripe não configurado ainda. Escolha outra forma de pagamento.", "danger")
                pedido.status = "cancelado"
                db.session.commit()
                return redirect(url_for("checkout"))

            line_items = []
            for it in items:
                amount = int(round(float(it["preco"]) * 100))
                line_items.append({
                    "price_data": {
                        "currency": "brl",
                        "product_data": {"name": it["nome"]},
                        "unit_amount": amount
                    },
                    "quantity": int(it["qtd"])
                })

            success_url = f"{app.config.get('BASE_URL')}{url_for('checkout_success')}?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{app.config.get('BASE_URL')}{url_for('checkout_cancel')}?pedido_id={pedido.id}"

            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"pedido_id": str(pedido.id)}
            )

            pedido.stripe_session_id = checkout_session.id
            db.session.commit()

            return redirect(checkout_session.url)

        # Pagamento na entrega
        session["cart"] = {}
        session.modified = True

        flash("✅ Pedido enviado! Em breve entraremos em contato.", "success")
        return redirect(url_for("pedido_confirmado", pedido_id=pedido.id))

    @app.route("/pedido/<int:pedido_id>")
    def pedido_confirmado(pedido_id):
        cfg = get_site_config()
        pedido = Pedido.query.get_or_404(pedido_id)
        itens = json.loads(pedido.itens_json or "[]")
        return render_template("pedido_confirmado.html", cfg=cfg, pedido=pedido, itens=itens, cart_total=0, cart_items=[])

    @app.route("/checkout/success")
    def checkout_success():
        # ✅ Aqui NÃO marcamos como pago.
        # A confirmação verdadeira vem do WEBHOOK.
        session_id = request.args.get("session_id", "")
        if not session_id:
            abort(400)

        pedido = Pedido.query.filter_by(stripe_session_id=session_id).first()
        if not pedido:
            abort(404)

        # limpa carrinho mesmo assim
        session["cart"] = {}
        session.modified = True

        flash("✅ Pagamento processado! A confirmação final chega em instantes.", "success")
        return redirect(url_for("pedido_confirmado", pedido_id=pedido.id))

    @app.route("/checkout/cancel")
    def checkout_cancel():
        pedido_id = request.args.get("pedido_id", type=int)
        if pedido_id:
            pedido = Pedido.query.get(pedido_id)
            if pedido and pedido.status == "aguardando_pagamento":
                pedido.status = "cancelado"
                db.session.commit()
        flash("Pagamento cancelado. Você pode tentar novamente.", "info")
        return redirect(url_for("checkout"))

    # ---------- ✅ Stripe Webhook ----------
    @app.route("/webhook/stripe", methods=["POST"])
    def stripe_webhook():
        payload = request.get_data(as_text=False)
        sig_header = request.headers.get("Stripe-Signature", "")

        webhook_secret = app.config.get("STRIPE_WEBHOOK_SECRET", "")
        if not webhook_secret:
            # Sem secret, não dá pra validar assinatura
            return ("Webhook secret não configurado", 400)

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=webhook_secret
            )
        except ValueError:
            return ("Payload inválido", 400)
        except stripe.error.SignatureVerificationError:
            return ("Assinatura inválida", 400)

        # Evento principal: pagamento finalizado
        if event["type"] == "checkout.session.completed":
            session_obj = event["data"]["object"]
            pedido_id = None

            # tenta via metadata
            meta = session_obj.get("metadata") or {}
            if meta.get("pedido_id"):
                try:
                    pedido_id = int(meta["pedido_id"])
                except Exception:
                    pedido_id = None

            # fallback: procurar pelo stripe_session_id
            stripe_session_id = session_obj.get("id")

            pedido = None
            if pedido_id:
                pedido = Pedido.query.get(pedido_id)
            if not pedido and stripe_session_id:
                pedido = Pedido.query.filter_by(stripe_session_id=stripe_session_id).first()

            if pedido:
                pedido.status = "pago"
                db.session.commit()

        return ("OK", 200)

    # ---------- Admin ----------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            senha = (request.form.get("senha", "") or "").strip()
            if senha == app.config.get("ADMIN_PASSWORD"):
                session["is_admin"] = True
                flash("✅ Admin logado.", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Senha de admin incorreta.", "danger")
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        flash("Saiu do admin.", "info")
        return redirect(url_for("index"))

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        total_prod = Produto.query.count()
        total_cat = Categoria.query.count()
        total_pedidos = Pedido.query.count()
        ultimos = Pedido.query.order_by(Pedido.id.desc()).limit(10).all()
        return render_template("admin/dashboard.html", total_prod=total_prod, total_cat=total_cat, total_pedidos=total_pedidos, ultimos=ultimos)

    @app.route("/admin/categorias", methods=["GET", "POST"])
    @admin_required
    def admin_categorias():
        if request.method == "POST":
            nome = (request.form.get("nome", "") or "").strip()
            ordem = request.form.get("ordem", type=int, default=0)
            ativo = True if request.form.get("ativo") == "on" else False

            if len(nome) < 2:
                flash("Nome da categoria inválido.", "warning")
            else:
                c = Categoria(nome=nome, ordem=ordem, ativo=ativo)
                db.session.add(c)
                db.session.commit()
                flash("✅ Categoria criada.", "success")

            return redirect(url_for("admin_categorias"))

        categorias = Categoria.query.order_by(Categoria.ordem.asc(), Categoria.nome.asc()).all()
        return render_template("admin/categorias.html", categorias=categorias)

    @app.route("/admin/categorias/<int:cat_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_categoria_edit(cat_id):
        c = Categoria.query.get_or_404(cat_id)

        if request.method == "POST":
            nome = (request.form.get("nome", "") or "").strip()
            ordem = request.form.get("ordem", type=int, default=c.ordem)
            ativo = True if request.form.get("ativo") == "on" else False

            if len(nome) < 2:
                flash("Nome da categoria inválido.", "warning")
                return redirect(url_for("admin_categoria_edit", cat_id=c.id))

            c.nome = nome
            c.ordem = ordem
            c.ativo = ativo
            db.session.commit()

            flash("✅ Categoria atualizada.", "success")
            return redirect(url_for("admin_categorias"))

        return render_template("admin/categoria_editar.html", categoria=c)

    @app.route("/admin/categorias/<int:cat_id>/toggle")
    @admin_required
    def admin_categoria_toggle(cat_id):
        c = Categoria.query.get_or_404(cat_id)
        c.ativo = not c.ativo
        db.session.commit()
        return redirect(url_for("admin_categorias"))

    @app.route("/admin/categorias/<int:cat_id>/delete")
    @admin_required
    def admin_categoria_delete(cat_id):
        c = Categoria.query.get_or_404(cat_id)
        if Produto.query.filter_by(categoria_id=c.id).count() > 0:
            flash("Remova/realocar produtos da categoria antes de excluir.", "warning")
            return redirect(url_for("admin_categorias"))
        db.session.delete(c)
        db.session.commit()
        flash("Categoria excluída.", "info")
        return redirect(url_for("admin_categorias"))

    @app.route("/admin/produtos", methods=["GET", "POST"])
    @admin_required
    def admin_produtos():
        categorias = Categoria.query.order_by(Categoria.nome.asc()).all()

        if request.method == "POST":
            nome = (request.form.get("nome", "") or "").strip()
            descricao = (request.form.get("descricao", "") or "").strip()
            preco = request.form.get("preco", type=float, default=0.0)
            categoria_id = request.form.get("categoria_id", type=int)
            ativo = True if request.form.get("ativo") == "on" else False

            imagem_url = ""
            file = request.files.get("imagem_file")

            try:
                if file and file.filename:
                    imagem_url = save_uploaded_image(file)
                else:
                    imagem_url = (request.form.get("imagem_url", "") or "").strip()
            except ValueError as e:
                flash(str(e), "warning")
                return redirect(url_for("admin_produtos"))

            if len(nome) < 2 or not categoria_id:
                flash("Preencha nome e categoria.", "warning")
                return redirect(url_for("admin_produtos"))

            p = Produto(nome=nome, descricao=descricao, preco=float(preco), imagem_url=imagem_url, categoria_id=categoria_id, ativo=ativo)
            db.session.add(p)
            db.session.commit()
            flash("✅ Produto criado.", "success")
            return redirect(url_for("admin_produtos"))

        produtos = Produto.query.order_by(Produto.id.desc()).all()
        return render_template("admin/produtos.html", produtos=produtos, categorias=categorias)

    @app.route("/admin/produtos/<int:pid>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_produto_edit(pid):
        produto = Produto.query.get_or_404(pid)
        categorias = Categoria.query.order_by(Categoria.nome.asc()).all()

        if request.method == "POST":
            nome = (request.form.get("nome", "") or "").strip()
            descricao = (request.form.get("descricao", "") or "").strip()
            preco = request.form.get("preco", type=float, default=float(produto.preco or 0))
            categoria_id = request.form.get("categoria_id", type=int, default=produto.categoria_id)
            ativo = True if request.form.get("ativo") == "on" else False

            file = request.files.get("imagem_file")
            nova_url = (request.form.get("imagem_url", "") or "").strip()

            try:
                if file and file.filename:
                    produto.imagem_url = save_uploaded_image(file)
                elif nova_url:
                    produto.imagem_url = nova_url
            except ValueError as e:
                flash(str(e), "warning")
                return redirect(url_for("admin_produto_edit", pid=produto.id))

            if len(nome) < 2 or not categoria_id:
                flash("Preencha nome e categoria.", "warning")
                return redirect(url_for("admin_produto_edit", pid=produto.id))

            produto.nome = nome
            produto.descricao = descricao
            produto.preco = float(preco)
            produto.categoria_id = categoria_id
            produto.ativo = ativo

            db.session.commit()
            flash("✅ Produto atualizado.", "success")
            return redirect(url_for("admin_produtos"))

        return render_template("admin/produto_editar.html", produto=produto, categorias=categorias)

    @app.route("/admin/produtos/<int:pid>/toggle")
    @admin_required
    def admin_produto_toggle(pid):
        p = Produto.query.get_or_404(pid)
        p.ativo = not p.ativo
        db.session.commit()
        return redirect(url_for("admin_produtos"))

    @app.route("/admin/produtos/<int:pid>/delete")
    @admin_required
    def admin_produto_delete(pid):
        p = Produto.query.get_or_404(pid)
        db.session.delete(p)
        db.session.commit()
        flash("Produto excluído.", "info")
        return redirect(url_for("admin_produtos"))

    @app.route("/admin/pedidos/<int:pedido_id>", methods=["GET", "POST"])
    @admin_required
    def admin_pedido_detalhe(pedido_id):
        pedido = Pedido.query.get_or_404(pedido_id)
        itens = json.loads(pedido.itens_json or "[]")

        if request.method == "POST":
            novo_status = request.form.get("status")
            if novo_status in ["novo", "aguardando_pagamento", "preparando", "saiu_entrega", "entregue", "cancelado", "pago"]:
                pedido.status = novo_status
                db.session.commit()
                flash("Status atualizado!", "success")
                return redirect(url_for("admin_pedido_detalhe", pedido_id=pedido.id))

        return render_template("admin/pedido_detalhe.html", pedido=pedido, itens=itens)

    @app.route("/admin/configuracoes", methods=["GET", "POST"])
    @admin_required
    def admin_configuracoes():
        cfg = get_site_config()

        if request.method == "POST":
            cfg.site_name = (request.form.get("site_name", cfg.site_name) or cfg.site_name).strip()
            cfg.whatsapp = (request.form.get("whatsapp", cfg.whatsapp) or cfg.whatsapp).strip()
            cfg.telefone = (request.form.get("telefone", cfg.telefone) or cfg.telefone).strip()
            cfg.endereco_linha1 = (request.form.get("endereco_linha1", cfg.endereco_linha1) or cfg.endereco_linha1).strip()
            cfg.endereco_linha2 = (request.form.get("endereco_linha2", cfg.endereco_linha2) or cfg.endereco_linha2).strip()
            cfg.entrega_cidade = (request.form.get("entrega_cidade", cfg.entrega_cidade) or cfg.entrega_cidade).strip()
            cfg.frete_gratis = True if request.form.get("frete_gratis") == "on" else False
            cfg.logo_url = (request.form.get("logo_url", cfg.logo_url) or cfg.logo_url).strip()

            db.session.commit()
            flash("✅ Configurações atualizadas.", "success")
            return redirect(url_for("admin_configuracoes"))

        return render_template("admin/configuracoes.html", cfg=cfg)

    # ---------- Errors ----------
    @app.errorhandler(404)
    def not_found(e):
        cfg = get_site_config()
        total, items = cart_total_and_items()
        return render_template("404.html", cfg=cfg, cart_total=total, cart_items=items), 404

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not SiteConfig.query.first():
            db.session.add(SiteConfig(site_name="Fiorenza Pizzaria e Restaurante", logo_url="/static/images/logo.png"))
            db.session.commit()

    if __name__ == "__main__":
        app.run()



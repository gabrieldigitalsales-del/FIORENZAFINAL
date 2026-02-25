from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class SiteConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    site_name = db.Column(db.String(200), default="Fiorenza Pizzaria e Restaurante")
    whatsapp = db.Column(db.String(30), default="5531999999999")  # formato: 55DDDNUMERO
    telefone = db.Column(db.String(30), default="3771-8931")

    endereco_linha1 = db.Column(db.String(255), default="Avenida Getulio Vargas, 411")
    endereco_linha2 = db.Column(db.String(255), default="Centro - Sete Lagoas - Minas Gerais")

    frete_gratis = db.Column(db.Boolean, default=True)
    entrega_cidade = db.Column(db.String(100), default="Sete Lagoas - MG")

    logo_url = db.Column(db.String(500), default="/static/images/logo.png")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefone = db.Column(db.String(20), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, default="")
    preco = db.Column(db.Float, nullable=False, default=0.0)
    imagem_url = db.Column(db.String(500), default="")
    ativo = db.Column(db.Boolean, default=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria.id"), nullable=False)
    categoria = db.relationship("Categoria", backref=db.backref("produtos", lazy=True))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", backref=db.backref("pedidos", lazy=True))

    nome = db.Column(db.String(120), default="")
    telefone = db.Column(db.String(20), default="")
    endereco = db.Column(db.String(255), default="")
    referencia = db.Column(db.String(255), default="")

    forma_pagamento = db.Column(db.String(50), default="")  # stripe | credito | debito | pix | dinheiro
    troco_para = db.Column(db.String(30), default="")       # ex: 100

    total = db.Column(db.Float, default=0.0)
    itens_json = db.Column(db.Text, default="")             # string JSON

    status = db.Column(db.String(50), default="novo")       # novo | pago | em_preparo | saiu | entregue | cancelado

    stripe_session_id = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
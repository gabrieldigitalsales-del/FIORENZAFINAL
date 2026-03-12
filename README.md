# Fiorenza - Pizzaria e Restaurante

Projeto completo de site para delivery e retirada, inspirado na experiência de apps como iFood, com:

- vitrine responsiva para clientes
- carrinho e checkout
- painel administrativo com login
- CRUD de categorias
- CRUD de itens do cardápio
- controle de bairros e taxas de entrega
- atualização de pedido mínimo, frete grátis, cores e textos do site
- gestão de pedidos
- backup em JSON

## Dados já configurados

- **Empresa:** Fiorenza - Pizzaria e Restaurante
- **Endereço:** Av Getulio Vargas, 411
- **Telefone/WhatsApp:** 31 3771 8931

## Login inicial do admin

- **Usuário:** `admin`
- **Senha:** `fiorenza123`

Altere essas credenciais assim que entrar no painel.

## Como rodar localmente

### Opção 1 - Python

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra no navegador:

- Site: `http://127.0.0.1:8000`
- Admin: `http://127.0.0.1:8000/admin`

### Opção 2 - Docker

```bash
docker build -t fiorenza-site .
docker run -p 8000:8000 -e APP_SECRET="uma-chave-forte" fiorenza-site
```

## Estrutura

```text
fiorenza_site/
├── app/
│   ├── main.py
│   ├── static/
│   │   ├── admin.js
│   │   ├── app.js
│   │   ├── favicon.svg
│   │   └── styles.css
│   └── templates/
│       ├── admin.html
│       └── index.html
├── data/
├── Dockerfile
├── README.md
└── requirements.txt
```

## O que você pode editar pelo painel

Sem tocar no código, o admin consegue:

- trocar nome, slogan, textos e rodapé
- mudar endereço, telefone, WhatsApp e horário
- alterar cores do site
- ativar/desativar delivery e retirada
- editar pedido mínimo, frete grátis e taxa de serviço
- criar, editar e remover categorias
- criar, editar e remover itens
- mudar preços, disponibilidade, destaque e ordem de exibição
- cadastrar bairros com taxa, tempo estimado e pedido mínimo por bairro
- acompanhar pedidos e mudar status
- alterar login e senha do admin
- baixar backup do sistema em JSON

## Observações importantes

1. O sistema salva dados em **SQLite** (`data/fiorenza.db`), criado automaticamente no primeiro uso.
2. O botão de WhatsApp envia uma cópia formatada do pedido para o número configurado.
3. Para produção, use HTTPS, mude a variável `APP_SECRET`, hospede atrás de um proxy e considere integrar pagamento real (Pix/cartão) se quiser cobrança automatizada.
4. Os bairros iniciais são exemplos e podem ser trocados pelo admin.

## Próximos passos sugeridos para produção

- publicar em um VPS, Render, Railway ou outro host com Python
- ligar domínio próprio
- adicionar gateway de pagamento
- conectar impressão de pedidos ou alertas em WhatsApp/e-mail

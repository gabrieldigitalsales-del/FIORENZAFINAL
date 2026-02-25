const FZ = {
  openCart(){
    document.getElementById("fzCartDrawer").classList.add("open");
    document.getElementById("fzCartBackdrop").classList.add("open");
    FZ.refreshCart();
  },
  closeCart(){
    document.getElementById("fzCartDrawer").classList.remove("open");
    document.getElementById("fzCartBackdrop").classList.remove("open");
  },
  moneyBR(v){
    const n = Number(v || 0);
    return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  },
  async refreshCart(){
    const res = await fetch("/api/cart");
    const data = await res.json();
    if(!data.ok) return;

    const items = data.items || [];
    const total = data.total || 0;

    // badge
    const qtyTotal = items.reduce((acc, it) => acc + (it.qtd || 0), 0);
    const badge = document.getElementById("fzCartBadge");
    if (badge) badge.textContent = String(qtyTotal);

    // total
    const totalEl = document.getElementById("fzCartTotal");
    if(totalEl) totalEl.textContent = FZ.moneyBR(total);

    // body
    const body = document.getElementById("fzCartBody");
    if(!body) return;

    if(items.length === 0){
      body.innerHTML = `
        <div class="text-center p-4">
          <div class="fs-1 mb-2">🛒</div>
          <div class="fw-bold">Seu carrinho está vazio</div>
          <div class="small text-white-50 mt-1">Adicione itens no cardápio.</div>
        </div>
      `;
      return;
    }

    body.innerHTML = items.map(it => `
      <div class="fz-cart-item">
        <img src="${it.imagem_url || 'https://via.placeholder.com/120'}" alt="">
        <div class="flex-grow-1">
          <div class="fw-bold">${it.nome}</div>
          <div class="small text-white-50">${it.categoria || ''}</div>
          <div class="d-flex align-items-center justify-content-between mt-2">
            <div class="fw-semibold">${FZ.moneyBR(it.preco)}</div>
            <div class="d-flex align-items-center gap-2">
              <button class="btn btn-sm btn-outline-light" onclick="FZ.updateQty(${it.id}, ${it.qtd - 1})">-</button>
              <span class="fw-bold">${it.qtd}</span>
              <button class="btn btn-sm btn-outline-light" onclick="FZ.updateQty(${it.id}, ${it.qtd + 1})">+</button>
            </div>
          </div>
          <div class="small text-white-50 mt-1">Subtotal: <span class="fw-semibold">${FZ.moneyBR(it.subtotal)}</span></div>
        </div>
      </div>
    `).join("");
  },
  async addToCart(productId, qty=1){
    const res = await fetch("/api/cart/add", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ product_id: productId, qty })
    });
    const data = await res.json();
    if(!data.ok){
      alert(data.error || "Erro ao adicionar no carrinho");
      return;
    }
    FZ.refreshCart();
    FZ.openCart();
  },
  async updateQty(productId, qty){
    const res = await fetch("/api/cart/update", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ product_id: productId, qty })
    });
    const data = await res.json();
    if(!data.ok){
      alert(data.error || "Erro ao atualizar carrinho");
      return;
    }
    FZ.refreshCart();
  },
  async clearCart(){
    if(!confirm("Tem certeza que deseja limpar o carrinho?")) return;
    const res = await fetch("/api/cart/clear", { method: "POST" });
    const data = await res.json();
    if(data.ok){
      FZ.refreshCart();
    }
  }
};

// Atualiza badge ao carregar
document.addEventListener("DOMContentLoaded", () => {
  FZ.refreshCart();
});
const CART_STORAGE_KEY = 'fiorenza_cart_v1';

const state = {
  settings: {},
  categories: [],
  items: [],
  neighborhoods: [],
  paymentMethods: [],
  activeCategory: 'all',
  search: '',
  cart: loadCart(),
  submitting: false,
};

const refs = {};

document.addEventListener('DOMContentLoaded', () => {
  cacheRefs();
  bindEvents();
  loadBootstrap();
});

function cacheRefs() {
  refs.toastRoot = document.getElementById('toastRoot');
  refs.brandName = document.getElementById('brandName');
  refs.brandTagline = document.getElementById('brandTagline');
  refs.heroBadge = document.getElementById('heroBadge');
  refs.heroBadgeLarge = document.getElementById('heroBadgeLarge');
  refs.bannerTitle = document.getElementById('bannerTitle');
  refs.bannerSubtitle = document.getElementById('bannerSubtitle');
  refs.addressText = document.getElementById('addressText');
  refs.hoursText = document.getElementById('hoursText');
  refs.deliveryTimeText = document.getElementById('deliveryTimeText');
  refs.deliveryMode = document.getElementById('deliveryMode');
  refs.minimumOrder = document.getElementById('minimumOrder');
  refs.freeDeliveryFrom = document.getElementById('freeDeliveryFrom');
  refs.phoneLink = document.getElementById('phoneLink');
  refs.whatsLink = document.getElementById('whatsLink');
  refs.quickInfo = document.getElementById('quickInfo');
  refs.searchInput = document.getElementById('searchInput');
  refs.featuredGrid = document.getElementById('featuredGrid');
  refs.categoryPills = document.getElementById('categoryPills');
  refs.menuGrid = document.getElementById('menuGrid');
  refs.cartItems = document.getElementById('cartItems');
  refs.cartEmpty = document.getElementById('cartEmpty');
  refs.cartCountBadge = document.getElementById('cartCountBadge');
  refs.subtotalValue = document.getElementById('subtotalValue');
  refs.deliveryFeeValue = document.getElementById('deliveryFeeValue');
  refs.totalEstimateValue = document.getElementById('totalEstimateValue');
  refs.checkoutBtn = document.getElementById('checkoutBtn');
  refs.mobileCartButton = document.getElementById('mobileCartButton');
  refs.mobileCartLabel = document.getElementById('mobileCartLabel');
  refs.mobileCartTotal = document.getElementById('mobileCartTotal');
  refs.footerRestaurantName = document.getElementById('footerRestaurantName');
  refs.footerNote = document.getElementById('footerNote');
  refs.footerAddress = document.getElementById('footerAddress');
  refs.footerPhone = document.getElementById('footerPhone');
  refs.footerInstagram = document.getElementById('footerInstagram');
  refs.scrollToMenuBtn = document.getElementById('scrollToMenuBtn');
  refs.menuSection = document.getElementById('menuSection');
  refs.checkoutModal = document.getElementById('checkoutModal');
  refs.checkoutForm = document.getElementById('checkoutForm');
  refs.deliveryTypeSelect = document.getElementById('deliveryTypeSelect');
  refs.neighborhoodSelect = document.getElementById('neighborhoodSelect');
  refs.paymentMethodSelect = document.getElementById('paymentMethodSelect');
  refs.changeForField = document.getElementById('changeForField');
  refs.addressFields = document.getElementById('addressFields');
  refs.checkoutSubtotal = document.getElementById('checkoutSubtotal');
  refs.checkoutDeliveryFee = document.getElementById('checkoutDeliveryFee');
  refs.checkoutServiceFee = document.getElementById('checkoutServiceFee');
  refs.checkoutTotal = document.getElementById('checkoutTotal');
  refs.serviceFeeRow = document.getElementById('serviceFeeRow');
  refs.submitOrderBtn = document.getElementById('submitOrderBtn');
  refs.successModal = document.getElementById('successModal');
  refs.successMessage = document.getElementById('successMessage');
  refs.successSummary = document.getElementById('successSummary');
  refs.successWhatsappBtn = document.getElementById('successWhatsappBtn');
}

function bindEvents() {
  refs.searchInput?.addEventListener('input', (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderMenu();
  });

  refs.scrollToMenuBtn?.addEventListener('click', () => {
    refs.menuSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  refs.categoryPills?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-category-id]');
    if (!button) return;
    state.activeCategory = button.dataset.categoryId;
    renderCategories();
    renderMenu();
  });

  refs.featuredGrid?.addEventListener('click', handleMenuAction);
  refs.menuGrid?.addEventListener('click', handleMenuAction);
  refs.cartItems?.addEventListener('click', handleCartAction);

  refs.checkoutBtn?.addEventListener('click', () => {
    if (!state.cart.length) {
      showToast('Adicione itens ao carrinho antes de continuar.', 'error');
      refs.menuSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    openCheckout();
  });

  refs.mobileCartButton?.addEventListener('click', () => {
    if (state.cart.length) {
      openCheckout();
    } else {
      refs.menuSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });

  document.addEventListener('click', (event) => {
    const closer = event.target.closest('[data-close-modal]');
    if (!closer) return;
    closeModal(closer.dataset.closeModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal('checkoutModal');
      closeModal('successModal');
    }
  });

  refs.deliveryTypeSelect?.addEventListener('change', () => {
    syncCheckoutAvailability();
    updateCheckoutSummary();
  });

  refs.neighborhoodSelect?.addEventListener('change', updateCheckoutSummary);
  refs.paymentMethodSelect?.addEventListener('change', syncPaymentFields);

  refs.checkoutForm?.addEventListener('submit', submitOrder);
}

async function loadBootstrap() {
  try {
    const response = await fetch('/api/public/bootstrap');
    if (!response.ok) throw new Error('Falha ao carregar o cardápio.');
    const payload = await response.json();
    state.settings = payload.settings || {};
    state.categories = payload.categories || [];
    state.items = payload.items || [];
    state.neighborhoods = payload.neighborhoods || [];
    state.paymentMethods = payload.payment_methods || ['Pix', 'Cartão', 'Dinheiro'];
    syncCartWithMenu();
    applyTheme();
    populateRestaurantInfo();
    populateCheckoutOptions();
    renderQuickInfo();
    renderFeatured();
    renderCategories();
    renderMenu();
    renderCart();
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Não foi possível carregar o site.', 'error');
  }
}

function applyTheme() {
  const root = document.documentElement;
  root.style.setProperty('--primary', state.settings.primary_color || '#ea1d2c');
  root.style.setProperty('--secondary', state.settings.secondary_color || '#ff7a00');
  root.style.setProperty('--background', state.settings.background_color || '#fff7f4');
  root.style.setProperty('--surface', state.settings.surface_color || '#ffffff');
  root.style.setProperty('--text', state.settings.text_color || '#232323');
  root.style.setProperty('--muted', state.settings.muted_text_color || '#6b7280');
}

function populateRestaurantInfo() {
  const settings = state.settings;
  const restaurantName = settings.restaurant_name || 'Fiorenza - Pizzaria e Restaurante';
  const whatsappDigits = sanitizePhone(settings.whatsapp || settings.phone || '31 3771 8931');
  const phoneDigits = sanitizePhone(settings.phone || settings.whatsapp || '31 3771 8931');
  const deliveryEnabled = Boolean(settings.delivery_enabled);
  const pickupEnabled = Boolean(settings.pickup_enabled);

  refs.brandName.textContent = restaurantName;
  refs.brandTagline.textContent = settings.tagline || '';
  refs.heroBadge.textContent = settings.hero_badge || 'Entrega rápida';
  refs.heroBadgeLarge.textContent = settings.hero_badge || 'Entrega rápida';
  refs.bannerTitle.textContent = settings.banner_title || restaurantName;
  refs.bannerSubtitle.textContent = settings.banner_subtitle || '';
  refs.addressText.textContent = settings.address || '';
  refs.hoursText.textContent = settings.opening_hours || '';
  refs.deliveryTimeText.textContent = settings.delivery_time || '';
  refs.minimumOrder.textContent = currency(Number(settings.minimum_order || 0));
  refs.freeDeliveryFrom.textContent = Number(settings.free_delivery_from || 0)
    ? `Acima de ${currency(Number(settings.free_delivery_from || 0))}`
    : 'Consulte regras';
  refs.phoneLink.href = `tel:+${phoneDigits}`;
  refs.whatsLink.href = `https://wa.me/${whatsappDigits}`;
  refs.footerRestaurantName.textContent = restaurantName;
  refs.footerNote.textContent = settings.footer_note || '';
  refs.footerAddress.textContent = settings.address || '';
  refs.footerPhone.textContent = settings.phone || '';
  refs.footerInstagram.textContent = settings.instagram || '@fiorenza';

  if (deliveryEnabled && pickupEnabled) {
    refs.deliveryMode.textContent = 'Delivery e retirada';
  } else if (deliveryEnabled) {
    refs.deliveryMode.textContent = 'Somente delivery';
  } else {
    refs.deliveryMode.textContent = 'Somente retirada';
  }
}

function populateCheckoutOptions() {
  const deliveryEnabled = Boolean(state.settings.delivery_enabled);
  const pickupEnabled = Boolean(state.settings.pickup_enabled);

  refs.deliveryTypeSelect.innerHTML = '';
  if (deliveryEnabled) {
    refs.deliveryTypeSelect.insertAdjacentHTML('beforeend', '<option value="delivery">Entrega</option>');
  }
  if (pickupEnabled) {
    refs.deliveryTypeSelect.insertAdjacentHTML('beforeend', '<option value="pickup">Retirada no balcão</option>');
  }
  if (!deliveryEnabled && pickupEnabled) {
    refs.deliveryTypeSelect.value = 'pickup';
  }

  refs.neighborhoodSelect.innerHTML = state.neighborhoods.length
    ? state.neighborhoods
        .map(
          (neighborhood) =>
            `<option value="${neighborhood.id}">${escapeHtml(neighborhood.name)} · ${currency(neighborhood.fee)}</option>`
        )
        .join('')
    : '<option value="">Nenhum bairro cadastrado</option>';

  refs.paymentMethodSelect.innerHTML = state.paymentMethods
    .map((method) => `<option value="${escapeHtml(method)}">${escapeHtml(method)}</option>`)
    .join('');

  syncCheckoutAvailability();
  syncPaymentFields();
  updateCheckoutSummary();
}

function renderQuickInfo() {
  const chips = [];
  if (state.settings.city) chips.push(`📍 ${state.settings.city}`);
  if (state.settings.opening_hours) chips.push(`🕒 ${state.settings.opening_hours}`);
  if (state.settings.delivery_time) chips.push(`🛵 ${state.settings.delivery_time}`);
  if (state.settings.instagram) chips.push(`📸 ${state.settings.instagram}`);
  refs.quickInfo.innerHTML = chips.map((chip) => `<span class="quick-chip">${escapeHtml(chip)}</span>`).join('');
}

function renderFeatured() {
  const featuredItems = state.items.filter((item) => item.featured).slice(0, 3);
  const items = featuredItems.length ? featuredItems : state.items.slice(0, 3);
  if (!items.length) {
    refs.featuredGrid.innerHTML = '<div class="empty-state">Nenhum destaque disponível no momento.</div>';
    return;
  }

  refs.featuredGrid.innerHTML = items.map((item) => itemCardTemplate(item, true)).join('');
}

function renderCategories() {
  const allCount = getFilteredItems('all').length;
  const pills = [
    `<button type="button" class="category-pill ${state.activeCategory === 'all' ? 'active' : ''}" data-category-id="all">Todos (${allCount})</button>`,
    ...state.categories.map((category) => {
      const count = getFilteredItems(String(category.id)).length;
      const activeClass = state.activeCategory === String(category.id) ? 'active' : '';
      return `<button type="button" class="category-pill ${activeClass}" data-category-id="${category.id}">${escapeHtml(category.name)} (${count})</button>`;
    }),
  ];
  refs.categoryPills.innerHTML = pills.join('');
}

function renderMenu() {
  const items = getFilteredItems(state.activeCategory);
  if (!items.length) {
    refs.menuGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔎</div>
        <p>Nenhum item encontrado para os filtros atuais.</p>
      </div>
    `;
    return;
  }
  refs.menuGrid.innerHTML = items.map((item) => itemCardTemplate(item, false)).join('');
}

function renderCart() {
  const details = getCartDetails();
  const subtotal = details.reduce((sum, item) => sum + item.lineTotal, 0);
  const estimate = getCurrentDeliveryEstimate();
  const totalEstimate = subtotal + estimate + Number(state.settings.service_fee || 0);
  const count = details.reduce((sum, item) => sum + item.quantity, 0);

  refs.cartCountBadge.textContent = `${count} ${count === 1 ? 'item' : 'itens'}`;
  refs.cartItems.innerHTML = details
    .map(
      (item) => `
        <article class="cart-item">
          <div class="cart-item-top">
            <div>
              <h4>${escapeHtml(item.name)}</h4>
              <p>${currency(item.unitPrice)} cada</p>
            </div>
            <strong>${currency(item.lineTotal)}</strong>
          </div>
          <div class="modal-actions left">
            <div class="qty-controls">
              <button class="qty-btn" type="button" data-action="decrease" data-item-id="${item.item_id}" aria-label="Diminuir">−</button>
              <strong>${item.quantity}</strong>
              <button class="qty-btn" type="button" data-action="increase" data-item-id="${item.item_id}" aria-label="Aumentar">+</button>
            </div>
            <button class="ghost-btn" type="button" data-action="remove" data-item-id="${item.item_id}">Remover</button>
          </div>
        </article>
      `
    )
    .join('');
  refs.cartEmpty.classList.toggle('hidden', !!details.length);
  refs.subtotalValue.textContent = currency(subtotal);
  refs.deliveryFeeValue.textContent = estimate ? `A partir de ${currency(estimate)}` : 'Calculado no checkout';
  refs.totalEstimateValue.textContent = currency(totalEstimate);
  refs.mobileCartLabel.textContent = count ? `${count} ${count === 1 ? 'item' : 'itens'} no carrinho` : 'Carrinho vazio';
  refs.mobileCartTotal.textContent = currency(totalEstimate);
}

function itemCardTemplate(item, featured) {
  const emoji = emojiForCategory(item.category_name);
  return `
    <article class="${featured ? 'featured-card' : 'menu-card'}">
      <div class="item-visual">
        ${item.image_url ? `<img src="${escapeAttribute(item.image_url)}" alt="${escapeAttribute(item.name)}" loading="lazy" />` : `<div class="item-fallback">${emoji}</div>`}
      </div>
      <div class="${featured ? 'featured-content' : 'menu-content'}">
        <div class="item-meta">
          <span class="item-category-tag">${escapeHtml(item.category_name)}</span>
          ${item.featured ? '<span class="item-badge">Mais pedido</span>' : ''}
          <span class="status-tag">${item.prep_time} min</span>
        </div>
        <h4>${escapeHtml(item.name)}</h4>
        <p class="item-desc">${escapeHtml(item.description || 'Sem descrição.')}</p>
        <div class="price-row">
          <strong>${currency(item.price)}</strong>
          <button type="button" class="primary-btn" data-action="add" data-item-id="${item.id}">Adicionar</button>
        </div>
      </div>
    </article>
  `;
}

function handleMenuAction(event) {
  const addButton = event.target.closest('[data-action="add"]');
  if (!addButton) return;
  const itemId = Number(addButton.dataset.itemId);
  addToCart(itemId);
}

function handleCartAction(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const itemId = Number(button.dataset.itemId);
  const action = button.dataset.action;
  if (action === 'increase') changeQuantity(itemId, 1);
  if (action === 'decrease') changeQuantity(itemId, -1);
  if (action === 'remove') removeFromCart(itemId);
}

function addToCart(itemId) {
  const item = state.items.find((entry) => entry.id === itemId);
  if (!item) return;
  const existing = state.cart.find((entry) => entry.item_id === itemId);
  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({ item_id: itemId, quantity: 1, notes: '' });
  }
  persistCart();
  renderCart();
  updateCheckoutSummary();
  showToast(`${item.name} adicionado ao carrinho.`, 'success');
}

function changeQuantity(itemId, delta) {
  const entry = state.cart.find((item) => item.item_id === itemId);
  if (!entry) return;
  entry.quantity += delta;
  if (entry.quantity <= 0) {
    state.cart = state.cart.filter((item) => item.item_id !== itemId);
  }
  persistCart();
  renderCart();
  updateCheckoutSummary();
}

function removeFromCart(itemId) {
  const item = state.items.find((entry) => entry.id === itemId);
  state.cart = state.cart.filter((entry) => entry.item_id !== itemId);
  persistCart();
  renderCart();
  updateCheckoutSummary();
  if (item) showToast(`${item.name} removido do carrinho.`, 'success');
}

function getFilteredItems(categoryId) {
  return state.items.filter((item) => {
    const matchesCategory = categoryId === 'all' || String(item.category_id) === String(categoryId);
    const search = state.search.trim();
    const haystack = `${item.name} ${item.description} ${item.category_name}`.toLowerCase();
    const matchesSearch = !search || haystack.includes(search);
    return matchesCategory && matchesSearch;
  });
}

function getCartDetails() {
  return state.cart
    .map((entry) => {
      const item = state.items.find((candidate) => candidate.id === entry.item_id);
      if (!item) return null;
      const quantity = Number(entry.quantity || 0);
      const unitPrice = Number(item.price || 0);
      return {
        ...entry,
        name: item.name,
        unitPrice,
        lineTotal: quantity * unitPrice,
      };
    })
    .filter(Boolean);
}

function getCurrentDeliveryEstimate() {
  if (!state.neighborhoods.length) return 0;
  return Math.min(...state.neighborhoods.map((neighborhood) => Number(neighborhood.fee || 0)));
}

function syncCartWithMenu() {
  const validIds = new Set(state.items.map((item) => item.id));
  state.cart = state.cart.filter((entry) => validIds.has(entry.item_id) && Number(entry.quantity) > 0);
  persistCart();
}

function openCheckout() {
  const details = getCartDetails();
  if (!details.length) {
    showToast('Seu carrinho está vazio.', 'error');
    return;
  }
  updateCheckoutSummary();
  openModal('checkoutModal');
}

function syncCheckoutAvailability() {
  const deliveryType = refs.deliveryTypeSelect.value;
  const isDelivery = deliveryType === 'delivery';
  refs.addressFields.classList.toggle('hidden', !isDelivery);
  refs.neighborhoodSelect.disabled = !isDelivery || !state.neighborhoods.length;
  if (!isDelivery) {
    refs.neighborhoodSelect.value = '';
  } else if (!refs.neighborhoodSelect.value && state.neighborhoods.length) {
    refs.neighborhoodSelect.value = String(state.neighborhoods[0].id);
  }
}

function syncPaymentFields() {
  const isCash = refs.paymentMethodSelect.value === 'Dinheiro';
  refs.changeForField.classList.toggle('hidden', !isCash);
  const changeInput = refs.checkoutForm.querySelector('input[name="change_for"]');
  if (!isCash && changeInput) changeInput.value = '';
}

function updateCheckoutSummary() {
  const cartDetails = getCartDetails();
  const subtotal = cartDetails.reduce((sum, item) => sum + item.lineTotal, 0);
  const serviceFee = Number(state.settings.service_fee || 0);
  const deliveryType = refs.deliveryTypeSelect?.value || 'delivery';
  let deliveryFee = 0;

  if (deliveryType === 'delivery') {
    const neighborhood = state.neighborhoods.find((entry) => String(entry.id) === String(refs.neighborhoodSelect?.value || ''));
    if (neighborhood) deliveryFee = Number(neighborhood.fee || 0);
    const freeDeliveryFrom = Number(state.settings.free_delivery_from || 0);
    if (freeDeliveryFrom && subtotal >= freeDeliveryFrom) deliveryFee = 0;
  }

  const total = subtotal + serviceFee + deliveryFee;
  refs.checkoutSubtotal.textContent = currency(subtotal);
  refs.checkoutDeliveryFee.textContent = deliveryType === 'pickup' ? 'R$ 0,00' : currency(deliveryFee);
  refs.checkoutServiceFee.textContent = currency(serviceFee);
  refs.checkoutTotal.textContent = currency(total);
  refs.serviceFeeRow.classList.toggle('hidden', !serviceFee);
}

async function submitOrder(event) {
  event.preventDefault();
  if (state.submitting) return;
  const details = getCartDetails();
  if (!details.length) {
    showToast('Seu carrinho está vazio.', 'error');
    return;
  }

  const form = new FormData(refs.checkoutForm);
  const payload = {
    customer_name: form.get('customer_name')?.toString().trim() || '',
    phone: form.get('phone')?.toString().trim() || '',
    delivery_type: form.get('delivery_type')?.toString() || 'delivery',
    neighborhood_id: form.get('delivery_type') === 'pickup' ? null : Number(form.get('neighborhood_id') || 0) || null,
    address_line: form.get('address_line')?.toString().trim() || '',
    address_number: form.get('address_number')?.toString().trim() || '',
    address_complement: form.get('address_complement')?.toString().trim() || '',
    payment_method: form.get('payment_method')?.toString() || 'Pix',
    change_for: Number(form.get('change_for') || 0) || 0,
    notes: form.get('notes')?.toString().trim() || '',
    cart: state.cart.map((entry) => ({
      item_id: entry.item_id,
      quantity: entry.quantity,
      notes: entry.notes || '',
    })),
  };

  state.submitting = true;
  refs.submitOrderBtn.disabled = true;
  refs.submitOrderBtn.textContent = 'Enviando pedido...';

  try {
    const response = await fetch('/api/public/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Falha ao enviar pedido.');

    state.cart = [];
    persistCart();
    renderCart();
    refs.checkoutForm.reset();
    populateCheckoutOptions();
    closeModal('checkoutModal');
    showSuccess(result);
    showToast('Pedido confirmado com sucesso.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Não foi possível enviar o pedido.', 'error');
  } finally {
    state.submitting = false;
    refs.submitOrderBtn.disabled = false;
    refs.submitOrderBtn.textContent = 'Confirmar pedido';
  }
}

function showSuccess(result) {
  const order = result.order || {};
  refs.successMessage.textContent = `Pedido ${order.order_code || ''} registrado. Você pode enviar uma cópia para o WhatsApp da loja.`;
  const neighborhood = order.delivery_type === 'delivery' && order.neighborhood_name ? ` · ${escapeHtml(order.neighborhood_name)}` : '';
  refs.successSummary.innerHTML = `
    <div class="overview-item"><span>Código</span><strong>${escapeHtml(order.order_code || '-')}</strong></div>
    <div class="overview-item"><span>Cliente</span><strong>${escapeHtml(order.customer_name || '-')}</strong></div>
    <div class="overview-item"><span>Recebimento</span><strong>${order.delivery_type === 'pickup' ? 'Retirada no balcão' : `Entrega${neighborhood}`}</strong></div>
    <div class="overview-item"><span>Total</span><strong>${currency(Number(order.total || 0))}</strong></div>
  `;
  refs.successWhatsappBtn.href = result.whatsapp_url || '#';
  openModal('successModal');
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
}

function currency(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value || 0));
}

function loadCart() {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error(error);
    return [];
  }
}

function persistCart() {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state.cart));
}

function sanitizePhone(value) {
  const digits = String(value || '').replace(/\D+/g, '');
  if (digits.startsWith('55')) return digits;
  return `55${digits}`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll('`', '&#96;');
}

function emojiForCategory(name) {
  const normalized = String(name || '').toLowerCase();
  if (normalized.includes('pizza')) return '🍕';
  if (normalized.includes('massa')) return '🍝';
  if (normalized.includes('bebida')) return '🥤';
  if (normalized.includes('prato')) return '🍽️';
  return '🍴';
}

function showToast(message, type = 'default') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  refs.toastRoot.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3200);
}

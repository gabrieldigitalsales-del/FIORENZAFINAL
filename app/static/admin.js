const adminState = {
  admin: null,
  settings: {},
  categories: [],
  items: [],
  neighborhoods: [],
  orders: [],
  summary: {},
  statuses: [],
};

const refs = {};

document.addEventListener('DOMContentLoaded', () => {
  cacheRefs();
  bindEvents();
  checkSession();
});

function cacheRefs() {
  refs.toastRoot = document.getElementById('toastRoot');
  refs.loginView = document.getElementById('loginView');
  refs.dashboardView = document.getElementById('dashboardView');
  refs.loginForm = document.getElementById('loginForm');
  refs.logoutBtn = document.getElementById('logoutBtn');
  refs.tabsBar = document.getElementById('tabsBar');
  refs.statsGrid = document.getElementById('statsGrid');
  refs.overviewList = document.getElementById('overviewList');
  refs.pendingOrdersPreview = document.getElementById('pendingOrdersPreview');
  refs.settingsForm = document.getElementById('settingsForm');
  refs.categoryForm = document.getElementById('categoryForm');
  refs.categoryResetBtn = document.getElementById('categoryResetBtn');
  refs.categoriesList = document.getElementById('categoriesList');
  refs.itemForm = document.getElementById('itemForm');
  refs.itemResetBtn = document.getElementById('itemResetBtn');
  refs.itemsList = document.getElementById('itemsList');
  refs.itemCategorySelect = document.getElementById('itemCategorySelect');
  refs.neighborhoodForm = document.getElementById('neighborhoodForm');
  refs.neighborhoodResetBtn = document.getElementById('neighborhoodResetBtn');
  refs.neighborhoodsList = document.getElementById('neighborhoodsList');
  refs.ordersList = document.getElementById('ordersList');
  refs.credentialsForm = document.getElementById('credentialsForm');
}

function bindEvents() {
  refs.loginForm?.addEventListener('submit', handleLogin);
  refs.logoutBtn?.addEventListener('click', handleLogout);

  refs.tabsBar?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-tab]');
    if (!button) return;
    activateTab(button.dataset.tab);
  });

  refs.settingsForm?.addEventListener('submit', saveSettings);
  refs.categoryForm?.addEventListener('submit', saveCategory);
  refs.categoryResetBtn?.addEventListener('click', resetCategoryForm);
  refs.itemForm?.addEventListener('submit', saveItem);
  refs.itemResetBtn?.addEventListener('click', resetItemForm);
  refs.neighborhoodForm?.addEventListener('submit', saveNeighborhood);
  refs.neighborhoodResetBtn?.addEventListener('click', resetNeighborhoodForm);
  refs.credentialsForm?.addEventListener('submit', saveCredentials);

  refs.categoriesList?.addEventListener('click', handleCategoryListActions);
  refs.itemsList?.addEventListener('click', handleItemListActions);
  refs.neighborhoodsList?.addEventListener('click', handleNeighborhoodListActions);
  refs.ordersList?.addEventListener('click', handleOrderActions);
}

async function checkSession() {
  try {
    const response = await fetch('/api/admin/session');
    const result = await response.json();
    if (result.authenticated) {
      adminState.admin = result.admin;
      showDashboard();
      await loadBootstrap();
    } else {
      showLogin();
    }
  } catch (error) {
    console.error(error);
    showLogin();
  }
}

function showLogin() {
  refs.loginView.classList.remove('hidden');
  refs.dashboardView.classList.add('hidden');
  refs.logoutBtn.classList.add('hidden');
}

function showDashboard() {
  refs.loginView.classList.add('hidden');
  refs.dashboardView.classList.remove('hidden');
  refs.logoutBtn.classList.remove('hidden');
}

async function loadBootstrap() {
  try {
    const response = await fetch('/api/admin/bootstrap');
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Falha ao carregar painel.');
    adminState.admin = payload.admin;
    adminState.settings = payload.settings || {};
    adminState.categories = payload.categories || [];
    adminState.items = payload.items || [];
    adminState.neighborhoods = payload.neighborhoods || [];
    adminState.orders = payload.orders || [];
    adminState.summary = payload.summary || {};
    adminState.statuses = payload.statuses || [];
    renderDashboard();
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Não foi possível carregar o painel.', 'error');
    if (String(error.message).toLowerCase().includes('login')) {
      showLogin();
    }
  }
}

function renderDashboard() {
  renderStats();
  renderOverview();
  renderPendingPreview();
  populateSettingsForm();
  populateCategorySelect();
  renderCategories();
  renderItems();
  renderNeighborhoods();
  renderOrders();
  populateCredentialForm();
}

function renderStats() {
  const summary = adminState.summary;
  const cards = [
    ['Itens', summary.items_count || 0],
    ['Categorias', summary.categories_count || 0],
    ['Bairros', summary.neighborhoods_count || 0],
    ['Pedidos', summary.orders_count || 0],
    ['Receita', currency(summary.revenue_total || 0)],
  ];
  refs.statsGrid.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="stats-card glass-card">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(String(value))}</strong>
        </article>
      `
    )
    .join('');
}

function renderOverview() {
  const settings = adminState.settings;
  const items = [
    ['Restaurante', settings.restaurant_name || '-'],
    ['Telefone', settings.phone || '-'],
    ['WhatsApp', settings.whatsapp || '-'],
    ['Horário', settings.opening_hours || '-'],
    ['Pedido mínimo', currency(settings.minimum_order || 0)],
    ['Frete grátis acima de', currency(settings.free_delivery_from || 0)],
    ['Delivery', settings.delivery_enabled ? 'Ativo' : 'Desativado'],
    ['Retirada', settings.pickup_enabled ? 'Ativa' : 'Desativada'],
  ];
  refs.overviewList.innerHTML = items
    .map(
      ([label, value]) => `
        <div class="overview-item">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(String(value))}</strong>
        </div>
      `
    )
    .join('');
}

function renderPendingPreview() {
  const pending = adminState.orders.filter((order) => ['novo', 'confirmado', 'preparo'].includes(order.status)).slice(0, 5);
  if (!pending.length) {
    refs.pendingOrdersPreview.innerHTML = '<div class="empty-state">Nenhum pedido pendente no momento.</div>';
    return;
  }
  refs.pendingOrdersPreview.innerHTML = pending
    .map(
      (order) => `
        <article class="pending-card">
          <span class="section-kicker">${escapeHtml(order.order_code)}</span>
          <strong>${escapeHtml(order.customer_name)}</strong>
          <p>${escapeHtml(order.delivery_type === 'pickup' ? 'Retirada no balcão' : `Entrega - ${order.neighborhood_name || 'bairro não informado'}`)}</p>
          <p>Total: <strong>${currency(order.total)}</strong> · Status: <strong>${escapeHtml(order.status)}</strong></p>
        </article>
      `
    )
    .join('');
}

function populateSettingsForm() {
  const form = refs.settingsForm;
  if (!form) return;
  setFormValue(form, 'restaurant_name', adminState.settings.restaurant_name);
  setFormValue(form, 'tagline', adminState.settings.tagline);
  setFormValue(form, 'city', adminState.settings.city);
  setFormValue(form, 'address', adminState.settings.address);
  setFormValue(form, 'phone', adminState.settings.phone);
  setFormValue(form, 'whatsapp', adminState.settings.whatsapp);
  setFormValue(form, 'opening_hours', adminState.settings.opening_hours);
  setFormValue(form, 'delivery_time', adminState.settings.delivery_time);
  setFormValue(form, 'pickup_time', adminState.settings.pickup_time);
  setFormValue(form, 'minimum_order', adminState.settings.minimum_order);
  setFormValue(form, 'free_delivery_from', adminState.settings.free_delivery_from);
  setFormValue(form, 'service_fee', adminState.settings.service_fee);
  setFormValue(form, 'banner_title', adminState.settings.banner_title);
  setFormValue(form, 'banner_subtitle', adminState.settings.banner_subtitle);
  setFormValue(form, 'hero_badge', adminState.settings.hero_badge);
  setFormValue(form, 'pix_key', adminState.settings.pix_key);
  setFormValue(form, 'instagram', adminState.settings.instagram);
  setFormValue(form, 'footer_note', adminState.settings.footer_note);
  setFormValue(form, 'primary_color', adminState.settings.primary_color);
  setFormValue(form, 'secondary_color', adminState.settings.secondary_color);
  setFormValue(form, 'background_color', adminState.settings.background_color);
  setFormValue(form, 'text_color', adminState.settings.text_color);
  setCheckboxValue(form, 'delivery_enabled', adminState.settings.delivery_enabled);
  setCheckboxValue(form, 'pickup_enabled', adminState.settings.pickup_enabled);
}

function populateCategorySelect() {
  refs.itemCategorySelect.innerHTML = adminState.categories
    .map((category) => `<option value="${category.id}">${escapeHtml(category.name)}</option>`)
    .join('');
}

function renderCategories() {
  if (!adminState.categories.length) {
    refs.categoriesList.innerHTML = '<div class="empty-state">Nenhuma categoria cadastrada.</div>';
    return;
  }
  refs.categoriesList.innerHTML = adminState.categories
    .map(
      (category) => `
        <article class="entity-card">
          <header>
            <div>
              <span class="item-category-tag">Ordem ${category.sort_order}</span>
              <h4>${escapeHtml(category.name)}</h4>
            </div>
            <span class="status-tag">${category.active ? 'Ativa' : 'Oculta'}</span>
          </header>
          <p>${escapeHtml(category.description || 'Sem descrição.')}</p>
          <div class="entity-actions">
            <button type="button" class="entity-edit" data-action="edit-category" data-id="${category.id}">Editar</button>
            <button type="button" class="entity-delete" data-action="delete-category" data-id="${category.id}">Excluir</button>
          </div>
        </article>
      `
    )
    .join('');
}

function renderItems() {
  if (!adminState.items.length) {
    refs.itemsList.innerHTML = '<div class="empty-state">Nenhum item cadastrado.</div>';
    return;
  }
  refs.itemsList.innerHTML = adminState.items
    .map(
      (item) => `
        <article class="entity-card">
          <header>
            <div>
              <span class="item-category-tag">${escapeHtml(item.category_name)}</span>
              <h4>${escapeHtml(item.name)}</h4>
            </div>
            <span class="status-tag">${item.available ? 'Disponível' : 'Indisponível'}</span>
          </header>
          <p>${escapeHtml(item.description || 'Sem descrição.')}</p>
          <p><strong>${currency(item.price)}</strong> · preparo ${item.prep_time} min · ordem ${item.sort_order} ${item.featured ? '· destaque' : ''}</p>
          <div class="entity-actions">
            <button type="button" class="entity-edit" data-action="edit-item" data-id="${item.id}">Editar</button>
            <button type="button" class="entity-delete" data-action="delete-item" data-id="${item.id}">Excluir</button>
          </div>
        </article>
      `
    )
    .join('');
}

function renderNeighborhoods() {
  if (!adminState.neighborhoods.length) {
    refs.neighborhoodsList.innerHTML = '<div class="empty-state">Nenhum bairro cadastrado.</div>';
    return;
  }
  refs.neighborhoodsList.innerHTML = adminState.neighborhoods
    .map(
      (neighborhood) => `
        <article class="entity-card">
          <header>
            <div>
              <span class="item-category-tag">${neighborhood.eta_min} min</span>
              <h4>${escapeHtml(neighborhood.name)}</h4>
            </div>
            <span class="status-tag">${neighborhood.active ? 'Ativo' : 'Inativo'}</span>
          </header>
          <p>Frete ${currency(neighborhood.fee)} · Pedido mínimo ${currency(neighborhood.minimum_order)}</p>
          <div class="entity-actions">
            <button type="button" class="entity-edit" data-action="edit-neighborhood" data-id="${neighborhood.id}">Editar</button>
            <button type="button" class="entity-delete" data-action="delete-neighborhood" data-id="${neighborhood.id}">Excluir</button>
          </div>
        </article>
      `
    )
    .join('');
}

function renderOrders() {
  if (!adminState.orders.length) {
    refs.ordersList.innerHTML = '<div class="empty-state">Nenhum pedido recebido ainda.</div>';
    return;
  }
  refs.ordersList.innerHTML = adminState.orders
    .map((order) => {
      const itemsHtml = order.items
        .map(
          (item) => `
            <div class="order-item-line">
              <span>${item.quantity}x ${escapeHtml(item.name)}</span>
              <strong>${currency(item.line_total)}</strong>
            </div>
          `
        )
        .join('');

      return `
        <article class="order-card">
          <header>
            <div>
              <span class="section-kicker">${escapeHtml(order.order_code)}</span>
              <h4>${escapeHtml(order.customer_name)} · ${escapeHtml(order.phone)}</h4>
            </div>
            <span class="status-tag">${escapeHtml(order.status)}</span>
          </header>
          <p>${escapeHtml(order.delivery_type === 'pickup' ? 'Retirada no balcão' : `Entrega em ${order.neighborhood_name || 'bairro não informado'}`)}</p>
          ${order.delivery_type === 'delivery' ? `<p>Endereço: ${escapeHtml(order.address_line || '')}, ${escapeHtml(order.address_number || '')}${order.address_complement ? ` · ${escapeHtml(order.address_complement)}` : ''}</p>` : ''}
          ${order.notes ? `<p>Obs: ${escapeHtml(order.notes)}</p>` : ''}
          <div class="order-items-list">${itemsHtml}</div>
          <div class="order-total-grid">
            <div class="mini-box"><span>Subtotal</span><strong>${currency(order.subtotal)}</strong></div>
            <div class="mini-box"><span>Entrega</span><strong>${currency(order.delivery_fee)}</strong></div>
            <div class="mini-box"><span>Total</span><strong>${currency(order.total)}</strong></div>
          </div>
          <div class="order-status-control">
            <select data-order-status-select data-order-id="${order.id}">
              ${adminState.statuses
                .map(
                  (status) =>
                    `<option value="${escapeHtml(status)}" ${status === order.status ? 'selected' : ''}>${escapeHtml(status)}</option>`
                )
                .join('')}
            </select>
            <button type="button" class="order-update" data-action="save-order-status" data-id="${order.id}">Salvar status</button>
          </div>
        </article>
      `;
    })
    .join('');
}

function populateCredentialForm() {
  setFormValue(refs.credentialsForm, 'new_username', adminState.admin?.username || 'admin');
  setFormValue(refs.credentialsForm, 'new_password', '');
  setFormValue(refs.credentialsForm, 'current_password', '');
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(refs.loginForm);
  const payload = {
    username: formData.get('username')?.toString().trim() || '',
    password: formData.get('password')?.toString() || '',
  };

  try {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Credenciais inválidas.');
    adminState.admin = result.admin;
    showDashboard();
    await loadBootstrap();
    showToast('Login realizado com sucesso.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao entrar.', 'error');
  }
}

async function handleLogout() {
  try {
    const response = await fetch('/api/admin/logout', { method: 'POST' });
    if (!response.ok) throw new Error('Não foi possível sair.');
    adminState.admin = null;
    showLogin();
    showToast('Sessão encerrada.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao sair.', 'error');
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const form = refs.settingsForm;
  const payload = {
    restaurant_name: getFieldValue(form, 'restaurant_name'),
    tagline: getFieldValue(form, 'tagline'),
    city: getFieldValue(form, 'city'),
    address: getFieldValue(form, 'address'),
    phone: getFieldValue(form, 'phone'),
    whatsapp: getFieldValue(form, 'whatsapp'),
    opening_hours: getFieldValue(form, 'opening_hours'),
    delivery_time: getFieldValue(form, 'delivery_time'),
    pickup_time: getFieldValue(form, 'pickup_time'),
    minimum_order: Number(getFieldValue(form, 'minimum_order') || 0),
    free_delivery_from: Number(getFieldValue(form, 'free_delivery_from') || 0),
    service_fee: Number(getFieldValue(form, 'service_fee') || 0),
    banner_title: getFieldValue(form, 'banner_title'),
    banner_subtitle: getFieldValue(form, 'banner_subtitle'),
    hero_badge: getFieldValue(form, 'hero_badge'),
    pix_key: getFieldValue(form, 'pix_key'),
    instagram: getFieldValue(form, 'instagram'),
    footer_note: getFieldValue(form, 'footer_note'),
    primary_color: getFieldValue(form, 'primary_color'),
    secondary_color: getFieldValue(form, 'secondary_color'),
    background_color: getFieldValue(form, 'background_color'),
    text_color: getFieldValue(form, 'text_color'),
    delivery_enabled: isChecked(form, 'delivery_enabled'),
    pickup_enabled: isChecked(form, 'pickup_enabled'),
  };

  try {
    await apiRequest('/api/admin/settings', 'PUT', payload);
    await loadBootstrap();
    showToast('Configurações salvas.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Não foi possível salvar as configurações.', 'error');
  }
}

async function saveCategory(event) {
  event.preventDefault();
  const form = refs.categoryForm;
  const id = getFieldValue(form, 'id');
  const payload = {
    name: getFieldValue(form, 'name'),
    description: getFieldValue(form, 'description'),
    sort_order: Number(getFieldValue(form, 'sort_order') || 0),
    active: isChecked(form, 'active'),
  };
  const endpoint = id ? `/api/admin/categories/${id}` : '/api/admin/categories';
  const method = id ? 'PUT' : 'POST';
  try {
    await apiRequest(endpoint, method, payload);
    resetCategoryForm();
    await loadBootstrap();
    showToast(`Categoria ${id ? 'atualizada' : 'criada'} com sucesso.`, 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao salvar categoria.', 'error');
  }
}

async function saveItem(event) {
  event.preventDefault();
  const form = refs.itemForm;
  const id = getFieldValue(form, 'id');
  const payload = {
    category_id: Number(getFieldValue(form, 'category_id') || 0),
    name: getFieldValue(form, 'name'),
    description: getFieldValue(form, 'description'),
    price: Number(getFieldValue(form, 'price') || 0),
    image_url: getFieldValue(form, 'image_url'),
    featured: isChecked(form, 'featured'),
    available: isChecked(form, 'available'),
    sort_order: Number(getFieldValue(form, 'sort_order') || 0),
    prep_time: Number(getFieldValue(form, 'prep_time') || 0),
  };
  const endpoint = id ? `/api/admin/items/${id}` : '/api/admin/items';
  const method = id ? 'PUT' : 'POST';
  try {
    await apiRequest(endpoint, method, payload);
    resetItemForm();
    await loadBootstrap();
    showToast(`Item ${id ? 'atualizado' : 'criado'} com sucesso.`, 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao salvar item.', 'error');
  }
}

async function saveNeighborhood(event) {
  event.preventDefault();
  const form = refs.neighborhoodForm;
  const id = getFieldValue(form, 'id');
  const payload = {
    name: getFieldValue(form, 'name'),
    fee: Number(getFieldValue(form, 'fee') || 0),
    eta_min: Number(getFieldValue(form, 'eta_min') || 0),
    minimum_order: Number(getFieldValue(form, 'minimum_order') || 0),
    active: isChecked(form, 'active'),
  };
  const endpoint = id ? `/api/admin/neighborhoods/${id}` : '/api/admin/neighborhoods';
  const method = id ? 'PUT' : 'POST';
  try {
    await apiRequest(endpoint, method, payload);
    resetNeighborhoodForm();
    await loadBootstrap();
    showToast(`Bairro ${id ? 'atualizado' : 'criado'} com sucesso.`, 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao salvar bairro.', 'error');
  }
}

async function saveCredentials(event) {
  event.preventDefault();
  const form = refs.credentialsForm;
  const payload = {
    new_username: getFieldValue(form, 'new_username'),
    new_password: getFieldValue(form, 'new_password'),
    current_password: getFieldValue(form, 'current_password'),
  };
  try {
    const result = await apiRequest('/api/admin/credentials', 'PUT', payload);
    adminState.admin = result.admin;
    populateCredentialForm();
    showToast('Acesso administrativo atualizado.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao atualizar acesso.', 'error');
  }
}

function handleCategoryListActions(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const id = Number(button.dataset.id);
  const action = button.dataset.action;
  if (action === 'edit-category') loadCategoryIntoForm(id);
  if (action === 'delete-category') deleteCategory(id);
}

function handleItemListActions(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const id = Number(button.dataset.id);
  const action = button.dataset.action;
  if (action === 'edit-item') loadItemIntoForm(id);
  if (action === 'delete-item') deleteItem(id);
}

function handleNeighborhoodListActions(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const id = Number(button.dataset.id);
  const action = button.dataset.action;
  if (action === 'edit-neighborhood') loadNeighborhoodIntoForm(id);
  if (action === 'delete-neighborhood') deleteNeighborhood(id);
}

function handleOrderActions(event) {
  const button = event.target.closest('[data-action="save-order-status"]');
  if (!button) return;
  const id = Number(button.dataset.id);
  const select = refs.ordersList.querySelector(`[data-order-status-select][data-order-id="${id}"]`);
  if (!select) return;
  updateOrderStatus(id, select.value);
}

function loadCategoryIntoForm(id) {
  const category = adminState.categories.find((entry) => entry.id === id);
  if (!category) return;
  setFormValue(refs.categoryForm, 'id', category.id);
  setFormValue(refs.categoryForm, 'name', category.name);
  setFormValue(refs.categoryForm, 'description', category.description);
  setFormValue(refs.categoryForm, 'sort_order', category.sort_order);
  setCheckboxValue(refs.categoryForm, 'active', category.active);
  activateTab('tab-categories');
  refs.categoryForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function loadItemIntoForm(id) {
  const item = adminState.items.find((entry) => entry.id === id);
  if (!item) return;
  setFormValue(refs.itemForm, 'id', item.id);
  setFormValue(refs.itemForm, 'category_id', item.category_id);
  setFormValue(refs.itemForm, 'name', item.name);
  setFormValue(refs.itemForm, 'description', item.description);
  setFormValue(refs.itemForm, 'price', item.price);
  setFormValue(refs.itemForm, 'image_url', item.image_url);
  setFormValue(refs.itemForm, 'sort_order', item.sort_order);
  setFormValue(refs.itemForm, 'prep_time', item.prep_time);
  setCheckboxValue(refs.itemForm, 'featured', item.featured);
  setCheckboxValue(refs.itemForm, 'available', item.available);
  activateTab('tab-items');
  refs.itemForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function loadNeighborhoodIntoForm(id) {
  const neighborhood = adminState.neighborhoods.find((entry) => entry.id === id);
  if (!neighborhood) return;
  setFormValue(refs.neighborhoodForm, 'id', neighborhood.id);
  setFormValue(refs.neighborhoodForm, 'name', neighborhood.name);
  setFormValue(refs.neighborhoodForm, 'fee', neighborhood.fee);
  setFormValue(refs.neighborhoodForm, 'eta_min', neighborhood.eta_min);
  setFormValue(refs.neighborhoodForm, 'minimum_order', neighborhood.minimum_order);
  setCheckboxValue(refs.neighborhoodForm, 'active', neighborhood.active);
  activateTab('tab-neighborhoods');
  refs.neighborhoodForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetCategoryForm() {
  refs.categoryForm.reset();
  setFormValue(refs.categoryForm, 'id', '');
  setFormValue(refs.categoryForm, 'sort_order', 0);
  setCheckboxValue(refs.categoryForm, 'active', true);
}

function resetItemForm() {
  refs.itemForm.reset();
  setFormValue(refs.itemForm, 'id', '');
  setFormValue(refs.itemForm, 'sort_order', 0);
  setFormValue(refs.itemForm, 'prep_time', 30);
  setCheckboxValue(refs.itemForm, 'available', true);
  setCheckboxValue(refs.itemForm, 'featured', false);
  if (adminState.categories[0]) setFormValue(refs.itemForm, 'category_id', adminState.categories[0].id);
}

function resetNeighborhoodForm() {
  refs.neighborhoodForm.reset();
  setFormValue(refs.neighborhoodForm, 'id', '');
  setFormValue(refs.neighborhoodForm, 'fee', 0);
  setFormValue(refs.neighborhoodForm, 'eta_min', 35);
  setFormValue(refs.neighborhoodForm, 'minimum_order', 0);
  setCheckboxValue(refs.neighborhoodForm, 'active', true);
}

async function deleteCategory(id) {
  const category = adminState.categories.find((entry) => entry.id === id);
  if (!category) return;
  if (!window.confirm(`Excluir a categoria "${category.name}"? Os itens ligados a ela também serão removidos.`)) return;
  try {
    await apiRequest(`/api/admin/categories/${id}`, 'DELETE');
    await loadBootstrap();
    showToast('Categoria removida.', 'success');
    resetCategoryForm();
    resetItemForm();
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao excluir categoria.', 'error');
  }
}

async function deleteItem(id) {
  const item = adminState.items.find((entry) => entry.id === id);
  if (!item) return;
  if (!window.confirm(`Excluir o item "${item.name}"?`)) return;
  try {
    await apiRequest(`/api/admin/items/${id}`, 'DELETE');
    await loadBootstrap();
    showToast('Item removido.', 'success');
    resetItemForm();
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao excluir item.', 'error');
  }
}

async function deleteNeighborhood(id) {
  const neighborhood = adminState.neighborhoods.find((entry) => entry.id === id);
  if (!neighborhood) return;
  if (!window.confirm(`Excluir o bairro "${neighborhood.name}"?`)) return;
  try {
    await apiRequest(`/api/admin/neighborhoods/${id}`, 'DELETE');
    await loadBootstrap();
    showToast('Bairro removido.', 'success');
    resetNeighborhoodForm();
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao excluir bairro.', 'error');
  }
}

async function updateOrderStatus(id, status) {
  try {
    await apiRequest(`/api/admin/orders/${id}/status`, 'PUT', { status });
    await loadBootstrap();
    showToast('Status do pedido atualizado.', 'success');
  } catch (error) {
    console.error(error);
    showToast(error.message || 'Falha ao atualizar pedido.', 'error');
  }
}

async function apiRequest(url, method = 'GET', payload = undefined) {
  const options = { method, headers: {} };
  if (payload !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(result.detail || 'Erro na requisição.');
  }
  return result;
}

function activateTab(id) {
  document.querySelectorAll('.tab-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === id);
  });
  document.querySelectorAll('.tab-content').forEach((panel) => {
    panel.classList.toggle('active', panel.id === id);
  });
}

function setFormValue(form, name, value) {
  const field = form?.elements?.namedItem(name);
  if (!field) return;
  field.value = value ?? '';
}

function setCheckboxValue(form, name, value) {
  const field = form?.elements?.namedItem(name);
  if (!field) return;
  field.checked = Boolean(value);
}

function getFieldValue(form, name) {
  const field = form?.elements?.namedItem(name);
  return field ? field.value : '';
}

function isChecked(form, name) {
  const field = form?.elements?.namedItem(name);
  return Boolean(field?.checked);
}

function currency(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function showToast(message, type = 'default') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  refs.toastRoot.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

// ---------- Variables Globales y Estado ----------
let token = localStorage.getItem("iot_token");
let userRole = localStorage.getItem("iot_role");
let userEmail = localStorage.getItem("iot_email");
let isFirstLogin = false;

// ---------- Normalización de Texto (Insensible a Acentos y Mayúsculas/Minúsculas) ----------
function normalizarTexto(str) {
  if (!str) return '';
  return String(str)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

// ---------- Gestión de Tema Claro / Oscuro ----------
function aplicarTema(tema) {
  const temaFinal = (tema === 'light') ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', temaFinal);
  localStorage.setItem('iot_theme', temaFinal);

  const iconText = temaFinal === 'light' ? '☀️' : '🌙';
  const titleText = temaFinal === 'light' ? 'Cambiar a Modo Oscuro' : 'Cambiar a Modo Claro';

  document.querySelectorAll('.theme-icon-label').forEach((el) => {
    el.textContent = iconText;
  });
  document.querySelectorAll('.btn-toggle-theme').forEach((btn) => {
    btn.setAttribute('title', titleText);
  });
}

function alternarTema() {
  const temaActual = document.documentElement.getAttribute('data-theme') || 'dark';
  const nuevoTema = temaActual === 'light' ? 'dark' : 'light';
  aplicarTema(nuevoTema);
}

function inicializarTema() {
  const temaGuardado = localStorage.getItem('iot_theme') || 
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  aplicarTema(temaGuardado);

  document.querySelectorAll('.btn-toggle-theme').forEach((btn) => {
    btn.addEventListener('click', alternarTema);
  });
}

// Inicializar tema y listeners al cargar el script
inicializarTema();

// ---------- Seguridad: Prevención XSS ----------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sanitizeFragment(html) {
  // Permitir solo <mark> y </mark> del ts_headline de PostgreSQL
  if (!html) return '';
  return escapeHtml(html)
    .replace(/&lt;mark class=&quot;[^&]*&quot;&gt;/g, function(m) {
      // Re-insertar mark tags seguros con clases conocidas
      return m.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"');
    })
    .replace(/&lt;mark&gt;/g, '<mark>')
    .replace(/&lt;\/mark&gt;/g, '</mark>');
}

// ---------- Elementos de Login ----------
const loginModal = document.getElementById("login-modal");
const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");
const btnLogout = document.getElementById("btn-logout");
const userEmailDisplay = document.getElementById("user-email-display");
const userRoleDisplay = document.getElementById("user-role-display");

const tabAsistencia = document.getElementById("tab-asistencia");
const tabTickets = document.getElementById("tab-tickets");
const tabEsquemas = document.getElementById("tab-esquemas");
const tabLaboratorio = document.getElementById("tab-laboratorio");
const containerAccesoTecnico = document.getElementById("container-acceso-tecnico-discreto");
const tabSubir = document.getElementById("tab-subir");
const tabBiblioteca = document.getElementById("tab-biblioteca");
const tabUsuarios = document.getElementById("tab-usuarios");

// ---------- Elementos Cambio Password ----------
const passwordModal = document.getElementById("password-modal");
const passwordForm = document.getElementById("password-form");
const newPassword = document.getElementById("new-password");
const btnSkipPassword = document.getElementById("btn-skip-password");

// ---------- Fetch con Autenticación Automática ----------
async function fetchAuth(url, options = {}) {
  if (!options.headers) options.headers = {};
  if (token) {
    options.headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(url, options);
  
  if (response.status === 401) {
    // Si la sesión expiró o el token fue revocado en el backend
    if (token && userRole !== "invitado") {
      console.warn("Sesión expirada o no autorizada (401) en " + url + ". Cerrando sesión...");
      cerrarSesion();
    }
    throw new Error("No autorizado (401)");
  }
  if (response.status === 403) {
    // 403 es permiso denegado por rol, no debe invalidar la sesión
    throw new Error("Acceso denegado para tu rol actual (403)");
  }
  
  return response;
}

// ---------- Lógica de Autenticación ----------
function verificarSesion() {
  const isInvitado = (userRole === "invitado");
  if ((token && userRole && userEmail) || isInvitado) {
    if (loginModal) {
      loginModal.classList.add("oculto");
      loginModal.style.display = "none";
    }
    if (userEmailDisplay) {
      userEmailDisplay.textContent = isInvitado ? "Invitado (SAT / Manuales)" : userEmail;
      userEmailDisplay.setAttribute("title", isInvitado ? "Modo Invitado" : userEmail);
    }
    if (userRoleDisplay) {
      userRoleDisplay.textContent = isInvitado ? "Rol: Invitado" : ("Rol: " + userRole);
    }
    
    // RBAC: Mostrar u ocultar pestañas según el rol
    if (userRole === "admin" || userRole === "tecnico") {
      if (tabAsistencia) tabAsistencia.classList.remove("hidden");
      if (tabTickets) tabTickets.classList.remove("hidden");
      if (tabEsquemas) tabEsquemas.classList.remove("hidden");
      if (tabLaboratorio) tabLaboratorio.classList.remove("hidden");
      if (containerAccesoTecnico) containerAccesoTecnico.classList.remove("hidden");
    } else if (isInvitado) {
      if (tabAsistencia) tabAsistencia.classList.remove("hidden");
      if (tabTickets) tabTickets.classList.add("hidden");
      if (tabEsquemas) tabEsquemas.classList.remove("hidden");
      if (tabLaboratorio) tabLaboratorio.classList.remove("hidden");
      if (containerAccesoTecnico) containerAccesoTecnico.classList.remove("hidden");
    } else {
      if (tabAsistencia) tabAsistencia.classList.add("hidden");
      if (tabTickets) tabTickets.classList.add("hidden");
      if (tabEsquemas) tabEsquemas.classList.add("hidden");
      if (tabLaboratorio) tabLaboratorio.classList.add("hidden");
      if (containerAccesoTecnico) containerAccesoTecnico.classList.add("hidden");
    }

    if (userRole === "admin") {
      if (tabSubir) tabSubir.classList.remove("hidden");
      if (tabBiblioteca) tabBiblioteca.classList.remove("hidden");
      if (tabUsuarios) tabUsuarios.classList.remove("hidden");
    } else {
      if (tabSubir) tabSubir.classList.add("hidden");
      if (tabBiblioteca) tabBiblioteca.classList.add("hidden");
      if (tabUsuarios) tabUsuarios.classList.add("hidden");
    }
    
    if (isFirstLogin && passwordModal && !isInvitado) {
      passwordModal.classList.remove("hidden");
    }

    // Validar proactivamente que el token siga siendo admitido por el servidor
    if (token && !isInvitado) {
      fetch("/api/me", { headers: { "Authorization": `Bearer ${token}` } })
        .then((r) => {
          if (r.status === 401) {
            console.warn("Token caducado en el servidor. Reabriendo pantalla de acceso.");
            cerrarSesion();
          }
        })
        .catch(() => {});
    }

    // Cargar datos iniciales con protección ante fallos
    try {
      if (typeof cargarOpcionesFiltro === "function") cargarOpcionesFiltro();
    } catch (e) {
      console.error("Error al cargar opciones de filtro:", e);
    }
    try {
      if (typeof cargarSugerencias === "function") cargarSugerencias();
    } catch (e) {
      console.error("Error al cargar sugerencias:", e);
    }

    // Inicializar módulo SAT y stats para actualizar el badge del menú
    if (userRole === "admin" || userRole === "tecnico") {
      try {
        if (typeof inicializarModuloEsquemas === "function") inicializarModuloEsquemas();
      } catch (e) {
        console.error("Error al inicializar esquemas/stats:", e);
      }
    } else if (isInvitado) {
      try {
        if (typeof inicializarModuloEsquemas === "function") inicializarModuloEsquemas();
      } catch (e) {
        console.error("Error al inicializar esquemas modo invitado:", e);
      }
    }
  } else {
    if (loginModal) {
      loginModal.classList.remove("oculto");
      loginModal.style.display = "flex";
    }
    if (containerAccesoTecnico) containerAccesoTecnico.classList.add("hidden");
  }
}

function cerrarSesion() {
  localStorage.removeItem("iot_token");
  localStorage.removeItem("iot_role");
  localStorage.removeItem("iot_email");
  token = null;
  userRole = null;
  userEmail = null;
  verificarSesion();
}

async function realizarLogin(userVal, passVal) {
  if (loginError) {
    loginError.classList.add("hidden");
    loginError.textContent = "";
  }
  
  const user = (userVal || "").trim();
  const pass = (passVal || "").trim();
  
  if (!user || !pass) {
    if (loginError) {
      loginError.textContent = "Por favor, introduce usuario/email y contraseña.";
      loginError.classList.remove("hidden");
    }
    return;
  }
  
  const btnLoginSubmit = document.getElementById("btn-login-submit");
  const origBtnHtml = btnLoginSubmit ? btnLoginSubmit.innerHTML : "<span>Iniciar Sesión</span>";
  if (btnLoginSubmit) {
    btnLoginSubmit.disabled = true;
    btnLoginSubmit.innerHTML = `<span>⏳ Accediendo al sistema...</span>`;
  }
  
  const formData = new URLSearchParams();
  formData.append("username", user);
  formData.append("password", pass);
  
  try {
    const resp = await fetch("/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });
    
    if (!resp.ok) {
      const errorData = await resp.json().catch(() => ({}));
      throw new Error(errorData.detail || "Usuario o contraseña incorrectos");
    }
    
    const data = await resp.json();
    token = data.access_token;
    userRole = data.role;
    userEmail = data.email;
    
    localStorage.setItem("iot_token", token);
    localStorage.setItem("iot_role", userRole);
    localStorage.setItem("iot_email", userEmail);
    
    if (loginEmail) loginEmail.value = user;
    if (loginPassword) loginPassword.value = pass;

    if (loginModal) {
      loginModal.classList.add("oculto");
      loginModal.style.display = "none";
    }

    // Revisar si es el primer login
    try {
      const respMe = await fetchAuth("/api/me");
      if (respMe.ok) {
        const meData = await respMe.json();
        if (meData.is_first_login && passwordModal) {
          passwordModal.classList.remove("hidden");
        }
      }
    } catch(e) {
      console.warn("No se pudo verificar primer login:", e);
    }

    verificarSesion();
    
  } catch (err) {
    if (loginError) {
      loginError.textContent = err.message || "Error al iniciar sesión";
      loginError.classList.remove("hidden");
    }
  } finally {
    if (btnLoginSubmit) {
      btnLoginSubmit.disabled = false;
      btnLoginSubmit.innerHTML = origBtnHtml;
    }
  }
}

if (loginForm) {
  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    realizarLogin(loginEmail ? loginEmail.value : "", loginPassword ? loginPassword.value : "");
  });
}

// Botones de Acceso Rápido 1-Clic
const btnQuickLoginAdmin = document.getElementById("btn-quick-login-admin");
const btnQuickLoginTecnico = document.getElementById("btn-quick-login-tecnico");
const btnLoginInvitado = document.getElementById("btn-login-invitado");
const btnCerrarLogin = document.getElementById("btn-cerrar-login");

if (btnQuickLoginAdmin) {
  btnQuickLoginAdmin.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (loginEmail) loginEmail.value = "admin";
    if (loginPassword) loginPassword.value = "admin123";
    realizarLogin("admin", "admin123");
  });
}

if (btnQuickLoginTecnico) {
  btnQuickLoginTecnico.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (loginEmail) loginEmail.value = "tecnico";
    if (loginPassword) loginPassword.value = "tecnico123";
    realizarLogin("tecnico", "tecnico123");
  });
}

if (btnLoginInvitado) {
  btnLoginInvitado.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    userRole = "invitado";
    userEmail = "invitado@iotfenster.es";
    token = null;
    localStorage.setItem("iot_role", "invitado");
    localStorage.setItem("iot_email", userEmail);
    localStorage.removeItem("iot_token");
    if (loginModal) {
      loginModal.classList.add("oculto");
      loginModal.style.display = "none";
    }
    verificarSesion();
  });
}

if (btnCerrarLogin) {
  btnCerrarLogin.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (loginModal) {
      loginModal.classList.add("oculto");
      loginModal.style.display = "none";
    }
    if (!token && !userRole) {
      userRole = "invitado";
      userEmail = "invitado@iotfenster.es";
      localStorage.setItem("iot_role", "invitado");
      localStorage.setItem("iot_email", userEmail);
      verificarSesion();
    }
  });
}

if (btnSkipPassword) {
  btnSkipPassword.addEventListener("click", () => {
    if (passwordModal) passwordModal.classList.add("hidden");
    isFirstLogin = false;
  });
}

if (passwordForm) {
  passwordForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pwd = newPassword ? newPassword.value : "";
    if (!pwd) return;
    try {
      const resp = await fetchAuth("/api/usuarios/me/password", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: pwd })
      });
      if (resp.ok) {
        if (passwordModal) passwordModal.classList.add("hidden");
        isFirstLogin = false;
        alert("Contraseña cambiada con éxito.");
      } else {
        alert("Error al cambiar contraseña.");
      }
    } catch (err) {
      alert("Error de red.");
    }
  });
}

if (btnLogout) {
  btnLogout.addEventListener("click", cerrarSesion);
}


// Iniciar app verificando sesión
verificarSesion();

// ---------- Navegación entre pestañas y vistas ----------
const pestanas = document.querySelectorAll(".pestana");
const vistas = {
  buscar: document.getElementById("vista-buscar"),
  asistencia: document.getElementById("vista-asistencia"),
  tickets: document.getElementById("vista-tickets"),
  esquemas: document.getElementById("vista-esquemas"),
  laboratorio: document.getElementById("vista-laboratorio"),
  subir: document.getElementById("vista-subir"),
  biblioteca: document.getElementById("vista-biblioteca"),
  usuarios: document.getElementById("vista-usuarios"),
};

function abrirVistaDirecta(nombreVista) {
  window.abrirVistaDirecta = abrirVistaDirecta;
  pestanas.forEach((b) => b.classList.remove("activa"));
  Object.values(vistas).forEach((v) => {
    if (v) v.classList.remove("vista-activa");
  });

  const tabBtn = document.querySelector(`.pestana[data-vista="${nombreVista}"]`);
  if (tabBtn) tabBtn.classList.add("activa");

  if (vistas[nombreVista]) {
    vistas[nombreVista].classList.add("vista-activa");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (nombreVista === "buscar" && !inputBusqueda.value.trim()) {
    restablecerVistaBusqueda();
  }
  if (nombreVista === "asistencia") {
    inicializarModuloEsquemas();
    if (typeof window.ejecutarEvaluacionAsistencia === "function") {
      window.ejecutarEvaluacionAsistencia();
    }
  }
  if (nombreVista === "tickets") {
    inicializarModuloEsquemas();
    if (typeof window.cargarTicketsSAT === "function") {
      window.cargarTicketsSAT();
    }
    if (typeof window.cargarStatsTickets === "function") {
      window.cargarStatsTickets();
    }
  }
  if (nombreVista === "esquemas") {
    inicializarModuloEsquemas();
    const subtabSim = document.getElementById("subtab-btn-simulador");
    if (subtabSim) subtabSim.click();
  }
  if (nombreVista === "laboratorio") {
    inicializarLaboratorioIntegral();
  }
  if (nombreVista === "biblioteca" && userRole === "admin") {
    cargarBiblioteca();
    cargarBibliotecaVideos();
  }
  if (nombreVista === "usuarios" && userRole === "admin") cargarUsuarios();
}

pestanas.forEach((btn) => {
  btn.addEventListener("click", () => {
    abrirVistaDirecta(btn.dataset.vista);
  });
});

// ---------- Control del Acceso Técnico Discreto (Simulador y Laboratorio Ocultos) ----------
const btnToggleEsquemasOcultos = document.getElementById("btn-toggle-esquemas-ocultos");
const popoverEsquemasOcultos = document.getElementById("popover-esquemas-ocultos");

if (btnToggleEsquemasOcultos && popoverEsquemasOcultos) {
  btnToggleEsquemasOcultos.addEventListener("click", (e) => {
    e.stopPropagation();
    popoverEsquemasOcultos.classList.toggle("hidden");
  });

  // Cerrar popover al hacer clic fuera
  document.addEventListener("click", (e) => {
    if (!popoverEsquemasOcultos.classList.contains("hidden")) {
      if (!popoverEsquemasOcultos.contains(e.target) && e.target !== btnToggleEsquemasOcultos) {
        popoverEsquemasOcultos.classList.add("hidden");
      }
    }
  });

  // Botones para saltar a esquemas o laboratorio desde el popover
  document.querySelectorAll(".btn-ir-vista-oculta").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetVista = btn.dataset.target;
      popoverEsquemasOcultos.classList.add("hidden");
      abrirVistaDirecta(targetVista);
    });
  });
}

// Botones Volver al Buscador en vistas técnicas
document.querySelectorAll(".btn-volver-buscador").forEach((btn) => {
  btn.addEventListener("click", () => {
    abrirVistaDirecta("buscar");
  });
});

// ---------- Buscar ----------
const inputBusqueda = document.getElementById("input-busqueda");
const btnBuscar = document.getElementById("btn-buscar");
const btnLimpiarBusqueda = document.getElementById("btn-limpiar-busqueda");
const estadoBusqueda = document.getElementById("estado-busqueda");
const contenedorResultados = document.getElementById("resultados");
const filtroDispositivo = document.getElementById("filtro-dispositivo");
const filtroCategoria = document.getElementById("filtro-categoria");
const listaSugerencias = document.getElementById("lista-sugerencias");

// Elementos de Temas Frecuentes / Chips de Etiquetas
const contenedorChipsEtiquetas = document.getElementById("contenedor-chips-etiquetas");
const btnToggleTodosTags = document.getElementById("btn-toggle-todos-tags");
const labelToggleTags = document.getElementById("label-toggle-tags");
const iconoToggleTags = document.getElementById("icono-toggle-tags");
const panelTodosTags = document.getElementById("panel-todos-tags");
const listaChipsTagsTodos = document.getElementById("lista-chips-tags-todos");

// Temas técnicos prioritarios para el soporte SAT (documentación de averías, conectividad y dispositivos)
const TAGS_PRIORITARIOS = [
  "wifi", "cgnat", "problemas", "modo candado", "hard reset", 
  "pulsador insensible", "cable cortado", "rele suena", "motor roto",
  "finales de carrera", "ruido electrico", "se mueven solas", "invertir controles",
  "multicast", "punto a punto", "digi plus", "aisla clientes", "modo fabrica",
  "connect-1", "connect-2", "c-wall", "c-pulsar", "connect evo", "motores", "videos"
];

let sugerenciasDisponibles = { nombres: [], dispositivos: [], categorias: [] };

async function cargarOpcionesFiltro() {
  if (!token) return;
  try {
    const resp = await fetchAuth("/api/filtros");
    if (!resp || !resp.ok) return;
    const data = await resp.json();
    filtroDispositivo.innerHTML = `<option value="">Todos los dispositivos</option>` +
      data.dispositivos.map((d) => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join("");
    filtroCategoria.innerHTML = `<option value="">Todas las categorías</option>` +
      data.categorias.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
    
    // Renderizar chips de etiquetas para soporte
    renderizarChipsEtiquetas(data.etiquetas || []);
  } catch (e) {}
}

function renderizarChipsEtiquetas(etiquetas) {
  const contenedor = document.getElementById("lista-chips-tags");
  if (!contenedor) return;

  const rawTags = (etiquetas && etiquetas.length > 0)
    ? etiquetas
    : ["wifi", "cgnat", "problemas", "reset", "modo fabrica", "pulsador", "motores", "candado"];

  // Limpiar y deduplicar etiquetas
  const tagsUnicos = Array.from(new Set(
    rawTags.map(t => String(t).trim().toLowerCase()).filter(t => t.length > 1)
  ));

  const destacados = [];
  const restantes = [];

  // Priorizar tags conocidos clave
  TAGS_PRIORITARIOS.forEach((p) => {
    const match = tagsUnicos.find((t) => t === p || t === p.replace("-", " "));
    if (match && !destacados.includes(match)) {
      destacados.push(match);
    }
  });

  // Completar hasta 14-16 destacados si hacen falta
  tagsUnicos.forEach((t) => {
    if (!destacados.includes(t)) {
      if (destacados.length < 15) {
        destacados.push(t);
      } else {
        restantes.push(t);
      }
    }
  });
  restantes.sort((a, b) => a.localeCompare(b));

  const renderizarBotonTag = (tag) => `
    <button type="button" class="chip-tag bg-iot-panel hover:bg-iot-teal hover:text-white border border-iot-border hover:border-iot-teal text-iot-textSec px-2.5 py-1 rounded-lg text-xs font-mono transition-all flex items-center gap-1 shadow-sm active:scale-95 cursor-pointer" data-tag="${escapeHtml(tag)}">
      <span>#${escapeHtml(tag)}</span>
    </button>
  `;

  // Renderizar destacados compactos
  contenedor.innerHTML = destacados.map(renderizarBotonTag).join("");

  // Manejar panel colapsable de tags restantes
  if (panelTodosTags && listaChipsTagsTodos && btnToggleTodosTags) {
    if (restantes.length > 0) {
      listaChipsTagsTodos.innerHTML = restantes.map(renderizarBotonTag).join("");
      if (labelToggleTags) labelToggleTags.textContent = `Ver todos (${tagsUnicos.length})`;
      btnToggleTodosTags.classList.remove("hidden");
    } else {
      btnToggleTodosTags.classList.add("hidden");
      panelTodosTags.classList.add("hidden");
    }
  }

  // Asignar eventos de clic a todos los chips
  document.querySelectorAll("#contenedor-chips-etiquetas .chip-tag").forEach((btn) => {
    btn.addEventListener("click", () => {
      inputBusqueda.value = btn.dataset.tag;
      if (btnLimpiarBusqueda) btnLimpiarBusqueda.classList.remove("hidden");
      buscar();
    });
  });
}

// Event listener para desplegar / ocultar panel completo de tags
if (btnToggleTodosTags && panelTodosTags) {
  btnToggleTodosTags.addEventListener("click", () => {
    const estaOculto = panelTodosTags.classList.contains("hidden");
    if (estaOculto) {
      panelTodosTags.classList.remove("hidden");
      if (labelToggleTags) labelToggleTags.textContent = "Mostrar menos";
      if (iconoToggleTags) iconoToggleTags.textContent = "▲";
    } else {
      panelTodosTags.classList.add("hidden");
      const total = document.querySelectorAll("#contenedor-chips-etiquetas .chip-tag").length;
      if (labelToggleTags) labelToggleTags.textContent = `Ver todos (${total})`;
      if (iconoToggleTags) iconoToggleTags.textContent = "▼";
    }
  });
}

async function cargarSugerencias() {
  if (!token) return;
  try {
    const resp = await fetchAuth("/api/sugerencias");
    if (!resp || !resp.ok) return;
    sugerenciasDisponibles = await resp.json();
  } catch (e) {}
}

filtroDispositivo.addEventListener("change", buscar);
filtroCategoria.addEventListener("change", buscar);

function mostrarSugerencias(texto) {
  if (!texto.trim()) {
    listaSugerencias.classList.remove("visible");
    return;
  }
  const textoNorm = normalizarTexto(texto);
  const candidatos = [];

  sugerenciasDisponibles.nombres.forEach((n) => {
    if (normalizarTexto(n).includes(textoNorm)) candidatos.push({ texto: n, tipo: "Manual" });
  });
  sugerenciasDisponibles.dispositivos.forEach((d) => {
    if (normalizarTexto(d).includes(textoNorm)) candidatos.push({ texto: d, tipo: "Dispositivo" });
  });
  sugerenciasDisponibles.categorias.forEach((c) => {
    if (normalizarTexto(c).includes(textoNorm)) candidatos.push({ texto: c, tipo: "Categoría" });
  });

  const unicos = candidatos.filter((c, i) => candidatos.findIndex((x) => x.texto === c.texto) === i).slice(0, 6);

  if (unicos.length === 0) {
    listaSugerencias.classList.remove("visible");
    return;
  }

  listaSugerencias.innerHTML = unicos
    .map((c) => `<div class="item-sugerencia px-4 py-3 cursor-pointer text-sm border-b border-iot-border last:border-0 hover:bg-iot-hover flex items-center justify-between" data-texto="${escapeHtml(c.texto)}">
      <span class="flex items-center gap-2">📄 ${escapeHtml(c.texto)}</span>
      <span class="tipo-sugerencia text-xs text-iot-tealLight bg-iot-teal/10 px-2 py-0.5 rounded-full font-mono">${escapeHtml(c.tipo)}</span>
    </div>`)
    .join("");
  listaSugerencias.classList.add("visible");

  listaSugerencias.querySelectorAll(".item-sugerencia").forEach((el) => {
    el.addEventListener("click", () => {
      inputBusqueda.value = el.dataset.texto;
      listaSugerencias.classList.remove("visible");
      buscar();
    });
  });
}

inputBusqueda.addEventListener("input", () => mostrarSugerencias(inputBusqueda.value));
document.addEventListener("click", (e) => {
  if (!e.target.closest(".envoltorio-input")) listaSugerencias.classList.remove("visible");
});

// ---------- Reproductor de YouTube Modal ----------
const modalReproductorVideo = document.getElementById("modal-reproductor-video");
const btnCerrarModalPlayer = document.getElementById("btn-cerrar-modal-player");
const iframePlayer = document.getElementById("iframe-youtube-player");
const playerTituloVideo = document.getElementById("player-titulo-video");
const playerCanalVideo = document.getElementById("player-canal-video");
const playerTiempoChip = document.getElementById("player-tiempo-chip");
const playerLinkExterno = document.getElementById("player-link-externo");

function abrirReproductorVideo(titulo, urlEmbed, canal, urlWatch, tiempoFormateado) {
  if (!modalReproductorVideo) return;
  playerTituloVideo.textContent = titulo;
  playerCanalVideo.textContent = canal ? `Canal: ${canal}` : "Canal Oficial";
  playerTiempoChip.textContent = `⏱️ ${tiempoFormateado || '00:00'}`;
  playerLinkExterno.href = urlWatch || "#";
  // Solo permitir embeds de YouTube
  if (urlEmbed && (urlEmbed.startsWith('https://www.youtube.com/embed/') || urlEmbed.startsWith('https://youtube.com/embed/'))) {
    iframePlayer.src = urlEmbed;
  }
  modalReproductorVideo.classList.remove("hidden");
}

function cerrarReproductorVideo() {
  if (!modalReproductorVideo) return;
  iframePlayer.src = "";
  modalReproductorVideo.classList.add("hidden");
}

if (btnCerrarModalPlayer) {
  btnCerrarModalPlayer.addEventListener("click", cerrarReproductorVideo);
}
if (modalReproductorVideo) {
  modalReproductorVideo.addEventListener("click", (e) => {
    if (e.target === modalReproductorVideo) cerrarReproductorVideo();
  });
}

// ---------- Visor PDF Integrado (Deep Linking) ----------
const modalVisorPdf = document.getElementById("modal-visor-pdf");
const btnCerrarModalVisor = document.getElementById("btn-cerrar-modal-visor");
const iframeVisorPdf = document.getElementById("iframe-visor-pdf");
const visorTituloManual = document.getElementById("visor-titulo-manual");
const visorDispositivoChip = document.getElementById("visor-dispositivo-chip");
const visorPaginaChip = document.getElementById("visor-pagina-chip");
const visorRbacChip = document.getElementById("visor-rbac-chip");
const visorBtnPackObra = document.getElementById("visor-btn-pack-obra");
const visorBtnDescargar = document.getElementById("visor-btn-descargar");
const visorLinkExterno = document.getElementById("visor-link-externo");
const visorCargando = document.getElementById("visor-cargando");
const visorInfoArchivo = document.getElementById("visor-info-archivo");

let dispositivoActivoEnVisor = "";

window.abrirVisorPDF = abrirVisorPDF;
function abrirVisorPDF(nombre, archivo, pagina = 1, paginasTotales = 1, dispositivo = "", nivelAcceso = "publico") {
  if (!modalVisorPdf) return;
  if (!archivo || archivo === "undefined") {
    console.error("No se puede abrir el visor PDF sin un nombre de archivo válido:", { nombre, archivo });
    return;
  }
  const tkn = localStorage.getItem("iot_token") || "";
  dispositivoActivoEnVisor = dispositivo || "";

  if (visorTituloManual) visorTituloManual.textContent = nombre || archivo;
  if (visorPaginaChip) visorPaginaChip.textContent = `Pág. ${pagina} / ${paginasTotales || '?'}`;
  if (visorInfoArchivo) visorInfoArchivo.textContent = archivo;

  const esComercialRestringido = (userRole === "comercial" && nivelAcceso === "tecnico");

  if (visorRbacChip) {
    if (nivelAcceso === "tecnico") {
      visorRbacChip.textContent = "🔒 Solo Técnico";
      visorRbacChip.classList.remove("hidden");
    } else {
      visorRbacChip.classList.add("hidden");
    }
  }

  if (visorDispositivoChip) {
    if (dispositivo) {
      visorDispositivoChip.textContent = dispositivo;
      visorDispositivoChip.classList.remove("hidden");
    } else {
      visorDispositivoChip.classList.add("hidden");
    }
  }

  if (visorBtnPackObra) {
    if (dispositivo && !esComercialRestringido) {
      visorBtnPackObra.classList.remove("hidden");
    } else {
      visorBtnPackObra.classList.add("hidden");
    }
  }

  const urlPdfRaw = `/manuales/${encodeURIComponent(archivo)}?token=${tkn}`;
  const urlPdfConHash = `${urlPdfRaw}#page=${pagina}&zoom=page-width`;

  if (visorBtnDescargar) {
    if (esComercialRestringido) {
      visorBtnDescargar.classList.add("opacity-50", "pointer-events-none");
      visorBtnDescargar.removeAttribute("href");
      visorBtnDescargar.title = "Descarga no permitida para rol Comercial (Documento Técnico)";
    } else {
      visorBtnDescargar.classList.remove("opacity-50", "pointer-events-none");
      visorBtnDescargar.href = urlPdfRaw;
      visorBtnDescargar.removeAttribute("title");
    }
  }
  if (visorLinkExterno) visorLinkExterno.href = urlPdfConHash;

  if (visorCargando) {
    visorCargando.style.opacity = "1";
    visorCargando.classList.remove("hidden");
  }

  if (iframeVisorPdf) {
    iframeVisorPdf.onload = () => {
      if (visorCargando) {
        visorCargando.style.opacity = "0";
        setTimeout(() => visorCargando.classList.add("hidden"), 250);
      }
    };
    iframeVisorPdf.src = urlPdfConHash;
  }

  modalVisorPdf.classList.remove("hidden");
}

function cerrarVisorPDF() {
  if (!modalVisorPdf) return;
  if (iframeVisorPdf) iframeVisorPdf.src = "";
  modalVisorPdf.classList.add("hidden");
}

if (btnCerrarModalVisor) {
  btnCerrarModalVisor.addEventListener("click", cerrarVisorPDF);
}
if (modalVisorPdf) {
  modalVisorPdf.addEventListener("click", (e) => {
    if (e.target === modalVisorPdf) cerrarVisorPDF();
  });
}
if (visorBtnPackObra) {
  visorBtnPackObra.addEventListener("click", () => {
    if (dispositivoActivoEnVisor) descargarPackObra(dispositivoActivoEnVisor, visorBtnPackObra);
  });
}

// Atajo global ESC para cerrar modales
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (modalVisorPdf && !modalVisorPdf.classList.contains("hidden")) cerrarVisorPDF();
    if (modalReproductorVideo && !modalReproductorVideo.classList.contains("hidden")) cerrarReproductorVideo();
    if (modalPackObra && !modalPackObra.classList.contains("hidden")) cerrarModalPackObra();
  }
});

// ---------- Pack de Obra (ZIP por Dispositivo) ----------
const modalPackObra = document.getElementById("modal-pack-obra");
const btnAbrirModalPackObra = document.getElementById("btn-abrir-modal-pack-obra");
const btnCerrarModalPack = document.getElementById("btn-cerrar-modal-pack");
const listaPacksDispositivos = document.getElementById("lista-packs-dispositivos");
const bannerPackObra = document.getElementById("banner-pack-obra");
const bannerPackDispositivo = document.getElementById("banner-pack-dispositivo");
const btnBannerDescargarPack = document.getElementById("btn-banner-descargar-pack");

let dispositivoBannerActivo = "";

function descargarPackObra(dispositivo, btnElement = null) {
  const tkn = localStorage.getItem("iot_token") || "";
  const textoOriginal = btnElement ? btnElement.innerHTML : "";
  if (btnElement) {
    btnElement.innerHTML = `<span>⏳</span> Generando ZIP...`;
    btnElement.disabled = true;
  }

  const url = `/api/dispositivos/${encodeURIComponent(dispositivo)}/pack?token=${tkn}`;
  const link = document.createElement("a");
  link.href = url;
  link.download = `Pack_Obra_${dispositivo}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  setTimeout(() => {
    if (btnElement) {
      btnElement.innerHTML = `<span>✅</span> ¡Descargado!`;
      setTimeout(() => {
        btnElement.innerHTML = textoOriginal;
        btnElement.disabled = false;
      }, 2000);
    }
  }, 1500);
}

async function abrirModalPackObra() {
  if (!modalPackObra) return;
  modalPackObra.classList.remove("hidden");
  if (!listaPacksDispositivos) return;

  listaPacksDispositivos.innerHTML = `
    <div class="p-8 text-center text-xs text-iot-textSec font-mono">
      <div class="w-6 h-6 border-2 border-iot-teal border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
      Cargando catálogo de dispositivos...
    </div>
  `;

  try {
    const resp = await fetchAuth("/api/dispositivos");
    const dispositivos = await resp.json();

    if (!dispositivos || dispositivos.length === 0) {
      listaPacksDispositivos.innerHTML = `
        <div class="p-6 text-center text-xs text-iot-textSec font-mono">
          No hay dispositivos registrados con documentación técnica aún.
        </div>
      `;
      return;
    }

    listaPacksDispositivos.innerHTML = "";
    dispositivos.forEach(d => {
      const item = document.createElement("div");
      item.className = "flex items-center justify-between gap-4 p-4 rounded-xl bg-iot-bg/60 border border-iot-border hover:border-iot-teal/40 transition-all";
      item.innerHTML = `
        <div class="flex items-center gap-3 min-w-0">
          <span class="text-2xl shrink-0">📦</span>
          <div class="min-w-0">
            <h4 class="font-sora font-bold text-sm text-iot-text">${escapeHtml(d.dispositivo)}</h4>
            <div class="flex items-center gap-2 text-xs font-mono text-iot-textSec mt-0.5">
              <span>📄 ${d.manuales} Manual${d.manuales === 1 ? '' : 'es'}</span>
              <span>·</span>
              <span>🎥 ${d.videos} Video${d.videos === 1 ? '' : 's'}</span>
            </div>
          </div>
        </div>
        <button type="button" class="btn-descargar-pack-item shrink-0 bg-iot-teal hover:bg-iot-tealLight text-white px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow active:scale-95">
          <span>📥</span> Descargar ZIP
        </button>
      `;

      const btnDescargar = item.querySelector(".btn-descargar-pack-item");
      btnDescargar.addEventListener("click", () => descargarPackObra(d.dispositivo, btnDescargar));

      listaPacksDispositivos.appendChild(item);
    });
  } catch (err) {
    listaPacksDispositivos.innerHTML = `
      <div class="p-4 text-center text-xs text-red-400 font-mono">
        Error al cargar dispositivos: ${escapeHtml(err.message)}
      </div>
    `;
  }
}

function cerrarModalPackObra() {
  if (!modalPackObra) return;
  modalPackObra.classList.add("hidden");
}

if (btnAbrirModalPackObra) {
  btnAbrirModalPackObra.addEventListener("click", abrirModalPackObra);
}
if (btnCerrarModalPack) {
  btnCerrarModalPack.addEventListener("click", cerrarModalPackObra);
}
if (modalPackObra) {
  modalPackObra.addEventListener("click", (e) => {
    if (e.target === modalPackObra) cerrarModalPackObra();
  });
}
if (btnBannerDescargarPack) {
  btnBannerDescargarPack.addEventListener("click", () => {
    if (dispositivoBannerActivo) descargarPackObra(dispositivoBannerActivo, btnBannerDescargarPack);
  });
}

// ---------- Filtros de Tipo de Resultado (Todos / Manuales / Videos) ----------
let ultimosResultados = {
  todos: [],
  manuales: [],
  videos: []
};
let filtroTipoActivo = "todos";

const filtrosTipoResultado = document.getElementById("filtros-tipo-resultado");
const btnFiltroTodos = document.getElementById("btn-filtro-todos");
const btnFiltroManuales = document.getElementById("btn-filtro-manuales");
const btnFiltroVideos = document.getElementById("btn-filtro-videos");
const contadorTodos = document.getElementById("contador-todos");
const contadorManuales = document.getElementById("contador-manuales");
const contadorVideos = document.getElementById("contador-videos");

function activarFiltroTipo(tipo) {
  filtroTipoActivo = tipo;
  const botones = [
    { btn: btnFiltroTodos, tipo: "todos" },
    { btn: btnFiltroManuales, tipo: "manuales" },
    { btn: btnFiltroVideos, tipo: "videos" }
  ];

  botones.forEach(({ btn, tipo: bTipo }) => {
    if (!btn) return;
    if (bTipo === tipo) {
      btn.className = "btn-tipo-filtro px-4 py-1.5 rounded-full text-xs font-semibold bg-iot-teal text-white shadow transition-all active:scale-95";
    } else {
      btn.className = "btn-tipo-filtro px-4 py-1.5 rounded-full text-xs font-semibold bg-iot-panel text-iot-textSec hover:text-white border border-iot-border transition-all active:scale-95";
    }
  });

  renderizarResultados(ultimosResultados[tipo] || []);
}

if (btnFiltroTodos) btnFiltroTodos.addEventListener("click", () => activarFiltroTipo("todos"));
if (btnFiltroManuales) btnFiltroManuales.addEventListener("click", () => activarFiltroTipo("manuales"));
if (btnFiltroVideos) btnFiltroVideos.addEventListener("click", () => activarFiltroTipo("videos"));

function renderizarResultados(lista) {
  contenedorResultados.innerHTML = "";
  if (!lista || lista.length === 0) {
    contenedorResultados.innerHTML = `<div class="p-8 text-center text-iot-textSec glass-panel rounded-2xl border border-iot-border">No hay resultados en esta pestaña.</div>`;
    return;
  }

  lista.forEach((r) => {
    const tarjeta = document.createElement("div");
    let badgePrivacidad = "";
    let tagsBadges = "";

    if (r.tipo === "video") {
      tarjeta.className = "tarjeta-resultado glass-panel rounded-2xl p-6 shadow-xl hover:-translate-y-1 hover:shadow-red-500/10 transition-all flex flex-col md:flex-row gap-5 border border-red-500/20";
      
      badgePrivacidad = r.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Técnico</span>`
        : '';

      tagsBadges = r.etiquetas
        ? r.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="etiqueta bg-red-500/10 border border-red-500/30 text-red-300 px-2 py-0.5 rounded-md shadow-sm">🏷️ ${escapeHtml(t)}</span>`).join(' ')
        : '';

      tarjeta.innerHTML = `
        <div class="relative shrink-0 w-full md:w-56 h-32 rounded-xl overflow-hidden border border-iot-border bg-black group cursor-pointer video-thumb-trigger">
          <img class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 opacity-90 group-hover:opacity-100" src="${escapeHtml(r.miniatura)}" alt="${escapeHtml(r.titulo)}" loading="lazy">
          <div class="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-colors flex items-center justify-center">
            <div class="w-10 h-10 rounded-full bg-red-600/90 text-white flex items-center justify-center shadow-lg group-hover:scale-110 group-hover:bg-red-500 transition-all">
              <svg class="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </div>
          </div>
          <span class="absolute bottom-2 right-2 bg-black/80 text-white text-[11px] font-mono px-1.5 py-0.5 rounded font-semibold">
            ⏱️ ${r.tiempo_formateado}
          </span>
        </div>
        <div class="resultado-contenido flex-1 min-w-0 flex flex-col justify-between">
          <div>
            <div class="resultado-cabecera flex justify-between items-baseline gap-3 flex-wrap mb-2">
              <div class="font-sora font-bold text-lg text-red-400 hover:text-red-300 transition-colors flex items-center gap-2 cursor-pointer video-title-trigger">
                <span>▶ ${escapeHtml(r.titulo)}</span>
              </div>
              </div>
              <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
                <span class="bg-red-600/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded text-xs font-semibold">🎥 Video Tutorial</span>
                ${badgePrivacidad}
                ${r.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(r.dispositivo)}</span>` : ""}
                ${r.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(r.categoria)}</span>` : ""}
                ${tagsBadges}
              </div>
            </div>
            <div class="resultado-fragmento text-sm text-iot-textSec leading-relaxed bg-iot-bg/50 p-3.5 rounded-xl border border-iot-border/50 mb-3">
              <span class="text-xs text-iot-tealLight font-mono block mb-1">🗣️ Explicado en el video (minuto ${r.tiempo_formateado}):</span>
              ${sanitizeFragment(r.fragmento.replace(/<mark>/g, '<mark class="bg-red-500/30 text-white font-semibold rounded px-1">'))}
            </div>
          </div>
          <div class="flex items-center justify-between text-xs pt-1">
            <span class="text-iot-textSec font-mono">Canal: <strong class="text-iot-text">${escapeHtml(r.canal || 'MySmartWindow')}</strong></span>
            <div class="flex items-center gap-3">
              <button type="button" class="btn-ver-video bg-red-600 hover:bg-red-500 text-white px-3 py-1.5 rounded-lg font-sora font-semibold transition-all shadow-md flex items-center gap-1.5 cursor-pointer">
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                Ver Explicación (${r.tiempo_formateado})
              </button>
              <a href="${r.url}" target="_blank" class="text-iot-textSec hover:text-white font-mono flex items-center gap-1">
                YouTube ↗
              </a>
            </div>
          </div>
        </div>
      `;

      const lanzarPlayer = () => abrirReproductorVideo(r.titulo, r.url_embed, r.canal, r.url, r.tiempo_formateado);
      tarjeta.querySelector(".video-thumb-trigger").addEventListener("click", lanzarPlayer);
      tarjeta.querySelector(".video-title-trigger").addEventListener("click", lanzarPlayer);
      tarjeta.querySelector(".btn-ver-video").addEventListener("click", lanzarPlayer);

    } else {
      // Manual PDF
      tarjeta.className = "tarjeta-resultado glass-panel rounded-2xl p-6 shadow-xl hover:-translate-y-1 hover:shadow-iot-teal/5 transition-all flex flex-col sm:flex-row gap-6";
      const archivoPdf = r.archivo || r.nombre_archivo || "";
      const urlConPagina = `/manuales/${encodeURIComponent(archivoPdf)}?token=${token}#page=${r.pagina_encontrada}&zoom=page-width`;
      const urlRaw = `/manuales/${encodeURIComponent(archivoPdf)}?token=${token}`;
      const infoPaginas = r.paginas_coincidentes > 1
        ? `<span>Pág. ${r.pagina_encontrada} de ${r.paginas} · coincide en ${r.paginas_coincidentes} páginas</span>`
        : `<span>Pág. ${r.pagina_encontrada} de ${r.paginas}</span>`;
      
      badgePrivacidad = r.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Confidencial Técnico</span>`
        : '';

      tagsBadges = r.etiquetas
        ? r.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="etiqueta bg-iot-teal/10 border border-iot-teal/30 text-iot-tealLight px-2 py-0.5 rounded-md shadow-sm">🏷️ ${escapeHtml(t)}</span>`).join(' ')
        : '';

      tarjeta.innerHTML = `
        <div class="relative shrink-0 w-24 h-32 rounded-xl overflow-hidden border border-iot-border bg-iot-bg hidden sm:block cursor-pointer group shadow-inner manual-thumb-trigger" title="Previsualizar en Visor (Pág. ${r.pagina_encontrada})">
          <img class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" src="/api/miniatura/${r.id}/${r.pagina_encontrada}?token=${encodeURIComponent(token || '')}" alt="" loading="lazy" onerror="this.style.display='none'">
          <div class="absolute inset-0 bg-iot-teal/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xl">
            👁️
          </div>
        </div>
        <div class="resultado-contenido flex-1 min-w-0">
          <div class="resultado-cabecera flex justify-between items-baseline gap-3 flex-wrap mb-3">
            <div class="flex items-center gap-2 flex-wrap">
              <a class="resultado-titulo font-sora font-bold text-xl text-iot-tealLight hover:text-iot-teal transition-colors flex items-center gap-2 cursor-pointer manual-title-trigger" href="${urlConPagina}" title="Abrir en Visor">
                📄 ${escapeHtml(r.nombre)}
              </a>
              <a href="${urlConPagina}" target="_blank" class="text-iot-textSec hover:text-iot-tealLight text-xs transition-colors p-1" title="Abrir en nueva pestaña externa">↗</a>
            </div>
            <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
              <span class="bg-iot-teal/20 text-iot-tealLight border border-iot-teal/30 px-2 py-0.5 rounded text-xs font-semibold">📄 Manual PDF</span>
              ${badgePrivacidad}
              ${r.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(r.dispositivo)}</span>` : ""}
              ${r.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(r.categoria)}</span>` : ""}
              ${tagsBadges}
              <span class="text-iot-tealLight bg-iot-teal/10 px-2 py-0.5 rounded-md border border-iot-teal/20 shadow-sm">${infoPaginas}</span>
            </div>
          </div>
          <div class="resultado-fragmento text-sm text-iot-textSec leading-relaxed bg-iot-bg/50 p-4 rounded-xl border border-iot-border/50">${sanitizeFragment(r.fragmento.replace(/<mark>/g, '<mark class="bg-iot-teal text-white rounded px-1">'))}</div>
          
          <div class="mt-4 flex items-center justify-between flex-wrap gap-2 pt-3 border-t border-iot-border/50">
            <div class="flex items-center gap-2">
              <button type="button" class="btn-ver-pdf-visor bg-iot-teal hover:bg-iot-tealLight text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow active:scale-95">
                👁️ Ver en Pág. ${r.pagina_encontrada}
              </button>
              ${r.dispositivo ? `
              <button type="button" class="btn-pack-obra-card text-iot-textSec hover:text-white bg-iot-panel hover:bg-iot-hover border border-iot-border px-3 py-1.5 rounded-lg text-xs font-mono transition-colors flex items-center gap-1.5">
                📦 Pack Obra
              </button>` : ''}
            </div>
            <a href="${urlRaw}" download class="text-iot-textSec hover:text-white text-xs font-mono transition-colors flex items-center gap-1">
              📥 Descargar PDF
            </a>
          </div>
        </div>
      `;

      const lanzarVisor = (e) => {
        if (e) e.preventDefault();
        abrirVisorPDF(r.nombre || r.nombre_original || archivoPdf, archivoPdf, r.pagina_encontrada, r.paginas || r.num_paginas || 1, r.dispositivo, r.nivel_acceso || 'publico');
      };

      const thumbTrigger = tarjeta.querySelector(".manual-thumb-trigger");
      if (thumbTrigger) thumbTrigger.addEventListener("click", lanzarVisor);
      tarjeta.querySelector(".manual-title-trigger").addEventListener("click", lanzarVisor);
      tarjeta.querySelector(".btn-ver-pdf-visor").addEventListener("click", lanzarVisor);

      const btnPackCard = tarjeta.querySelector(".btn-pack-obra-card");
      if (btnPackCard && r.dispositivo) {
        btnPackCard.addEventListener("click", () => descargarPackObra(r.dispositivo, btnPackCard));
      }
    }

    contenedorResultados.appendChild(tarjeta);
  });
}

function restablecerVistaBusqueda() {
  contenedorResultados.innerHTML = "";
  estadoBusqueda.style.display = "none";
  estadoBusqueda.textContent = "";
  if (filtrosTipoResultado) filtrosTipoResultado.classList.add("hidden");
  if (bannerPackObra) bannerPackObra.classList.add("hidden");
  if (contenedorChipsEtiquetas) contenedorChipsEtiquetas.classList.remove("hidden");
  if (btnLimpiarBusqueda) btnLimpiarBusqueda.classList.add("hidden");
  listaSugerencias.classList.remove("visible");
}

async function buscar() {
  const q = inputBusqueda.value.trim();
  contenedorResultados.innerHTML = "";
  listaSugerencias.classList.remove("visible");
  if (filtrosTipoResultado) filtrosTipoResultado.classList.add("hidden");
  if (bannerPackObra) bannerPackObra.classList.add("hidden");

  // Ocultar tags al buscar para que los resultados aparezcan inmediatamente en pantalla sin scroll
  if (contenedorChipsEtiquetas) {
    contenedorChipsEtiquetas.classList.add("hidden");
  }
  if (btnLimpiarBusqueda && q.length > 0) {
    btnLimpiarBusqueda.classList.remove("hidden");
  }

  if (!q) {
    estadoBusqueda.style.display = "block";
    estadoBusqueda.textContent = "Introduce tu consulta.";
    if (contenedorChipsEtiquetas) contenedorChipsEtiquetas.classList.remove("hidden");
    if (btnLimpiarBusqueda) btnLimpiarBusqueda.classList.add("hidden");
    return;
  }
  estadoBusqueda.style.display = "block";
  estadoBusqueda.textContent = "Buscando en manuales y transcripciones de video...";

  const parametros = new URLSearchParams({
    q,
    dispositivo: filtroDispositivo.value,
    categoria: filtroCategoria.value,
  });

  try {
    const resp = await fetchAuth(`/api/buscar?${parametros.toString()}`);
    const data = await resp.json();

    ultimosResultados.todos = data.resultados || [];
    ultimosResultados.manuales = data.manuales || [];
    ultimosResultados.videos = data.videos || [];

    if (ultimosResultados.todos.length === 0) {
      estadoBusqueda.textContent = "No se ha encontrado ninguna coincidencia. Prueba con alguno de los temas frecuentes:";
      if (contenedorChipsEtiquetas) contenedorChipsEtiquetas.classList.remove("hidden");
      return;
    }
    estadoBusqueda.style.display = "none";

    // Actualizar contadores
    if (contadorTodos) contadorTodos.textContent = ultimosResultados.todos.length;
    if (contadorManuales) contadorManuales.textContent = ultimosResultados.manuales.length;
    if (contadorVideos) contadorVideos.textContent = ultimosResultados.videos.length;

    // Detectar si mostrar banner de Pack de Obra
    const dispSeleccionado = filtroDispositivo.value || (ultimosResultados.todos.find(item => item.dispositivo)?.dispositivo) || "";
    if (dispSeleccionado && bannerPackObra && bannerPackDispositivo) {
      dispositivoBannerActivo = dispSeleccionado;
      bannerPackDispositivo.textContent = dispSeleccionado;
      bannerPackObra.classList.remove("hidden");
    } else if (bannerPackObra) {
      dispositivoBannerActivo = "";
      bannerPackObra.classList.add("hidden");
    }

    if (filtrosTipoResultado) filtrosTipoResultado.classList.remove("hidden");
    activarFiltroTipo("todos");
  } catch (e) {
    if (e.message !== "No autorizado") {
      estadoBusqueda.textContent = "Ocurrió un error al buscar. Revisa que el servidor esté funcionando.";
    }
    if (contenedorChipsEtiquetas) contenedorChipsEtiquetas.classList.remove("hidden");
  }
}

btnBuscar.addEventListener("click", buscar);
inputBusqueda.addEventListener("keydown", (e) => {
  if (e.key === "Enter") buscar();
});

inputBusqueda.addEventListener("input", () => {
  if (inputBusqueda.value.trim().length > 0) {
    if (btnLimpiarBusqueda) btnLimpiarBusqueda.classList.remove("hidden");
  } else {
    restablecerVistaBusqueda();
  }
});

if (btnLimpiarBusqueda) {
  btnLimpiarBusqueda.addEventListener("click", () => {
    inputBusqueda.value = "";
    restablecerVistaBusqueda();
    inputBusqueda.focus();
  });
}

// ---------- Subir ----------
const zonaDrop = document.getElementById("zona-drop");
const inputArchivos = document.getElementById("input-archivos");
const listaSeleccionados = document.getElementById("lista-archivos-seleccionados");
const btnSubir = document.getElementById("btn-subir");
const estadoSubida = document.getElementById("estado-subida");

let archivosSeleccionados = [];

zonaDrop.addEventListener("click", () => inputArchivos.click());

zonaDrop.addEventListener("dragover", (e) => {
  e.preventDefault();
  zonaDrop.classList.add("border-iot-teal");
});
zonaDrop.addEventListener("dragleave", () => zonaDrop.classList.remove("border-iot-teal"));
zonaDrop.addEventListener("drop", (e) => {
  e.preventDefault();
  zonaDrop.classList.remove("border-iot-teal");
  agregarArchivos(e.dataTransfer.files);
});

inputArchivos.addEventListener("change", () => agregarArchivos(inputArchivos.files));

function agregarArchivos(fileList) {
  Array.from(fileList).forEach((f) => {
    if (f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")) {
      archivosSeleccionados.push(f);
    }
  });
  renderizarSeleccionados();
}

function renderizarSeleccionados() {
  listaSeleccionados.innerHTML = "";
  archivosSeleccionados.forEach((f, idx) => {
    const item = document.createElement("div");
    item.className = "archivo-item flex justify-between items-center bg-iot-bg border border-iot-border p-3 rounded-xl text-sm";
    item.innerHTML = `<span class="text-iot-text flex items-center gap-2">📄 ${f.name}</span><span class="quitar cursor-pointer text-red-400 hover:text-red-300 font-bold transition-colors" data-idx="${idx}">Quitar</span>`;
    listaSeleccionados.appendChild(item);
  });
  btnSubir.disabled = archivosSeleccionados.length === 0;

  listaSeleccionados.querySelectorAll(".quitar").forEach((el) => {
    el.addEventListener("click", () => {
      archivosSeleccionados.splice(Number(el.dataset.idx), 1);
      renderizarSeleccionados();
    });
  });
}

btnSubir.addEventListener("click", async () => {
  if (archivosSeleccionados.length === 0) return;

  btnSubir.disabled = true;
  btnSubir.textContent = "Indexando...";
  estadoSubida.innerHTML = "";

  const formData = new FormData();
  archivosSeleccionados.forEach((f) => formData.append("archivos", f));
  formData.append("dispositivo", document.getElementById("input-dispositivo").value);
  formData.append("categoria", document.getElementById("input-categoria").value);
  formData.append("nivel_acceso", document.getElementById("input-acceso").value); // RBAC
  formData.append("etiquetas", document.getElementById("input-etiquetas").value);

  try {
    const resp = await fetchAuth("/api/subir", { method: "POST", body: formData });
    const data = await resp.json();

    data.resultados.forEach((r) => {
      const linea = document.createElement("div");
      linea.className = "py-2 text-sm text-iot-textSec";
      if (r.ok) {
        linea.textContent = `✅ ${r.archivo} indexado correctamente (${r.paginas} páginas)`;
      } else {
        linea.textContent = `❌ ${r.archivo}: ${r.error}`;
      }
      estadoSubida.appendChild(linea);
    });

    cargarSugerencias();
    archivosSeleccionados = [];
    renderizarSeleccionados();
    document.getElementById("input-dispositivo").value = "";
    document.getElementById("input-categoria").value = "";
    document.getElementById("input-etiquetas").value = "";
    cargarOpcionesFiltro();
  } catch (e) {} finally {
    btnSubir.disabled = false;
    btnSubir.textContent = "Procesar e Indexar";
  }
});

// ---------- Modal Editar Manual ----------
const modalEditar = document.getElementById("modal-editar-manual");
const formEditar = document.getElementById("form-editar-manual");
const editManualId = document.getElementById("edit-manual-id");
const editManualNombre = document.getElementById("edit-manual-nombre");
const editDispositivo = document.getElementById("edit-dispositivo");
const editCategoria = document.getElementById("edit-categoria");
const editAcceso = document.getElementById("edit-acceso");
const editEtiquetas = document.getElementById("edit-etiquetas");
const editError = document.getElementById("edit-manual-error");
const btnCerrarModalEditar = document.getElementById("btn-cerrar-modal-editar");
const btnCancelarEditar = document.getElementById("btn-cancelar-editar");

function cerrarModalEditar() {
  if (modalEditar) modalEditar.classList.add("hidden");
  if (formEditar) formEditar.reset();
  if (editError) editError.classList.add("hidden");
}

if (btnCerrarModalEditar) btnCerrarModalEditar.addEventListener("click", cerrarModalEditar);
if (btnCancelarEditar) btnCancelarEditar.addEventListener("click", cerrarModalEditar);

if (formEditar) {
  formEditar.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (editError) editError.classList.add("hidden");

    const id = editManualId.value;
    const tipo = formEditar.dataset.tipo || "manual";
    const payload = {
      dispositivo: editDispositivo.value,
      categoria: editCategoria.value,
      nivel_acceso: editAcceso.value,
      etiquetas: editEtiquetas.value
    };

    try {
      const endpoint = tipo === "video" ? `/api/videos/${id}` : `/api/manuales/${id}`;
      const resp = await fetchAuth(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Error al actualizar");
      }

      cerrarModalEditar();
      if (tipo === "video") {
        cargarBibliotecaVideos();
      } else {
        cargarBiblioteca();
      }
      cargarOpcionesFiltro();
      cargarSugerencias();
    } catch (err) {
      if (editError) {
        editError.textContent = err.message;
        editError.classList.remove("hidden");
      }
    }
  });
}

// ---------- Biblioteca ----------
async function cargarBiblioteca() {
  const contenedor = document.getElementById("lista-biblioteca");
  const contadorManualesBiblio = document.getElementById("biblio-contador-manuales");
  contenedor.innerHTML = `<div class="p-8 text-center text-iot-textSec font-mono text-sm">Cargando base de conocimiento...</div>`;

  try {
    const resp = await fetchAuth("/api/manuales");
    const data = await resp.json();

    if (contadorManualesBiblio) {
      contadorManualesBiblio.textContent = data.manuales.length;
    }

    if (data.manuales.length === 0) {
      contenedor.innerHTML = `<div class="p-8 text-center text-iot-textSec text-sm">La biblioteca de manuales está vacía.</div>`;
      return;
    }

    contenedor.innerHTML = "";
    data.manuales.forEach((m) => {
      const fila = document.createElement("div");
      fila.className = "bg-iot-panel p-4 flex justify-between items-center gap-4 hover:bg-iot-hover transition-colors group";
      
      const badgePrivacidad = m.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Confidencial</span>`
        : `<span class="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20 text-xs shadow-sm">🌍 Público</span>`;
      
      const tagsBadges = m.etiquetas
        ? m.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="bg-iot-teal/10 text-iot-tealLight border border-iot-teal/30 px-2 py-0.5 rounded text-[11px] font-mono">🏷️ ${escapeHtml(t)}</span>`).join(' ')
        : '';
        
      fila.innerHTML = `
        <div class="flex flex-col gap-1.5 flex-1 min-w-0">
          <a class="font-sora font-semibold text-iot-text hover:text-iot-tealLight transition-colors flex items-center gap-2 truncate text-lg manual-biblio-link cursor-pointer" href="/manuales/${encodeURIComponent(m.archivo)}?token=${encodeURIComponent(token || '')}" title="Previsualizar en Visor">📄 ${escapeHtml(m.nombre)}</a>
          <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
            ${badgePrivacidad}
            ${m.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(m.dispositivo)}</span>` : ""}
            ${m.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(m.categoria)}</span>` : ""}
            ${tagsBadges}
            <span class="text-iot-textSec/70 shrink-0">${m.paginas} pág.</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button class="boton-ver-biblio text-iot-tealLight hover:text-white text-xs bg-iot-teal/15 hover:bg-iot-teal/25 border border-iot-teal/30 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm font-sora cursor-pointer"
            data-nombre="${encodeURIComponent(m.nombre)}"
            data-archivo="${encodeURIComponent(m.archivo)}"
            data-paginas="${m.paginas}"
            data-dispositivo="${encodeURIComponent(m.dispositivo || '')}"
            data-acceso="${encodeURIComponent(m.nivel_acceso || 'publico')}">
            👁️ Ver
          </button>
          <button class="boton-editar text-iot-tealLight hover:text-white text-xs bg-iot-teal/10 hover:bg-iot-teal/20 border border-iot-teal/30 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm font-sora cursor-pointer" 
            data-id="${m.id}" 
            data-nombre="${encodeURIComponent(m.nombre)}" 
            data-dispositivo="${encodeURIComponent(m.dispositivo || '')}" 
            data-categoria="${encodeURIComponent(m.categoria || '')}" 
            data-acceso="${encodeURIComponent(m.nivel_acceso || 'publico')}" 
            data-etiquetas="${encodeURIComponent(m.etiquetas || '')}">
            ✏️ Editar
          </button>
          <button class="boton-eliminar text-red-400 hover:text-red-300 font-bold text-xs bg-red-400/10 hover:bg-red-400/20 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm cursor-pointer" data-id="${m.id}">Eliminar</button>
        </div>
      `;
      contenedor.appendChild(fila);
    });

    contenedor.querySelectorAll(".boton-ver-biblio").forEach((btn) => {
      btn.addEventListener("click", () => {
        abrirVisorPDF(
          decodeURIComponent(btn.dataset.nombre || ''),
          decodeURIComponent(btn.dataset.archivo || ''),
          1,
          parseInt(btn.dataset.paginas || '1'),
          decodeURIComponent(btn.dataset.dispositivo || ''),
          decodeURIComponent(btn.dataset.acceso || 'publico')
        );
      });
    });

    contenedor.querySelectorAll(".manual-biblio-link").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const row = link.closest(".flex.items-center");
        const btnVer = row ? row.querySelector(".boton-ver-biblio") : null;
        if (btnVer) btnVer.click();
      });
    });

    contenedor.querySelectorAll(".boton-editar").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!modalEditar) return;
        formEditar.dataset.tipo = "manual";
        editManualId.value = btn.dataset.id;
        editManualNombre.textContent = "📄 " + decodeURIComponent(btn.dataset.nombre || '');
        editDispositivo.value = decodeURIComponent(btn.dataset.dispositivo || '');
        editCategoria.value = decodeURIComponent(btn.dataset.categoria || '');
        editAcceso.value = decodeURIComponent(btn.dataset.acceso || 'publico');
        editEtiquetas.value = decodeURIComponent(btn.dataset.etiquetas || '');
        if (editError) editError.classList.add("hidden");
        modalEditar.classList.remove("hidden");
      });
    });

    contenedor.querySelectorAll(".boton-eliminar").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("¿Seguro que deseas eliminar este manual del RAG?")) return;
        try {
          await fetchAuth(`/api/manuales/${btn.dataset.id}`, { method: "DELETE" });
          cargarBiblioteca();
          cargarOpcionesFiltro();
          cargarSugerencias();
        } catch(e) {}
      });
    });
  } catch (e) {}
}

// ---------- Reindexar Todo ----------
const btnReindexar = document.getElementById("btn-reindexar");
if (btnReindexar) {
  btnReindexar.addEventListener("click", async () => {
    if (!confirm("¿Seguro que deseas re-extraer el texto de todos los PDFs? Esto puede tardar unos minutos si hay muchos archivos.")) return;
    
    const textoOriginal = btnReindexar.innerHTML;
    btnReindexar.innerHTML = `<svg class="animate-spin w-4 h-4 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Reindexando...`;
    btnReindexar.disabled = true;
    
    try {
      const resp = await fetchAuth("/api/reindexar", { method: "POST" });
      const data = await resp.json();
      if (data.errores && data.errores.length > 0) {
        alert("Reindexación completada con " + data.errores.length + " errores:\\n" + data.errores.join("\\n"));
      } else {
        alert(`¡Reindexación exitosa! Se han procesado ${data.reindexados} manuales.`);
      }
      cargarBiblioteca();
    } catch(e) {
      alert("Error en la reindexación: " + e.message);
    } finally {
      btnReindexar.innerHTML = textoOriginal;
      btnReindexar.disabled = false;
    }
  });
}

// ---------- Gestión de Videos de YouTube (Biblioteca) ----------
const btnSubtabManuales = document.getElementById("btn-subtab-manuales");
const btnSubtabVideos = document.getElementById("btn-subtab-videos");
const seccionManuales = document.getElementById("seccion-biblioteca-manuales");
const seccionVideos = document.getElementById("seccion-biblioteca-videos");
const biblioContadorVideos = document.getElementById("biblio-contador-videos");
const listaBibliotecaVideos = document.getElementById("lista-biblioteca-videos");
const btnSyncCanal = document.getElementById("btn-sync-canal");
const estadoSyncCanal = document.getElementById("estado-sync-canal");

function alternarSubtabBiblioteca(pestana) {
  if (pestana === "manuales") {
    btnSubtabManuales.className = "subtab-biblio px-4 py-2 rounded-lg text-sm font-semibold bg-iot-teal text-white shadow-sm transition-all flex items-center gap-2";
    btnSubtabVideos.className = "subtab-biblio px-4 py-2 rounded-lg text-sm font-semibold bg-iot-panel text-iot-textSec hover:text-white border border-iot-border transition-all flex items-center gap-2";
    seccionManuales.classList.remove("hidden");
    seccionVideos.classList.add("hidden");
  } else {
    btnSubtabVideos.className = "subtab-biblio px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white shadow-sm transition-all flex items-center gap-2";
    btnSubtabManuales.className = "subtab-biblio px-4 py-2 rounded-lg text-sm font-semibold bg-iot-panel text-iot-textSec hover:text-white border border-iot-border transition-all flex items-center gap-2";
    seccionVideos.classList.remove("hidden");
    seccionManuales.classList.add("hidden");
    cargarBibliotecaVideos();
  }
}

if (btnSubtabManuales) btnSubtabManuales.addEventListener("click", () => alternarSubtabBiblioteca("manuales"));
if (btnSubtabVideos) btnSubtabVideos.addEventListener("click", () => alternarSubtabBiblioteca("videos"));

async function cargarBibliotecaVideos() {
  if (!listaBibliotecaVideos) return;
  listaBibliotecaVideos.innerHTML = `<div class="p-8 text-center text-iot-textSec font-mono text-sm">Cargando catálogo de videos...</div>`;

  try {
    const resp = await fetchAuth("/api/videos");
    const data = await resp.json();

    if (biblioContadorVideos) {
      biblioContadorVideos.textContent = data.videos.length;
    }

    // Actualizar badge de sincronizador programado en segundo plano
    try {
      const respStatus = await fetchAuth("/api/videos/sync-status");
      const statusData = await respStatus.json();
      const textoStatus = document.getElementById("texto-cron-status");
      if (textoStatus && statusData) {
        if (statusData.ultima_ejecucion) {
          const fecha = new Date(statusData.ultima_ejecucion);
          const hora = fecha.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          textoStatus.textContent = `Auto-Sync: Activo (cada ${statusData.intervalo_horas}h · Última: ${hora})`;
        } else {
          textoStatus.textContent = `Auto-Sync: Activo (cada ${statusData.intervalo_horas}h)`;
        }
      }
    } catch(e) {}

    if (!data.videos || data.videos.length === 0) {
      listaBibliotecaVideos.innerHTML = `
        <div class="p-10 text-center text-iot-textSec flex flex-col items-center gap-3">
          <span class="text-4xl">🎬</span>
          <p class="text-sm">Aún no hay videos indexados en la biblioteca.</p>
          <p class="text-xs text-iot-tealLight font-mono">Haz clic en "Sincronizar @MySmartWindow" para importar los tutoriales oficiales.</p>
        </div>
      `;
      return;
    }

    listaBibliotecaVideos.innerHTML = "";
    data.videos.forEach((v) => {
      const fila = document.createElement("div");
      fila.className = "bg-iot-panel p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 hover:bg-iot-hover transition-colors group";
      
      const badgePrivacidad = v.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Confidencial</span>`
        : `<span class="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20 text-xs shadow-sm">🌍 Público</span>`;
      
      const badgeSubs = v.tiene_subtitulos
        ? `<span class="bg-iot-teal/10 text-iot-tealLight border border-iot-teal/30 px-2 py-0.5 rounded text-[11px] font-mono">📝 Subtítulos indexados</span>`
        : `<span class="bg-gray-500/10 text-gray-400 border border-gray-500/30 px-2 py-0.5 rounded text-[11px] font-mono">🔇 Sin subtítulos</span>`;

      const tagsBadges = v.etiquetas
        ? v.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="bg-red-500/10 text-red-300 border border-red-500/30 px-2 py-0.5 rounded text-[11px] font-mono">🏷️ ${escapeHtml(t)}</span>`).join(' ')
        : '';

      fila.innerHTML = `
        <div class="flex items-center gap-4 flex-1 min-w-0">
          <div class="relative shrink-0 w-24 h-16 rounded-lg overflow-hidden border border-iot-border bg-black cursor-pointer video-thumb-player">
            <img class="w-full h-full object-cover group-hover:scale-105 transition-transform opacity-90" src="${escapeHtml(v.miniatura_url)}" alt="${escapeHtml(v.titulo)}">
            <div class="absolute inset-0 bg-black/20 hover:bg-black/0 flex items-center justify-center">
              <svg class="w-6 h-6 text-white drop-shadow" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </div>
          </div>
          <div class="flex flex-col gap-1 min-w-0">
            <div class="font-sora font-semibold text-iot-text hover:text-red-400 transition-colors cursor-pointer truncate text-base video-title-player" title="${escapeHtml(v.titulo)}">
              ▶ ${escapeHtml(v.titulo)}
            </div>
            </div>
            <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
              ${badgePrivacidad}
              ${badgeSubs}
              ${v.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(v.dispositivo)}</span>` : ""}
              ${v.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${escapeHtml(v.categoria)}</span>` : ""}
              ${tagsBadges}
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0 self-end sm:self-center">
          <button type="button" class="btn-biblio-ver-video text-white text-xs bg-red-600 hover:bg-red-500 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm font-sora cursor-pointer">
            ▶ Ver
          </button>
          <button class="boton-editar-video text-iot-tealLight hover:text-white text-xs bg-iot-teal/10 hover:bg-iot-teal/20 border border-iot-teal/30 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm font-sora cursor-pointer" 
            data-id="${v.id}" 
            data-titulo="${encodeURIComponent(v.titulo)}" 
            data-dispositivo="${encodeURIComponent(v.dispositivo || '')}" 
            data-categoria="${encodeURIComponent(v.categoria || '')}" 
            data-acceso="${encodeURIComponent(v.nivel_acceso || 'publico')}" 
            data-etiquetas="${encodeURIComponent(v.etiquetas || '')}">
            ✏️ Editar
          </button>
          <button class="boton-eliminar-video text-red-400 hover:text-red-300 font-bold text-xs bg-red-400/10 hover:bg-red-400/20 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm cursor-pointer" data-id="${v.id}">
            Eliminar
          </button>
        </div>
      `;

      const playVideo = () => abrirReproductorVideo(v.titulo, `https://www.youtube.com/embed/${v.video_id}?autoplay=1`, v.canal, v.url, "00:00");
      fila.querySelector(".video-thumb-player").addEventListener("click", playVideo);
      fila.querySelector(".video-title-player").addEventListener("click", playVideo);
      fila.querySelector(".btn-biblio-ver-video").addEventListener("click", playVideo);

      listaBibliotecaVideos.appendChild(fila);
    });

    listaBibliotecaVideos.querySelectorAll(".boton-editar-video").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!modalEditar) return;
        formEditar.dataset.tipo = "video";
        editManualId.value = btn.dataset.id;
        editManualNombre.textContent = "🎥 " + decodeURIComponent(btn.dataset.titulo || '');
        editDispositivo.value = decodeURIComponent(btn.dataset.dispositivo || '');
        editCategoria.value = decodeURIComponent(btn.dataset.categoria || '');
        editAcceso.value = decodeURIComponent(btn.dataset.acceso || 'publico');
        editEtiquetas.value = decodeURIComponent(btn.dataset.etiquetas || '');
        if (editError) editError.classList.add("hidden");
        modalEditar.classList.remove("hidden");
      });
    });

    listaBibliotecaVideos.querySelectorAll(".boton-eliminar-video").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("¿Seguro que deseas eliminar este video de la base de conocimiento?")) return;
        try {
          await fetchAuth(`/api/videos/${btn.dataset.id}`, { method: "DELETE" });
          cargarBibliotecaVideos();
          cargarOpcionesFiltro();
          cargarSugerencias();
        } catch(e) {}
      });
    });

  } catch(e) {}
}

// Evento Sincronizar Canal Oficial
if (btnSyncCanal) {
  btnSyncCanal.addEventListener("click", async () => {
    if (!confirm("¿Deseas sincronizar todos los videos y transcripciones del canal oficial @MySmartWindow? Esto conectará con YouTube para extraer títulos, miniaturas y subtítulos.")) return;
    
    const textoOriginal = btnSyncCanal.innerHTML;
    btnSyncCanal.innerHTML = `<svg class="animate-spin w-3.5 h-3.5 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Sincronizando canal...`;
    btnSyncCanal.disabled = true;

    if (estadoSyncCanal) {
      estadoSyncCanal.className = "text-xs font-mono text-center block p-2 rounded-lg bg-iot-teal/10 border border-iot-teal/30 text-iot-tealLight mb-2";
      estadoSyncCanal.textContent = "Conectando con YouTube y extrayendo videos de @MySmartWindow...";
      estadoSyncCanal.classList.remove("hidden");
    }

    try {
      const resp = await fetchAuth("/api/videos/sincronizar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ canal_url: "https://www.youtube.com/@MySmartWindow/videos" })
      });
      const data = await resp.json();
      if (resp.ok) {
        if (estadoSyncCanal) {
          estadoSyncCanal.className = "text-xs font-mono text-center block p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-2";
          estadoSyncCanal.textContent = `¡Sincronización completada con éxito! Se han procesado e indexado ${data.sincronizados} videos.`;
        }
        cargarBibliotecaVideos();
        cargarOpcionesFiltro();
        cargarSugerencias();
      } else {
        throw new Error(data.detail || "Error en la sincronización");
      }
    } catch (err) {
      if (estadoSyncCanal) {
        estadoSyncCanal.className = "text-xs font-mono text-center block p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 mb-2";
        estadoSyncCanal.textContent = `Error al sincronizar: ${err.message}`;
      }
    } finally {
      btnSyncCanal.innerHTML = textoOriginal;
      btnSyncCanal.disabled = false;
      setTimeout(() => {
        if (estadoSyncCanal) estadoSyncCanal.classList.add("hidden");
      }, 8000);
    }
  });
}

// Modal Agregar Video Individual
const modalAgregarVideo = document.getElementById("modal-agregar-video");
const formAgregarVideo = document.getElementById("form-agregar-video");
const btnAbrirModalVideo = document.getElementById("btn-abrir-modal-video");
const btnCerrarModalVideo = document.getElementById("btn-cerrar-modal-video");
const btnCancelarVideo = document.getElementById("btn-cancelar-video");
const videoUrlInput = document.getElementById("video-url");
const videoDispositivoInput = document.getElementById("video-dispositivo");
const videoCategoriaInput = document.getElementById("video-categoria");
const videoAccesoInput = document.getElementById("video-acceso");
const videoEtiquetasInput = document.getElementById("video-etiquetas");
const videoError = document.getElementById("video-error");

function cerrarModalVideo() {
  if (modalAgregarVideo) modalAgregarVideo.classList.add("hidden");
  if (formAgregarVideo) formAgregarVideo.reset();
  if (videoError) videoError.classList.add("hidden");
}

if (btnAbrirModalVideo) {
  btnAbrirModalVideo.addEventListener("click", () => {
    if (modalAgregarVideo) modalAgregarVideo.classList.remove("hidden");
  });
}
if (btnCerrarModalVideo) btnCerrarModalVideo.addEventListener("click", cerrarModalVideo);
if (btnCancelarVideo) btnCancelarVideo.addEventListener("click", cerrarModalVideo);

if (formAgregarVideo) {
  formAgregarVideo.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (videoError) videoError.classList.add("hidden");

    const submitBtn = document.getElementById("btn-guardar-video");
    submitBtn.disabled = true;
    submitBtn.textContent = "Indexando...";

    try {
      const resp = await fetchAuth("/api/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: videoUrlInput.value.trim(),
          dispositivo: videoDispositivoInput.value.trim(),
          categoria: videoCategoriaInput.value.trim(),
          nivel_acceso: videoAccesoInput.value,
          etiquetas: videoEtiquetasInput.value.trim()
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Error al añadir video");
      }

      cerrarModalVideo();
      cargarBibliotecaVideos();
      cargarOpcionesFiltro();
      cargarSugerencias();
    } catch (err) {
      if (videoError) {
        videoError.textContent = err.message;
        videoError.classList.remove("hidden");
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Indexar Video";
    }
  });
}

// ---------- Gestión de Usuarios (Admin) ----------
const tablaUsuarios = document.getElementById("lista-usuarios-tabla");
const formCrearUsuario = document.getElementById("form-crear-usuario");
const estadoCrearUsuario = document.getElementById("estado-crear-usuario");

async function cargarUsuarios() {
  tablaUsuarios.innerHTML = `<tr><td colspan="3" class="px-6 py-4 text-center text-iot-textSec">Cargando usuarios...</td></tr>`;
  try {
    const resp = await fetchAuth("/api/usuarios");
    const usuarios = await resp.json();
    
    tablaUsuarios.innerHTML = "";
    usuarios.forEach(u => {
      const isMe = u.email === userEmail;
      
      const tr = document.createElement("tr");
      tr.className = "hover:bg-iot-hover transition-colors";
      tr.innerHTML = `
        <td class="px-6 py-4">
          <div class="font-semibold text-iot-text">${escapeHtml(u.email)}</div>
          ${isMe ? `<div class="text-[10px] text-iot-tealLight font-mono mt-0.5 uppercase">Tú (Sesión Actual)</div>` : ''}
          ${u.is_first_login ? `<div class="text-[10px] text-orange-400 font-mono mt-0.5 uppercase">Pendiente cambiar password</div>` : ''}
        </td>
        <td class="px-6 py-4">
          <div class="relative max-w-[150px]">
            <select class="select-rol w-full bg-iot-bg border border-iot-border text-iot-text text-xs rounded px-2 py-1 focus:outline-none focus:border-iot-teal cursor-pointer ${isMe ? 'opacity-50 cursor-not-allowed' : ''}" data-id="${u.id}" ${isMe ? 'disabled' : ''}>
              <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
              <option value="tecnico" ${u.role === 'tecnico' ? 'selected' : ''}>Técnico</option>
              <option value="comercial" ${u.role === 'comercial' ? 'selected' : ''}>Comercial</option>
            </select>
          </div>
        </td>
        <td class="px-6 py-4 text-right">
          ${isMe ? '' : `
            <button class="btn-eliminar-usuario text-red-400 hover:text-red-300 bg-red-400/10 hover:bg-red-400/20 px-3 py-1 rounded text-xs font-bold transition-colors" data-id="${u.id}">
              Eliminar
            </button>
          `}
        </td>
      `;
      tablaUsuarios.appendChild(tr);
    });

    // Eventos Select Rol
    tablaUsuarios.querySelectorAll(".select-rol").forEach(select => {
      select.addEventListener("change", async (e) => {
        const id = select.dataset.id;
        const newRole = e.target.value;
        try {
          const resp = await fetchAuth(`/api/usuarios/${id}/rol`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: newRole })
          });
          if (!resp.ok) throw new Error();
        } catch(err) {
          alert("Error al cambiar el rol");
          cargarUsuarios(); // Revert UI
        }
      });
    });

    // Eventos Eliminar
    tablaUsuarios.querySelectorAll(".btn-eliminar-usuario").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("¿Seguro que deseas eliminar a este usuario permanentemente?")) return;
        try {
          const resp = await fetchAuth(`/api/usuarios/${btn.dataset.id}`, { method: "DELETE" });
          if (resp.ok) cargarUsuarios();
          else alert("Error al eliminar");
        } catch(err) {
          alert("Error de conexión");
        }
      });
    });

  } catch(e) {
    tablaUsuarios.innerHTML = `<tr><td colspan="3" class="px-6 py-4 text-center text-red-400">Error cargando usuarios</td></tr>`;
  }
}

formCrearUsuario.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("nuevo-user-email").value;
  const password = document.getElementById("nuevo-user-password").value;
  const role = document.getElementById("nuevo-user-role").value;
  
  const btn = document.getElementById("btn-crear-usuario");
  btn.disabled = true;
  estadoCrearUsuario.textContent = "Creando...";
  estadoCrearUsuario.className = "text-xs text-center font-mono mt-1 h-4 text-iot-tealLight";

  try {
    const resp = await fetchAuth("/api/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role })
    });
    
    if (resp.ok) {
      estadoCrearUsuario.textContent = "Usuario creado correctamente.";
      estadoCrearUsuario.classList.add("text-emerald-400");
      document.getElementById("nuevo-user-email").value = "";
      // Refresh list
      cargarUsuarios();
    } else {
      const data = await resp.json();
      throw new Error(data.detail || "Error al crear");
    }
  } catch (err) {
    estadoCrearUsuario.textContent = err.message;
    estadoCrearUsuario.className = "text-xs text-center font-mono mt-1 h-4 text-red-400";
  } finally {
    btn.disabled = false;
  }
});

// ==========================================================================
// MÓDULO: ESQUEMAS INTERACTIVOS DE CABLEADO 230V & ASISTENTE DE DIAGNÓSTICO SAT
// ==========================================================================

let esquemasModuloInicializado = false;

// Estado de la Simulación
let simEstadoActual = "reposo"; // "reposo" | "subiendo" | "bajando"
let simInvertido = false;

// Catálogo de Equipos y Advertencias Técnicas SAT
const CATALOGO_EQUIPOS_SAT = {
  "connect-1": {
    titulo: "CONNECT-1",
    subtitulo: "IoT Fenster Smart Controller · 230V 5A",
    alerta: "💡 <strong>CONNECT-1 (En marco / cajón):</strong> Alimentación 230V AC a través de magnetotérmico de persianas (máx. 10A). Asegura que la antena Wi-Fi no quede aprisionada o en contacto directo con el perfil de aluminio.",
    hasCpulsarBus: false,
    salida1Normal: "▲ (Marrón)",
    salida2Normal: "▼ (Negro)"
  },
  "connect-2": {
    titulo: "CONNECT-2",
    subtitulo: "Controlador Doble Canal / Sensores · 230V",
    alerta: "💡 <strong>CONNECT-2:</strong> Dispone de salidas dobles independientes para 2 motores o entradas de maniobra para sensores de viento/lluvia. Potencia máx: 500W por canal.",
    hasCpulsarBus: false,
    salida1Normal: "▲ M1 (Marrón)",
    salida2Normal: "▼ M1 (Negro)"
  },
  "c-wall": {
    titulo: "C-WALL",
    subtitulo: "Mecanismo Empotrado 60mm · Táctil 230V",
    alerta: "⚠️ <strong>¡OJO C-WALL REQUIERE NEUTRO OBLIGATORIO!:</strong> En cajas de mecanismos antiguas solo suele haber fase cortada. C-Wall es un receptor inteligente activo y <strong>DEBE tener Fase (L) y Neutro (N) directos</strong>. Si falta neutro en la caja, pásalo desde el registro o el cajón.",
    hasCpulsarBus: false,
    salida1Normal: "▲ (Marrón)",
    salida2Normal: "▼ (Negro)"
  },
  "c-pulsar": {
    titulo: "C-PULSAR (MÓDULO POTENCIA)",
    subtitulo: "Potencia en Cajón + Marco · Split 230V / 3.3V",
    alerta: "⚡ <strong>¡PELIGRO C-PULSAR - NUNCA 230V AL MARCO!:</strong> La electrónica de potencia 230V va exclusivamente en el cajón. El pulsador de marco trabaja a <strong>baja tensión (3.3V)</strong> mediante cable apantallado de 4 hilos. ¡Si metes 230V al pulsador se destruirá! Si parpadea continuo en el marco, el cable de señal está cortado por tornillo.",
    hasCpulsarBus: true,
    salida1Normal: "▲ (Marrón)",
    salida2Normal: "▼ (Negro)"
  },
  "connect-evo": {
    titulo: "CONNECT EVO",
    subtitulo: "Mecanismo Superficie de Marco · 230V",
    alerta: "💡 <strong>CONNECT EVO:</strong> Mecanismo de superficie para marco de ventana con teclas mecánicas. Alimentación directa 230V. Si una dirección no actúa, verifica el enclavamiento mecánico de las teclas.",
    hasCpulsarBus: false,
    salida1Normal: "▲ (Marrón)",
    salida2Normal: "▼ (Negro)"
  }
};

// Catálogo Canónico de 10 Averías SAT
const CASOS_TRIAGE_SAT = [
  {
    id: "triage-1",
    categoria: "motores",
    categoriaNombre: "Motores & Giros",
    dispositivo: "TODOS",
    titulo: "Persiana sube al pulsar bajar (giro invertido)",
    sintoma: "Al presionar la tecla de subida en la app o pulsador, la persiana desciende, o viceversa.",
    causa: "Los cables de maniobra marrón (subida) y negro (bajada) están conectados a la inversa en la salida del motor, o el parámetro de giro está invertido.",
    solucion: [
      "Opción 1 (Obra): Desconecta el magnetotérmico e intercambia de posición los cables marrón y negro en la bornera de salida del dispositivo.",
      "Opción 2 (App): En Ajustes del Dispositivo > Configuración Avanzada, activa la opción 'Invertir Dirección de Giro'."
    ],
    manualNombre: "Problemas y Soluciones SAT",
    manualArchivo: "Problemas_y_Soluciones_SAT.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "connect-1", invertir: true }
  },
  {
    id: "triage-2",
    categoria: "cpulsar",
    categoriaNombre: "C-Pulsar",
    dispositivo: "C-PULSAR",
    titulo: "C-Pulsar parpadea continuo en marco y no responde",
    sintoma: "El pulsador táctil integrado en el perfil de la ventana parpadea permanentemente en rojo o azul y no obedece a toques.",
    causa: "Pérdida de comunicación en el cable apantallado de 4 hilos entre el módulo de cajón y el pulsador de marco. Comúnmente perforado por un tornillo de fijación de la ventana o conector mal insertado.",
    solucion: [
      "Verifica si algún tornillo de carpintería ha mordido el cable de señal al fijar la ventana a obra.",
      "Comprueba la continuidad con un polímetro en los 4 hilos (VCC 3.3V, GND, TX, RX).",
      "Asegúrate de que el conector rápido hembra haya encajado hasta hacer 'clic'.",
      "¡NUNCA conectes 230V a este conector!"
    ],
    manualNombre: "Manual Técnico C-Pulsar",
    manualArchivo: "C-PULSAR_ES.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "c-pulsar", invertir: false }
  },
  {
    id: "triage-3",
    categoria: "wifi",
    categoriaNombre: "Wi-Fi & Red",
    dispositivo: "TODOS",
    titulo: "No conecta a Wi-Fi / Digi o Movistar CG-NAT",
    sintoma: "El dispositivo no completa la vinculación, o solo responde en red local pero no fuera del hogar.",
    causa: "Operadores con CG-NAT (como Digi, MásMóvil, Pepephone) comparten la misma IP pública y bloquean puertos MQTT (8883) y WebSockets. También routers con 2.4GHz y 5GHz combinados.",
    solucion: [
      "En el router: Crea una red Wi-Fi separada exclusiva de 2.4GHz con cifrado WPA2-PSK.",
      "En fibra Digi: Solicitar al operador el servicio 'Conexión Plus' (salida de CG-NAT a IP pública por 1€/mes).",
      "Desactivar 'Aislamiento de clientes' (AP Isolation / WMF) en la configuración Wi-Fi del router.",
      "Asegurar que los puertos salientes 8883 (MQTT TLS) y 443 estén abiertos."
    ],
    manualNombre: "Requisitos Conectividad y CGNAT",
    manualArchivo: "CONECTIVIDAD_REQUISITOS.pdf",
    manualPagina: 1,
    simPreset: null
  },
  {
    id: "triage-4",
    categoria: "motores",
    categoriaNombre: "Motores & Giros",
    dispositivo: "TODOS",
    titulo: "El relé hace 'clic' pero el motor no se mueve",
    sintoma: "Se escucha claramente el conmutador del relé al pulsar la orden, pero el motor no reacciona.",
    causa: "1) Protector térmico del motor disparado por uso continuado (más de 4 min seguidos en obra). 2) Final de carrera alcanzado. 3) Neutro (azul) del motor desconectado o suelto.",
    solucion: [
      "Protección térmica: Deja enfriar el motor durante 20 minutos sin pulsar.",
      "Comprobación de Neutro: Mide con el multímetro en alterna si hay 230V reales entre la fase activa (marrón o negro) y el neutro azul del motor.",
      "Finales de carrera: Verifica con la varilla allen si el tornillo del cabezal ha llegado al tope de carrera."
    ],
    manualNombre: "Problemas y Soluciones SAT",
    manualArchivo: "Problemas_y_Soluciones_SAT.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "connect-1", invertir: false }
  },
  {
    id: "triage-5",
    categoria: "cwall",
    categoriaNombre: "C-Wall",
    dispositivo: "C-WALL",
    titulo: "C-Wall sin alimentación / LED apagado",
    sintoma: "Al instalar C-Wall en la caja empotrada de pared, no enciende ningún LED ni responde.",
    causa: "Falta de hilo de Neutro (N) en la caja de 60mm. En instalaciones antiguas tradicionales de España solo bajaba la fase cortada a la tecla, sin neutro.",
    solucion: [
      "Mide con un polímetro entre L y N en la bornera de C-Wall: debe haber 230V AC continuos.",
      "Si solo hay fase y retornos al motor, es OBLIGATORIO pasar un cable de neutro (azul) desde la caja de registro o el cajón de persiana.",
      "Conectar la fase a L y el neutro a N."
    ],
    manualNombre: "Manual Instalación C-Wall",
    manualArchivo: "C-WALL_ES.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "c-wall", invertir: false }
  },
  {
    id: "triage-6",
    categoria: "motores",
    categoriaNombre: "Motores & Giros",
    dispositivo: "TODOS",
    titulo: "Motor descalibrado o no para en los extremos",
    sintoma: "La persiana golpea arriba en el cajón o sigue forzando el motor una vez que las lamas tocan el suelo.",
    causa: "Tornillos de final de carrera mecánico desajustados, o desfase en el conteo de tiempo/corriente de la app.",
    solucion: [
      "Motores mecánicos: Ajusta los tornillos blanco (subida) y amarillo (bajada) del cabezal del motor con una varilla o llave allen hasta fijar el tope físico deseado.",
      "En la App: Ve a Ajustes > Calibración Automática de Recorrido. Deja que complete un ciclo ininterrumpido (subida -> pausa -> bajada) para que grabe el consumo de corriente."
    ],
    manualNombre: "Calibración Motores y FC",
    manualArchivo: "CALIBRACION_MOTORES_Y_FINALES_DE_CARRERA.pdf",
    manualPagina: 1,
    simPreset: null
  },
  {
    id: "triage-7",
    categoria: "motores",
    categoriaNombre: "Motores & Giros",
    dispositivo: "CONNECT-EVO",
    titulo: "Pulsador físico responde con retardo o inversión",
    sintoma: "Hay que mantener pulsada la tecla para que se mueva o reacciona varios segundos después de soltar.",
    causa: "Tipo de pulsador mal configurado en firmware: el equipo espera un interruptor biestable cuando hay un pulsador monoestable (o viceversa).",
    solucion: [
      "Accede a los ajustes del dispositivo en la app de soporte técnico.",
      "En 'Tipo de Entrada de Pulsador': Selecciona 'Pulsador Monoestable' para teclas de retorno por muelle, o 'Interruptor Biestable' para conmutadores fijos.",
      "Verifica que el tiempo antirrebote esté fijado en 50ms."
    ],
    manualNombre: "Problemas y Soluciones SAT",
    manualArchivo: "Problemas_y_Soluciones_SAT.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "connect-evo", invertir: false }
  },
  {
    id: "triage-8",
    categoria: "motores",
    categoriaNombre: "Motores & Giros",
    dispositivo: "CONNECT-1",
    titulo: "Error de sobrecorriente o parpadeo rojo (Atasco de Lama)",
    sintoma: "El motor se para bruscamente a mitad de carrera y el LED del Connect parpadea rápidamente en rojo.",
    causa: "El sensor de corriente interno ha detectado un consumo superior a 2.2A debido a atasco de lama, fleje roto o suciedad en las guías laterales.",
    solucion: [
      "Inspecciona las guías laterales de aluminio en busca de rebabas, tornillos salientes o suciedad de obra.",
      "Comprueba que el peso total de la persiana no exceda el par nominal del motor (Nm).",
      "En la app de soporte, regula la 'Sensibilidad ante Obstáculos' a nivel medio."
    ],
    manualNombre: "Problemas y Soluciones SAT",
    manualArchivo: "Problemas_y_Soluciones_SAT.pdf",
    manualPagina: 1,
    simPreset: { dispositivo: "connect-1", invertir: false }
  },
  {
    id: "triage-9",
    categoria: "reset",
    categoriaNombre: "Reset & Fábrica",
    dispositivo: "TODOS",
    titulo: "Procedimiento Oficial de Reset de Fábrica (Modo AP)",
    sintoma: "Se requiere borrar el emparejamiento anterior o vincular el dispositivo a una red Wi-Fi nueva.",
    causa: "Cambio de router o contraseña de la vivienda, o reasignación de dispositivo a otra ventana.",
    solucion: [
      "Método Pulsador: Realiza 5 pulsaciones cortas (1 seg cada una) con pausas de 1 seg entre ellas. El LED parpadeará rápido en azul/verde.",
      "Método Micro-Switch: Mantén presionado el botón micro-switch del equipo durante 10 segundos continuados.",
      "El dispositivo emitirá su punto de acceso Wi-Fi propio (ej. 'IoT-Fenster-XXXX') para configuración inicial."
    ],
    manualNombre: "Modo Fábrica y Reset Oficial",
    manualArchivo: "MODO_FABRICA_RESET.pdf",
    manualPagina: 1,
    simPreset: null
  },
  {
    id: "triage-10",
    categoria: "wifi",
    categoriaNombre: "Wi-Fi & Red",
    dispositivo: "TODOS",
    titulo: "Desconexiones aleatorias cada pocas horas (DHCP Lease / Mesh)",
    sintoma: "El equipo aparece como 'Fuera de línea' en la app de manera intermitente pero vuelve a conectar solo al cabo de unos minutos.",
    causa: "Tiempo de concesión DHCP demasiado corto en el router (ej. 60 min), o saltos de roaming agresivos entre nodos Wi-Fi Mesh.",
    solucion: [
      "Asigna una IP estática fija (reserva DHCP por MAC) para el dispositivo en el panel de control del router.",
      "En redes Mesh (Deco, Google Wifi, Asus AiMesh): Desactiva la opción 'Roaming Rápido' (Fast Roaming) o fuerza la vinculación del equipo al nodo más cercano.",
      "Comprueba que el nivel de señal RSSI recibido por el dispositivo sea superior a -70 dBm."
    ],
    manualNombre: "Requisitos Conectividad y CGNAT",
    manualArchivo: "CONECTIVIDAD_REQUISITOS.pdf",
    manualPagina: 1,
    simPreset: null
  }
];

function inicializarModuloEsquemas() {
  if (esquemasModuloInicializado) return;
  esquemasModuloInicializado = true;

  // 1. Selector de Sub-pestañas (Simulador vs Triage)
  const subtabSimulador = document.getElementById("subtab-btn-simulador");
  const subtabTriage = document.getElementById("subtab-btn-triage");
  const subvistaSimulador = document.getElementById("subvista-simulador");
  const subvistaTriage = document.getElementById("subvista-triage");

  function alternarSubvista(vista) {
    [subtabSimulador, subtabTriage].forEach(btn => {
      if (btn) {
        btn.classList.remove("activa", "bg-iot-teal", "text-white");
        btn.classList.add("text-iot-textSec");
      }
    });
    if (subvistaSimulador) subvistaSimulador.classList.add("hidden");
    if (subvistaTriage) subvistaTriage.classList.add("hidden");

    if (vista === "simulador") {
      if (subtabSimulador) { subtabSimulador.classList.add("activa", "bg-iot-teal", "text-white"); subtabSimulador.classList.remove("text-iot-textSec"); }
      if (subvistaSimulador) subvistaSimulador.classList.remove("hidden");
      if (typeof actualizarSimulador === "function") actualizarSimulador();
    } else if (vista === "triage") {
      if (subtabTriage) { subtabTriage.classList.add("activa", "bg-iot-teal", "text-white"); subtabTriage.classList.remove("text-iot-textSec"); }
      if (subvistaTriage) subvistaTriage.classList.remove("hidden");
    }
  }

  if (subtabSimulador) subtabSimulador.addEventListener("click", () => alternarSubvista("simulador"));
  if (subtabTriage) subtabTriage.addEventListener("click", () => alternarSubvista("triage"));

  // Inicializar Módulo de Asistencia Guiada IoT (12 Módulos)
  inicializarModuloAsistencia();

  // 2. Elementos del Simulador
  const simSelectDispositivo = document.getElementById("sim-dispositivo");
  const simSelectMotor = document.getElementById("sim-motor");
  const simCheckInvertir = document.getElementById("sim-invertir");

  const btnSimSubir = document.getElementById("btn-sim-subir");
  const btnSimBajar = document.getElementById("btn-sim-bajar");
  const btnSimParar = document.getElementById("btn-sim-parar");
  const btnSimSwap = document.getElementById("btn-sim-swap");

  const simEstadoLed = document.getElementById("sim-estado-led");
  const simEstadoTexto = document.getElementById("sim-estado-texto");
  const simEstadoSubtexto = document.getElementById("sim-estado-subtexto");
  const simAlertaTexto = document.getElementById("sim-alerta-texto");

  // Elementos SVG
  const svgDeviceTitle = document.getElementById("sim-svg-device-title");
  const svgDiagramaChip = document.getElementById("sim-diagrama-chip-dispositivo");
  const svgContactK1 = document.getElementById("sim-svg-contact-k1");
  const svgContactK2 = document.getElementById("sim-svg-contact-k2");
  const svgK1Badge = document.getElementById("sim-svg-k1-badge");
  const svgK2Badge = document.getElementById("sim-svg-k2-badge");
  const svgLblOut1 = document.getElementById("sim-svg-lbl-out1");
  const svgLblOut2 = document.getElementById("sim-svg-lbl-out2");
  const svgMotorSubtext = document.getElementById("sim-svg-motor-subtext");
  const svgMotorLblUp = document.getElementById("sim-svg-motor-lbl-up");
  const svgMotorSubUp = document.getElementById("sim-svg-motor-sub-up");
  const svgMotorLblDown = document.getElementById("sim-svg-motor-lbl-down");
  const svgMotorSubDown = document.getElementById("sim-svg-motor-sub-down");
  const svgMotorRotor = document.getElementById("sim-motor-rotor");
  const svgRotorIndicador = document.getElementById("sim-svg-rotor-indicador");
  const svgCpulsarModule = document.getElementById("sim-svg-cpulsar-module");
  const svgTornillosFc = document.getElementById("sim-svg-tornillos-fc");

  const wireOutUp = document.getElementById("sim-wire-out-up");
  const wireOutDown = document.getElementById("sim-wire-out-down");
  const wireOutN = document.getElementById("sim-wire-out-n");

  function actualizarSimulador() {
    const dispClave = simSelectDispositivo.value;
    const motorClave = simSelectMotor.value;
    const equipo = CATALOGO_EQUIPOS_SAT[dispClave] || CATALOGO_EQUIPOS_SAT["connect-1"];

    // Actualizar datos del dispositivo en SVG y Alerta
    if (svgDeviceTitle) svgDeviceTitle.textContent = equipo.titulo;
    if (svgDiagramaChip) svgDiagramaChip.textContent = dispClave.toUpperCase();
    if (simAlertaTexto) simAlertaTexto.innerHTML = equipo.alerta;

    // Mostrar/ocultar módulo C-Pulsar
    if (svgCpulsarModule) {
      svgCpulsarModule.style.opacity = equipo.hasCpulsarBus ? "1" : "0.15";
    }

    // Actualizar tipo de motor
    if (svgMotorSubtext) {
      if (motorClave === "electronico-4hilos") svgMotorSubtext.textContent = "Electrónico Digital";
      else if (motorClave === "via-radio") svgMotorSubtext.textContent = "Vía Radio Maniobra";
      else svgMotorSubtext.textContent = "4 Hilos Mecánico";
    }
    if (svgTornillosFc) {
      svgTornillosFc.style.opacity = (motorClave === "mecanico-4hilos") ? "1" : "0.2";
    }

    // Rotulación de bornes según inversión
    if (simInvertido) {
      if (svgLblOut1) svgLblOut1.textContent = "▼ (Negro - Invertido)";
      if (svgLblOut2) svgLblOut2.textContent = "▲ (Marrón - Invertido)";
      if (svgMotorSubUp) svgMotorSubUp.textContent = "Negro (Inv)";
      if (svgMotorSubDown) svgMotorSubDown.textContent = "Marrón (Inv)";
    } else {
      if (svgLblOut1) svgLblOut1.textContent = equipo.salida1Normal;
      if (svgLblOut2) svgLblOut2.textContent = equipo.salida2Normal;
      if (svgMotorSubUp) svgMotorSubUp.textContent = "Marrón";
      if (svgMotorSubDown) svgMotorSubDown.textContent = "Negro";
    }

    // Resetear estados visuales
    if (svgContactK1) svgContactK1.classList.remove("relay-closed-k1");
    if (svgContactK2) svgContactK2.classList.remove("relay-closed-k2");
    if (svgMotorRotor) svgMotorRotor.classList.remove("rotor-spin-cw", "rotor-spin-ccw");

    if (wireOutUp) wireOutUp.style.opacity = "0";
    if (wireOutDown) wireOutDown.style.opacity = "0";
    if (wireOutN) wireOutN.style.opacity = "0";

    // Aplicar estado
    if (simEstadoActual === "subiendo") {
      // Relé K1 Cierra
      if (svgContactK1) svgContactK1.classList.add("relay-closed-k1");
      if (svgK1Badge) { svgK1Badge.textContent = "CERRADO (Fase)"; svgK1Badge.setAttribute("fill", "#10b981"); }
      if (svgK2Badge) { svgK2Badge.textContent = "ABIERTO"; svgK2Badge.setAttribute("fill", "#64748b"); }

      // Corriente activa
      if (!simInvertido) {
        if (wireOutUp) { wireOutUp.style.opacity = "1"; wireOutUp.className = "wire-flow-up"; }
      } else {
        if (wireOutDown) { wireOutDown.style.opacity = "1"; wireOutDown.className = "wire-flow-up"; }
      }
      if (wireOutN) { wireOutN.style.opacity = "1"; wireOutN.className = "wire-flow-neutral"; }

      // Giro rotor (Antihorario = Subida persiana)
      if (svgMotorRotor) svgMotorRotor.classList.add("rotor-spin-ccw");
      if (svgRotorIndicador) { svgRotorIndicador.textContent = "SUBIENDO (◄)"; svgRotorIndicador.setAttribute("fill", "#10b981"); }

      // Badge Estado
      if (simEstadoLed) simEstadoLed.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse";
      if (simEstadoTexto) { simEstadoTexto.textContent = "SUBIENDO (Relé K1 Cerrado)"; simEstadoTexto.className = "font-bold text-emerald-400"; }
      if (simEstadoSubtexto) simEstadoSubtexto.textContent = "230V AC activo en borne de Subida";

    } else if (simEstadoActual === "bajando") {
      // Relé K2 Cierra
      if (svgContactK2) svgContactK2.classList.add("relay-closed-k2");
      if (svgK2Badge) { svgK2Badge.textContent = "CERRADO (Fase)"; svgK2Badge.setAttribute("fill", "#38bdf8"); }
      if (svgK1Badge) { svgK1Badge.textContent = "ABIERTO"; svgK1Badge.setAttribute("fill", "#64748b"); }

      // Corriente activa
      if (!simInvertido) {
        if (wireOutDown) { wireOutDown.style.opacity = "1"; wireOutDown.className = "wire-flow-down"; }
      } else {
        if (wireOutUp) { wireOutUp.style.opacity = "1"; wireOutUp.className = "wire-flow-down"; }
      }
      if (wireOutN) { wireOutN.style.opacity = "1"; wireOutN.className = "wire-flow-neutral"; }

      // Giro rotor (Horario = Bajada persiana)
      if (svgMotorRotor) svgMotorRotor.classList.add("rotor-spin-cw");
      if (svgRotorIndicador) { svgRotorIndicador.textContent = "BAJANDO (►)"; svgRotorIndicador.setAttribute("fill", "#38bdf8"); }

      // Badge Estado
      if (simEstadoLed) simEstadoLed.className = "w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse";
      if (simEstadoTexto) { simEstadoTexto.textContent = "BAJANDO (Relé K2 Cerrado)"; simEstadoTexto.className = "font-bold text-cyan-400"; }
      if (simEstadoSubtexto) simEstadoSubtexto.textContent = "230V AC activo en borne de Bajada";

    } else {
      // Reposo
      if (svgK1Badge) { svgK1Badge.textContent = "ABIERTO"; svgK1Badge.setAttribute("fill", "#64748b"); }
      if (svgK2Badge) { svgK2Badge.textContent = "ABIERTO"; svgK2Badge.setAttribute("fill", "#64748b"); }
      if (svgRotorIndicador) { svgRotorIndicador.textContent = "PARADO"; svgRotorIndicador.setAttribute("fill", "#64748b"); }

      // Badge Estado
      if (simEstadoLed) simEstadoLed.className = "w-2 h-2 rounded-full bg-slate-500";
      if (simEstadoTexto) { simEstadoTexto.textContent = "EN REPOSO (Relés Abiertos)"; simEstadoTexto.className = "font-bold text-iot-textSec"; }
      if (simEstadoSubtexto) simEstadoSubtexto.textContent = "Sin tensión 230V en salidas del motor";
    }
  }

  // Eventos de simulación
  if (simSelectDispositivo) simSelectDispositivo.addEventListener("change", actualizarSimulador);
  if (simSelectMotor) simSelectMotor.addEventListener("change", actualizarSimulador);
  
  if (simCheckInvertir) {
    simCheckInvertir.addEventListener("change", (e) => {
      simInvertido = e.target.checked;
      actualizarSimulador();
    });
  }

  if (btnSimSubir) {
    btnSimSubir.addEventListener("click", () => {
      simEstadoActual = "subiendo";
      actualizarSimulador();
    });
  }
  if (btnSimBajar) {
    btnSimBajar.addEventListener("click", () => {
      simEstadoActual = "bajando";
      actualizarSimulador();
    });
  }
  if (btnSimParar) {
    btnSimParar.addEventListener("click", () => {
      simEstadoActual = "reposo";
      actualizarSimulador();
    });
  }
  if (btnSimSwap) {
    btnSimSwap.addEventListener("click", () => {
      simInvertido = !simInvertido;
      if (simCheckInvertir) simCheckInvertir.checked = simInvertido;
      actualizarSimulador();
    });
  }

  // Exportar a WhatsApp
  const btnSimWhatsapp = document.getElementById("sim-btn-whatsapp");
  if (btnSimWhatsapp) {
    btnSimWhatsapp.addEventListener("click", () => {
      const dispNombre = simSelectDispositivo.options[simSelectDispositivo.selectedIndex].text;
      const motorNombre = simSelectMotor.options[simSelectMotor.selectedIndex].text;
      const invTexto = simInvertido ? "⚠️ CABLES INVERTIDOS (Marrón = Bajada / Negro = Subida)" : "Estándar (Marrón = Subida / Negro = Bajada)";

      const textoWp = `*🔌 ESQUEMA TÉCNICO DE CONEXIÓN 230V - IOT FENSTER*
*Dispositivo:* ${dispNombre}
*Motor:* ${motorNombre}
*Sentido de Giro:* ${invTexto}

*⚡ ALIMENTACIÓN GENERAL (230V AC):*
• Fase (L): Cable Marrón/Gris directo al borne L_IN
• Neutro (N): Cable Azul directo al borne N_IN
• Toma Tierra (PE): Cable Verde/Amarillo directo a la tierra de la vivienda

*🔄 CONEXIÓN AL MOTOR TUBULAR:*
• 🔵 *Azul:* Neutro común del motor (al borne N del dispositivo o clema común)
• 🟤 *Marrón:* Fase de ${simInvertido ? "BAJADA" : "SUBIDA"} (al borne de Salida 1 / ▲)
• ⚫ *Negro:* Fase de ${simInvertido ? "SUBIDA" : "BAJADA"} (al borne de Salida 2 / ▼)
• 🟢🟡 *Verde/Amarillo:* Tierra física conectada a la carcasa metálica del motor

*⚠️ PRECAUCIONES DE OBRA:*
• Cortar el magnetotérmico antes de manipular el cableado.
• En C-WALL es OBLIGATORIO disponer de neutro en la caja de 60mm.
• En C-PULSAR NUNCA meter 230V al pulsador de marco (baja tensión 3.3V).

_Generado desde el Buscador de Manuales IoT Fenster_`;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textoWp).then(() => {
          const original = btnSimWhatsapp.innerHTML;
          btnSimWhatsapp.innerHTML = "<span>✅</span> ¡Copiado para WhatsApp!";
          setTimeout(() => { btnSimWhatsapp.innerHTML = original; }, 3000);
        });
      } else {
        alert("Copia el texto:\n\n" + textoWp);
      }
    });
  }

  // Descargar SVG Vectorial
  const btnDescargarSvg = document.getElementById("sim-btn-descargar-svg");
  if (btnDescargarSvg) {
    btnDescargarSvg.addEventListener("click", () => {
      const svgEl = document.getElementById("sim-svg-canvas");
      if (!svgEl) return;
      const serializer = new XMLSerializer();
      let source = serializer.serializeToString(svgEl);
      if (!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)) {
        source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
      }
      const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `esquema-${simSelectDispositivo.value}-230v.svg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  // Modo Pantalla Completa / Vista Grande del Esquema
  const simDiagramCard = document.getElementById("sim-diagram-card");
  const btnSimFullscreen = document.getElementById("btn-sim-fullscreen");
  const simFsIcon = document.getElementById("sim-fs-icon");
  const simFsTexto = document.getElementById("sim-fs-texto");
  const simFsManiobra = document.getElementById("sim-fullscreen-maniobra");

  const btnSimFsSubir = document.getElementById("btn-sim-fs-subir");
  const btnSimFsBajar = document.getElementById("btn-sim-fs-bajar");
  const btnSimFsParar = document.getElementById("btn-sim-fs-parar");

  let esFullscreen = false;

  function alternarFullscreenEsquema() {
    esFullscreen = !esFullscreen;
    if (simDiagramCard) {
      simDiagramCard.classList.toggle("esquema-fullscreen", esFullscreen);
    }
    if (simFsManiobra) {
      simFsManiobra.classList.toggle("hidden", !esFullscreen);
    }
    if (simFsIcon) {
      simFsIcon.textContent = esFullscreen ? "✕" : "⛶";
    }
    if (simFsTexto) {
      simFsTexto.textContent = esFullscreen ? "Cerrar Vista Grande (Esc)" : "Ver en Grande";
    }
    if (btnSimFullscreen) {
      if (esFullscreen) {
        btnSimFullscreen.classList.add("bg-red-500/20", "text-red-300", "border-red-500/40");
        btnSimFullscreen.classList.remove("bg-iot-bg", "text-iot-tealLight");
      } else {
        btnSimFullscreen.classList.remove("bg-red-500/20", "text-red-300", "border-red-500/40");
        btnSimFullscreen.classList.add("bg-iot-bg", "text-iot-tealLight");
      }
    }
  }

  if (btnSimFullscreen) {
    btnSimFullscreen.addEventListener("click", alternarFullscreenEsquema);
  }

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && esFullscreen) {
      alternarFullscreenEsquema();
    }
  });

  if (btnSimFsSubir) {
    btnSimFsSubir.addEventListener("click", () => {
      simEstadoActual = "subiendo";
      actualizarSimulador();
    });
  }
  if (btnSimFsBajar) {
    btnSimFsBajar.addEventListener("click", () => {
      simEstadoActual = "bajando";
      actualizarSimulador();
    });
  }
  if (btnSimFsParar) {
    btnSimFsParar.addEventListener("click", () => {
      simEstadoActual = "reposo";
      actualizarSimulador();
    });
  }

  // 3. Modo Dual: Wizard Interactivo vs Catálogo Directo
  const btnTriageModoWizard = document.getElementById("btn-triage-modo-wizard");
  const btnTriageModoCatalogo = document.getElementById("btn-triage-modo-catalogo");
  const triageModoWizard = document.getElementById("triage-modo-wizard");
  const triageModoCatalogo = document.getElementById("triage-modo-catalogo");

  function alternarModoTriage(modo) {
    if (modo === "wizard") {
      if (btnTriageModoWizard) {
        btnTriageModoWizard.classList.add("bg-iot-teal", "text-white");
        btnTriageModoWizard.classList.remove("text-iot-textSec");
      }
      if (btnTriageModoCatalogo) {
        btnTriageModoCatalogo.classList.remove("bg-iot-teal", "text-white");
        btnTriageModoCatalogo.classList.add("text-iot-textSec");
      }
      if (triageModoWizard) triageModoWizard.classList.remove("hidden");
      if (triageModoCatalogo) triageModoCatalogo.classList.add("hidden");
    } else {
      if (btnTriageModoCatalogo) {
        btnTriageModoCatalogo.classList.add("bg-iot-teal", "text-white");
        btnTriageModoCatalogo.classList.remove("text-iot-textSec");
      }
      if (btnTriageModoWizard) {
        btnTriageModoWizard.classList.remove("bg-iot-teal", "text-white");
        btnTriageModoWizard.classList.add("text-iot-textSec");
      }
      if (triageModoCatalogo) triageModoCatalogo.classList.remove("hidden");
      if (triageModoWizard) triageModoWizard.classList.add("hidden");
    }
  }

  if (btnTriageModoWizard) btnTriageModoWizard.addEventListener("click", () => alternarModoTriage("wizard"));
  if (btnTriageModoCatalogo) btnTriageModoCatalogo.addEventListener("click", () => alternarModoTriage("catalogo"));

  // 4. Árbol de Decisión del Wizard de Soporte (Llamadas SAT)
  const WIZARD_PASOS = {
    inicio: {
      contador: "Paso 1 de 3",
      titulo: "¿Qué comportamiento o síntoma describe el instalador?",
      subtitulo: "Selecciona el área principal donde se manifiesta el problema en la ventana.",
      progreso: "33%",
      opciones: [
        {
          id: "alimentacion",
          icono: "💡",
          titulo: "Alimentación / LED de Estado",
          desc: "Dispositivo completamente apagado, parpadeo rápido continuo o parpadeos intermitentes.",
          siguiente: "rama_alimentacion"
        },
        {
          id: "motor",
          icono: "⚙️",
          titulo: "Movimiento / Motor Tubular",
          desc: "Gira al revés, el relé suena pero no se mueve, se atasca a mitad o golpea en los topes.",
          siguiente: "rama_motor"
        },
        {
          id: "wifi",
          icono: "📶",
          titulo: "Wi-Fi / Red & Conectividad",
          desc: "No empareja con router Digi/Movistar, problemas de CG-NAT, o desconexión aleatoria.",
          siguiente: "rama_wifi"
        },
        {
          id: "config",
          icono: "🔄",
          titulo: "Pulsador / Reset de Fábrica",
          desc: "Pulsador físico responde con retardo, o se requiere borrado y vuelta a modo fábrica.",
          siguiente: "rama_config"
        }
      ]
    },

    // Rama 1: Alimentación y LEDs
    rama_alimentacion: {
      contador: "Paso 2 de 3",
      titulo: "¿Cómo se comporta el LED o la electrónica?",
      subtitulo: "Pregunta al instalador qué luz o señal observa en el dispositivo.",
      progreso: "66%",
      opciones: [
        {
          id: "apagado_total",
          icono: "⚫",
          titulo: "Completamente apagado (sin luz ni zumbido)",
          desc: "No reacciona en absoluto al recibir tensión 230V.",
          siguiente: "rama_disp_apagado"
        },
        {
          id: "parpadeo_rapido",
          icono: "🔴",
          titulo: "Parpadeo rápido continuo en el pulsador o placa",
          desc: "LED parpadea constantemente sin detenerse nunca.",
          siguiente: "rama_disp_parpadeo"
        },
        {
          id: "parpadeo_2s",
          icono: "🔵",
          titulo: "Parpadeo suave cada 2 segundos",
          desc: "El equipo está esperando vinculación en modo fábrica (ventana de 60 min).",
          diagnosticoDirecto: "triage-9"
        }
      ]
    },

    rama_disp_apagado: {
      contador: "Paso 3 de 3",
      titulo: "¿Qué dispositivo físico tiene instalado?",
      subtitulo: "Identifica el modelo de controlador IoT Fenster en la ventana.",
      progreso: "90%",
      opciones: [
        {
          id: "cwall_apagado",
          icono: "🧱",
          titulo: "C-WALL (Mecanismo de pared empotrado 60mm)",
          desc: "Sustituye a un interruptor clásico en caja redonda de mecanismo.",
          diagnosticoDirecto: "triage-5"
        },
        {
          id: "connect_apagado",
          icono: "📦",
          titulo: "CONNECT-1 o CONNECT-2 (En cajón o marco)",
          desc: "Módulo oculto en el cajón de persiana o en el perfil de aluminio.",
          diagnosticoDirecto: "triage-4"
        }
      ]
    },

    rama_disp_parpadeo: {
      contador: "Paso 3 de 3",
      titulo: "¿Dónde se produce el parpadeo rápido continuo?",
      subtitulo: "Diferencia entre el pulsador de marco y el controlador de cajón.",
      progreso: "90%",
      opciones: [
        {
          id: "cpulsar_parpadeo",
          icono: "🪟",
          titulo: "C-PULSAR (Pulsador táctil en el perfil de marco)",
          desc: "El botón del marco parpadea permanentemente en rojo/azul y no obedece.",
          diagnosticoDirecto: "triage-2"
        },
        {
          id: "connect_parpadeo",
          icono: "⚡",
          titulo: "CONNECT-1 / CONNECT-2 (LED parpadea en rojo en cajón)",
          desc: "El motor se paró bruscamente y la electrónica parpadea en rojo.",
          diagnosticoDirecto: "triage-8"
        }
      ]
    },

    // Rama 2: Movimiento y Motor
    rama_motor: {
      contador: "Paso 2 de 2",
      titulo: "¿Cuál es el fallo exacto de maniobra del motor?",
      subtitulo: "Observa qué ocurre cuando se pulsa la orden de subir o bajar.",
      progreso: "85%",
      opciones: [
        {
          id: "giro_invertido",
          icono: "⇄",
          titulo: "Sube al pulsar bajar (giro invertido)",
          desc: "La persiana se mueve al revés de lo que indica la tecla o la app.",
          diagnosticoDirecto: "triage-1"
        },
        {
          id: "rele_clic_no_mueve",
          icono: "🔊",
          titulo: "El relé suena ('clic') pero el motor no se mueve",
          desc: "Se escucha claramente el conmutador interno pero el eje no gira.",
          diagnosticoDirecto: "triage-4"
        },
        {
          id: "atasco_medio",
          icono: "🛑",
          titulo: "Se detiene a mitad de carrera en seco",
          desc: "Frena bruscamente por sobreesfuerzo con parpadeo rojo.",
          diagnosticoDirecto: "triage-8"
        },
        {
          id: "no_frena_topes",
          icono: "🎯",
          titulo: "No frena en extremos / Golpea arriba o abajo",
          desc: "Sigue empujando en el suelo o se mete en el cajón sin detenerse.",
          diagnosticoDirecto: "triage-6"
        }
      ]
    },

    // Rama 3: Wi-Fi y Conectividad
    rama_wifi: {
      contador: "Paso 2 de 2",
      titulo: "¿En qué momento falla la conexión de red?",
      subtitulo: "Pregunta por el router del cliente y el tipo de incidencia.",
      progreso: "85%",
      opciones: [
        {
          id: "error_vinculacion_cgnat",
          icono: "🚫",
          titulo: "Fallo al vincular / Router Digi, Movistar o MásMóvil",
          desc: "No completa el registro o la operadora utiliza CG-NAT.",
          diagnosticoDirecto: "triage-3"
        },
        {
          id: "desconexion_aleatoria",
          icono: "⏳",
          titulo: "Se desconecta aleatoriamente cada pocas horas",
          desc: "Pasa a 'Fuera de línea' en la app de forma intermitente.",
          diagnosticoDirecto: "triage-10"
        }
      ]
    },

    // Rama 4: Configuración y Pulsador
    rama_config: {
      contador: "Paso 2 de 2",
      titulo: "¿Qué comportamiento o ajuste necesitas revisar?",
      subtitulo: "Ajuste de respuesta de teclas o reinicio de fábrica.",
      progreso: "85%",
      opciones: [
        {
          id: "pulsador_retardo",
          icono: "⏱️",
          titulo: "Pulsador físico responde con retardo o inversión",
          desc: "Hay que mantener pulsado para que mueva o responde varios segundos tarde.",
          diagnosticoDirecto: "triage-7"
        },
        {
          id: "reset_fabrica",
          icono: "🔄",
          titulo: "Procedimiento Oficial de Reset de Fábrica (Modo AP)",
          desc: "Restablecer de cero para cambiar de red Wi-Fi o reasignar.",
          diagnosticoDirecto: "triage-9"
        }
      ]
    }
  };

  // Elementos DOM del Wizard
  const wizardPasoContador = document.getElementById("wizard-paso-contador");
  const wizardPasoTitulo = document.getElementById("wizard-paso-titulo");
  const wizardPasoSubtitulo = document.getElementById("wizard-paso-subtitulo");
  const wizardProgresoBarra = document.getElementById("wizard-progreso-barra");
  const wizardBtnAtras = document.getElementById("wizard-btn-atras");
  const wizardBtnReiniciar = document.getElementById("wizard-btn-reiniciar");
  const wizardOpcionesContainer = document.getElementById("wizard-opciones-container");
  const wizardDiagnosticoResultado = document.getElementById("wizard-diagnostico-resultado");

  let wizardHistorial = [];
  let wizardPasoActual = "inicio";

  function renderizarWizardPaso(pasoClave) {
    wizardPasoActual = pasoClave;

    // Verificar si es un diagnóstico directo final
    if (pasoClave.startsWith("triage-")) {
      const caso = CASOS_TRIAGE_SAT.find((c) => c.id === pasoClave) || CASOS_TRIAGE_SAT[0];
      
      if (wizardPasoContador) wizardPasoContador.textContent = "Diagnóstico Confirmado";
      if (wizardPasoTitulo) wizardPasoTitulo.textContent = "Avería Diagnosticada con Éxito";
      if (wizardPasoSubtitulo) wizardPasoSubtitulo.textContent = "Indicaciones técnicas listas para dictar al instalador por teléfono o compartir por WhatsApp.";
      if (wizardProgresoBarra) wizardProgresoBarra.style.width = "100%";
      if (wizardBtnAtras) wizardBtnAtras.classList.remove("hidden");

      if (wizardOpcionesContainer) wizardOpcionesContainer.classList.add("hidden");
      if (wizardDiagnosticoResultado) {
        wizardDiagnosticoResultado.classList.remove("hidden");

        const pasosHtml = caso.solucion.map((p, idx) => `
          <li class="flex items-start gap-2.5">
            <span class="w-5 h-5 rounded-full bg-iot-teal/20 text-iot-tealLight font-mono text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">${idx + 1}</span>
            <span class="text-xs sm:text-sm text-iot-text leading-relaxed">${escapeHtml(p)}</span>
          </li>
        `).join("");

        const botonSimularHtml = caso.simPreset ? `
          <button type="button" class="btn-wizard-simular bg-iot-teal hover:bg-iot-tealLight text-white hover:text-iot-bg font-sora font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-md shadow-iot-teal/20" data-disp="${caso.simPreset.dispositivo}" data-inv="${caso.simPreset.invertir ? '1' : '0'}">
            <span>⚡</span> Ver en Simulador Eléctrico
          </button>
        ` : "";

        wizardDiagnosticoResultado.innerHTML = `
          <div class="bg-iot-bg/90 p-5 sm:p-6 rounded-2xl border border-iot-teal/40 flex flex-col gap-5 shadow-2xl animate-fade-in">
            
            <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-iot-border">
              <div class="flex items-center gap-2">
                <span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full text-xs font-mono font-bold flex items-center gap-1.5">
                  <span>🎯</span> Probabilidad de Acierto: 98%
                </span>
                <span class="text-xs font-mono text-iot-textSec bg-iot-panel px-2.5 py-1 rounded border border-iot-border">
                  ${escapeHtml(caso.dispositivo)}
                </span>
              </div>
              <span class="text-xs font-mono text-iot-tealLight">
                ${escapeHtml(caso.categoriaNombre)}
              </span>
            </div>

            <div>
              <h3 class="text-lg sm:text-xl font-sora font-bold text-iot-text mb-2">
                ${escapeHtml(caso.titulo)}
              </h3>
              <p class="text-xs sm:text-sm text-iot-textSec leading-relaxed">
                <strong class="text-amber-400">Síntoma verificado:</strong> ${escapeHtml(caso.sintoma)}
              </p>
            </div>

            <div class="bg-red-500/10 p-4 rounded-xl border border-red-500/25 text-red-300 text-xs sm:text-sm">
              <strong class="text-red-400 block mb-1">🔍 Causa Raíz Técnica:</strong>
              ${escapeHtml(caso.causa)}
            </div>

            <div class="bg-iot-panel p-4 sm:p-5 rounded-xl border border-iot-border flex flex-col gap-3">
              <strong class="text-iot-tealLight text-xs sm:text-sm font-sora block">
                🛠️ Qué indicarle al instalador por teléfono:
              </strong>
              <ul class="flex flex-col gap-2">
                ${pasosHtml}
              </ul>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-iot-border">
              <div class="flex flex-wrap items-center gap-2.5">
                <button type="button" class="btn-wizard-whatsapp bg-emerald-600 hover:bg-emerald-500 text-white font-sora font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition-all shadow-md shadow-emerald-600/20 active:scale-95">
                  <span>📲</span> Enviar Pasos por WhatsApp
                </button>
                <button type="button" class="btn-wizard-crear-ticket bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-slate-950 font-sora font-bold px-3.5 py-2.5 rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-md shadow-amber-500/20 active:scale-95">
                  <span>📝</span> Registrar Ticket SAT
                </button>
                <button type="button" class="btn-wizard-ver-manual bg-iot-panel hover:bg-iot-hover text-iot-textSec hover:text-white border border-iot-border font-sora font-semibold px-3.5 py-2.5 rounded-xl text-xs flex items-center gap-1.5 transition-all">
                  <span>📄</span> Ver Manual Oficial (Pág. ${caso.manualPagina})
                </button>
              </div>
              <div class="flex items-center gap-2">
                ${botonSimularHtml}
                <button type="button" class="btn-wizard-nueva-consulta bg-iot-bg hover:bg-iot-hover text-iot-textSec hover:text-white border border-iot-border font-sora px-3 py-2.5 rounded-xl text-xs transition-all">
                  🔄 Nueva Consulta
                </button>
              </div>
            </div>

          </div>
        `;

        // Botón WhatsApp
        const btnWp = wizardDiagnosticoResultado.querySelector(".btn-wizard-whatsapp");
        if (btnWp) {
          btnWp.addEventListener("click", () => {
            const textoWp = `*🩺 ASISTENCIA TÉCNICA SAT - IOT FENSTER*
*Incidencia:* ${caso.titulo}
*Causa Técnica:* ${caso.causa}

*Instrucciones de resolución en obra:*
${caso.solucion.map((p, i) => `${i + 1}. ${p}`).join("\n")}

_Enviado desde el Soporte Técnico IoT Fenster_`;

            if (navigator.clipboard && navigator.clipboard.writeText) {
              navigator.clipboard.writeText(textoWp).then(() => {
                const orig = btnWp.innerHTML;
                btnWp.innerHTML = "<span>✅</span> ¡Copiado para WhatsApp!";
                setTimeout(() => { btnWp.innerHTML = orig; }, 3000);
              });
            } else {
              alert("Copia el texto:\n\n" + textoWp);
            }
          });
        }

        // Botón Registrar Ticket SAT
        const btnCrearTicket = wizardDiagnosticoResultado.querySelector(".btn-wizard-crear-ticket");
        if (btnCrearTicket) {
          btnCrearTicket.addEventListener("click", () => {
            abrirModalTicket({
              sintoma: caso.sintoma,
              diagnostico: caso.causa,
              solucion: caso.solucion.join("\n"),
              dispositivo: caso.dispositivo
            });
          });
        }

        // Botón Ver Manual
        const btnManual = wizardDiagnosticoResultado.querySelector(".btn-wizard-ver-manual");
        if (btnManual) {
          btnManual.addEventListener("click", () => {
            if (typeof abrirVisorPDF === "function") {
              abrirVisorPDF(caso.manualArchivo, caso.manualArchivo, caso.manualPagina, 1, caso.dispositivo, "tecnico");
            }
          });
        }

        // Botón Probar en Simulador
        const btnSim = wizardDiagnosticoResultado.querySelector(".btn-wizard-simular");
        if (btnSim) {
          btnSim.addEventListener("click", () => {
            const disp = btnSim.dataset.disp;
            const inv = btnSim.dataset.inv === "1";
            alternarSubvista("simulador");
            if (simSelectDispositivo) simSelectDispositivo.value = disp;
            if (simCheckInvertir) simCheckInvertir.checked = inv;
            simInvertido = inv;
            simEstadoActual = "subiendo";
            actualizarSimulador();
            window.scrollTo({ top: 120, behavior: "smooth" });
          });
        }

        // Botón Nueva Consulta
        const btnReset = wizardDiagnosticoResultado.querySelector(".btn-wizard-nueva-consulta");
        if (btnReset) {
          btnReset.addEventListener("click", () => {
            wizardHistorial = [];
            renderizarWizardPaso("inicio");
          });
        }
      }
      return;
    }

    // Es un paso de preguntas del árbol
    const pasoData = WIZARD_PASOS[pasoClave] || WIZARD_PASOS.inicio;

    if (wizardPasoContador) wizardPasoContador.textContent = pasoData.contador;
    if (wizardPasoTitulo) wizardPasoTitulo.textContent = pasoData.titulo;
    if (wizardPasoSubtitulo) wizardPasoSubtitulo.textContent = pasoData.subtitulo;
    if (wizardProgresoBarra) wizardProgresoBarra.style.width = pasoData.progreso;

    if (wizardBtnAtras) {
      if (wizardHistorial.length > 0) wizardBtnAtras.classList.remove("hidden");
      else wizardBtnAtras.classList.add("hidden");
    }

    if (wizardDiagnosticoResultado) wizardDiagnosticoResultado.classList.add("hidden");
    if (wizardOpcionesContainer) {
      wizardOpcionesContainer.classList.remove("hidden");
      wizardOpcionesContainer.innerHTML = pasoData.opciones.map((op) => `
        <button type="button" class="btn-wizard-opcion text-left p-4 sm:p-5 rounded-2xl bg-iot-bg/70 hover:bg-iot-panel border border-iot-border hover:border-iot-teal transition-all group flex flex-col justify-between gap-3 shadow-sm hover:shadow-lg active:scale-[0.98]" data-target="${op.diagnosticoDirecto || op.siguiente}">
          <div class="flex items-center gap-3">
            <span class="text-2xl sm:text-3xl p-2 rounded-xl bg-iot-panel group-hover:bg-iot-teal/15 group-hover:scale-110 transition-all shrink-0">
              ${op.icono}
            </span>
            <div>
              <h3 class="text-sm sm:text-base font-sora font-bold text-iot-text group-hover:text-iot-tealLight transition-colors">
                ${escapeHtml(op.titulo)}
              </h3>
            </div>
          </div>
          <p class="text-xs text-iot-textSec leading-relaxed pl-1">
            ${escapeHtml(op.desc)}
          </p>
          <div class="flex items-center justify-end text-xs font-mono text-iot-tealLight font-semibold pt-1 border-t border-iot-border/40 group-hover:translate-x-1 transition-transform">
            <span>Seleccionar →</span>
          </div>
        </button>
      `).join("");

      // Listeners de cada opción
      wizardOpcionesContainer.querySelectorAll(".btn-wizard-opcion").forEach((btn) => {
        btn.addEventListener("click", () => {
          const target = btn.dataset.target;
          wizardHistorial.push(pasoClave);
          renderizarWizardPaso(target);
        });
      });
    }
  }

  // Evento Botón Atrás del Wizard
  if (wizardBtnAtras) {
    wizardBtnAtras.addEventListener("click", () => {
      if (wizardHistorial.length > 0) {
        const pasoPrevio = wizardHistorial.pop();
        renderizarWizardPaso(pasoPrevio);
      }
    });
  }

  // Evento Botón Reiniciar del Wizard
  if (wizardBtnReiniciar) {
    wizardBtnReiniciar.addEventListener("click", () => {
      wizardHistorial = [];
      renderizarWizardPaso("inicio");
    });
  }

  // 5. Renderizar y Filtrar Tarjetas de Triage SAT (Catálogo Directo)
  const triageGrid = document.getElementById("triage-grid-averias");
  const triageInput = document.getElementById("triage-input-busqueda");
  const triageFiltroBtns = document.querySelectorAll(".btn-triage-filtro");

  let categoriaTriageActiva = "todos";

  function renderizarTriage() {
    if (!triageGrid) return;
    const query = normalizarTexto(triageInput ? triageInput.value : "");

    const casosFiltrados = CASOS_TRIAGE_SAT.filter((caso) => {
      const cumpleCategoria = (categoriaTriageActiva === "todos" || caso.categoria === categoriaTriageActiva);
      if (!cumpleCategoria) return false;
      if (!query) return true;

      const textoBusqueda = normalizarTexto(`${caso.titulo} ${caso.sintoma} ${caso.causa} ${caso.categoriaNombre} ${caso.dispositivo}`);
      return textoBusqueda.includes(query);
    });

    if (casosFiltrados.length === 0) {
      triageGrid.innerHTML = `
        <div class="col-span-full py-12 text-center text-iot-textSec font-mono text-sm">
          🔍 No se han encontrado averías coincidentes con "<span class="text-iot-tealLight">${escapeHtml(triageInput.value)}</span>".
        </div>
      `;
      return;
    }

    triageGrid.innerHTML = casosFiltrados.map((c) => {
      const pasosHtml = c.solucion.map((p) => `<li class="flex items-start gap-2"><span>•</span><span>${escapeHtml(p)}</span></li>`).join("");
      const botonSimularHtml = c.simPreset ? `
        <button type="button" class="btn-triage-simular bg-iot-teal/15 hover:bg-iot-teal/25 text-iot-tealLight border border-iot-teal/30 px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all" data-preset-disp="${c.simPreset.dispositivo}" data-preset-inv="${c.simPreset.invertir ? '1' : '0'}">
          <span>⚡</span> Probar en Simulador
        </button>
      ` : "";

      return `
        <div class="glass-panel p-5 rounded-2xl border border-iot-border flex flex-col justify-between gap-3 shadow-md hover:border-iot-teal/50 transition-all card-triage" id="card-${c.id}">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="bg-iot-panel text-iot-tealLight border border-iot-border px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold">
                ${escapeHtml(c.categoriaNombre)}
              </span>
              <span class="text-xs font-mono text-iot-textSec bg-iot-bg px-2 py-0.5 rounded border border-iot-border">
                ${escapeHtml(c.dispositivo)}
              </span>
            </div>
            
            <h3 class="text-base font-sora font-bold text-iot-text mb-1">
              ${escapeHtml(c.titulo)}
            </h3>
            
            <p class="text-xs text-iot-textSec leading-relaxed">
              <strong class="text-amber-400">Síntoma:</strong> ${escapeHtml(c.sintoma)}
            </p>
          </div>

          <!-- Acordeón de Solución -->
          <div class="border-t border-iot-border/70 pt-3">
            <button type="button" class="btn-toggle-solucion text-xs font-mono text-iot-tealLight hover:text-white flex items-center justify-between w-full transition-colors" data-target="detalle-${c.id}">
              <span>Diagnóstico & Solución Técnica</span>
              <span class="arrow-indicator text-base">▼</span>
            </button>
            
            <div id="detalle-${c.id}" class="hidden flex flex-col gap-3 mt-3 pt-3 border-t border-iot-border/40 text-xs">
              <div class="bg-red-500/10 p-3 rounded-xl border border-red-500/20 text-red-300">
                <strong class="text-red-400 block mb-1">🔍 Causa Raíz Técnica:</strong>
                ${escapeHtml(c.causa)}
              </div>

              <div class="bg-iot-bg/80 p-3 rounded-xl border border-iot-border text-iot-text">
                <strong class="text-iot-tealLight block mb-1.5">🛠️ Procedimiento de Solución:</strong>
                <ul class="flex flex-col gap-1.5 text-iot-textSec leading-relaxed">
                  ${pasosHtml}
                </ul>
              </div>

              <div class="flex flex-wrap items-center justify-between gap-2 mt-1 pt-2 border-t border-iot-border/40">
                <button type="button" class="btn-triage-ver-manual bg-iot-panel hover:bg-iot-hover text-iot-textSec hover:text-white border border-iot-border px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all" data-manual="${c.manualArchivo}" data-pagina="${c.manualPagina}" data-disp="${c.dispositivo}">
                  <span>📄</span> ${escapeHtml(c.manualNombre)} (Pág. ${c.manualPagina})
                </button>
                ${botonSimularHtml}
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");

    // Listeners de los botones del acordeón
    triageGrid.querySelectorAll(".btn-toggle-solucion").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.target;
        const targetEl = document.getElementById(targetId);
        const arrow = btn.querySelector(".arrow-indicator");
        if (targetEl) {
          const isHidden = targetEl.classList.contains("hidden");
          targetEl.classList.toggle("hidden");
          if (arrow) arrow.textContent = isHidden ? "▲" : "▼";
        }
      });
    });

    // Listeners para abrir el PDF del manual oficial
    triageGrid.querySelectorAll(".btn-triage-ver-manual").forEach((btn) => {
      btn.addEventListener("click", () => {
        const archivo = btn.dataset.manual;
        const pag = parseInt(btn.dataset.pagina) || 1;
        const disp = btn.dataset.disp || "";
        if (typeof abrirVisorPDF === "function") {
          abrirVisorPDF(archivo, archivo, pag, 1, disp, "tecnico");
        }
      });
    });

    // Listeners para "Probar en Simulador"
    triageGrid.querySelectorAll(".btn-triage-simular").forEach((btn) => {
      btn.addEventListener("click", () => {
        const disp = btn.dataset.presetDisp;
        const inv = btn.dataset.presetInv === "1";

        // Cambiar a subpestaña de simulador
        alternarSubvista("simulador");

        // Configurar simulador
        if (simSelectDispositivo) simSelectDispositivo.value = disp;
        if (simCheckInvertir) simCheckInvertir.checked = inv;
        simInvertido = inv;
        simEstadoActual = "subiendo"; // Arrancar demostración activa
        actualizarSimulador();

        // Scroll al lienzo suavemente
        window.scrollTo({ top: 120, behavior: "smooth" });
      });
    });
  }

  // Filtrar por categoría
  triageFiltroBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      triageFiltroBtns.forEach((b) => {
        b.classList.remove("bg-iot-teal", "text-white");
        b.classList.add("bg-iot-bg", "text-iot-textSec");
      });
      btn.classList.add("bg-iot-teal", "text-white");
      btn.classList.remove("bg-iot-bg", "text-iot-textSec");
      categoriaTriageActiva = btn.dataset.categoria;
      renderizarTriage();
    });
  });

  if (triageInput) {
    triageInput.addEventListener("input", renderizarTriage);
  }

  // -------------------------------------------------------------------
  // 6. GESTIÓN MINI-CRM TICKETS SAT
  // -------------------------------------------------------------------
  const ticketsGrid = document.getElementById("tickets-sat-grid");
  const ticketsInput = document.getElementById("tickets-input-busqueda");
  const modalTicket = document.getElementById("modal-ticket-sat");
  const formTicket = document.getElementById("form-ticket-sat");
  const btnTicketNuevo = document.getElementById("btn-ticket-nuevo");
  const btnCerrarModalTicket = document.getElementById("btn-cerrar-modal-ticket");
  const btnCancelarModalTicket = document.getElementById("btn-cancelar-modal-ticket");
  const filtroEstadoBtns = document.querySelectorAll(".btn-ticket-filtro-estado");

  let estadoTicketFiltroActivo = "todos";
  let ticketsCargados = [];
  let paginaActualTickets = 1;
  const limiteTickets = 20;
  let totalTickets = 0;

  async function cargarTicketsSAT(reiniciarPagina = false) {
    if (reiniciarPagina) {
      paginaActualTickets = 1;
    }
    try {
      const q = ticketsInput ? encodeURIComponent(ticketsInput.value.trim()) : "";
      const estadoParam = estadoTicketFiltroActivo !== "todos" ? `&estado=${estadoTicketFiltroActivo}` : "";
      const offset = (paginaActualTickets - 1) * limiteTickets;
      const url = `/api/sat/tickets?q=${q}${estadoParam}&limit=${limiteTickets}&offset=${offset}`;

      const res = await fetchAuth(url);
      if (res && res.ok) {
        const headerTotal = res.headers.get("X-Total-Count");
        ticketsCargados = await res.json();
        totalTickets = headerTotal ? parseInt(headerTotal) : ticketsCargados.length;
        renderizarTickets(ticketsCargados);
        actualizarBarraPaginacion();
      } else if (res && res.status === 403) {
        if (ticketsGrid) {
          ticketsGrid.innerHTML = `
            <div class="col-span-full py-12 text-center text-amber-400 font-mono text-xs">
              ⚠️ Acceso restringido. Solo el personal técnico o administrador puede consultar los tickets SAT.
            </div>
          `;
        }
      }

      cargarStatsTickets();
    } catch (e) {
      console.error("Error al cargar tickets SAT:", e);
    }
  }
  window.cargarTicketsSAT = cargarTicketsSAT;

  function actualizarBarraPaginacion() {
    const info = document.getElementById("tickets-paginacion-info");
    const txtPag = document.getElementById("tickets-pag-actual-txt");
    const btnAnt = document.getElementById("btn-ticket-pag-anterior");
    const btnSig = document.getElementById("btn-ticket-pag-siguiente");
    const pagBar = document.getElementById("tickets-paginacion-bar");

    if (!pagBar) return;

    if (totalTickets <= 0) {
      pagBar.classList.add("hidden");
      return;
    }
    pagBar.classList.remove("hidden");

    const totalPaginas = Math.max(1, Math.ceil(totalTickets / limiteTickets));
    const inicio = ticketsCargados.length ? (paginaActualTickets - 1) * limiteTickets + 1 : 0;
    const fin = Math.min(paginaActualTickets * limiteTickets, totalTickets);

    if (info) info.textContent = `Mostrando ${inicio} - ${fin} de ${totalTickets} incidencias`;
    if (txtPag) txtPag.textContent = `${paginaActualTickets} / ${totalPaginas}`;
    if (btnAnt) btnAnt.disabled = (paginaActualTickets <= 1);
    if (btnSig) btnSig.disabled = (paginaActualTickets >= totalPaginas);
  }

  async function cargarStatsTickets() {
    try {
      const res = await fetchAuth("/api/sat/tickets/stats");
      if (res && res.ok) {
        const stats = await res.json();
        const elTotal = document.getElementById("kpi-tickets-total");
        const elEspera = document.getElementById("kpi-tickets-espera");
        const elResueltos = document.getElementById("kpi-tickets-resueltos");
        const elRma = document.getElementById("kpi-tickets-rma");
        const elSla = document.getElementById("kpi-tickets-sla");
        const elSemana = document.getElementById("kpi-tickets-semana");
        const badgeContador = document.getElementById("contador-tickets-badge");
        const tabTicketsBadge = document.getElementById("tab-tickets-badge");

        if (elTotal) elTotal.textContent = stats.total || 0;
        if (elEspera) elEspera.textContent = stats.en_espera || 0;
        if (elResueltos) elResueltos.textContent = stats.resuelto || 0;
        if (elRma) elRma.textContent = stats.rma_pendiente || 0;
        if (elSla) {
          elSla.textContent = (stats.tiempo_medio_resolucion_horas !== null && stats.tiempo_medio_resolucion_horas !== undefined)
            ? `${stats.tiempo_medio_resolucion_horas}h`
            : "N/A";
        }
        if (elSemana) elSemana.textContent = stats.esta_semana || 0;
        if (badgeContador) badgeContador.textContent = stats.en_espera || 0;

        // Badge en el navbar
        if (tabTicketsBadge) {
          const numPendientes = stats.en_espera || 0;
          if (numPendientes > 0) {
            tabTicketsBadge.textContent = numPendientes;
            tabTicketsBadge.classList.remove("hidden");
          } else {
            tabTicketsBadge.classList.add("hidden");
          }
        }
      }
    } catch (e) {
      console.error("Error al obtener stats:", e);
    }
  }
  window.cargarStatsTickets = cargarStatsTickets;

  function renderizarTickets(lista) {
    if (!ticketsGrid) return;
    if (!lista || lista.length === 0) {
      ticketsGrid.innerHTML = `
        <div class="col-span-full py-14 text-center text-iot-textSec font-mono text-sm glass-panel p-8 rounded-2xl border border-iot-border flex flex-col items-center justify-center gap-3">
          <span class="text-3xl">📭</span>
          <span>No hay tickets de asistencia registrados en este estado o filtro.</span>
          <button type="button" id="btn-empty-nuevo-ticket" class="mt-2 text-xs text-iot-tealLight hover:underline font-sora">
            + Crear primer ticket de llamada
          </button>
        </div>
      `;
      const btnEmpty = document.getElementById("btn-empty-nuevo-ticket");
      if (btnEmpty) btnEmpty.addEventListener("click", () => abrirModalTicket());
      return;
    }

    const estadoConfig = {
      en_espera: { label: "⏳ En Espera", class: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
      resuelto: { label: "✅ Resuelto", class: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
      rma_pendiente: { label: "📦 Pendiente RMA", class: "bg-purple-500/15 text-purple-300 border-purple-500/30" },
      descartado: { label: "❌ Descartado", class: "bg-slate-500/15 text-slate-400 border-slate-500/30" }
    };

    ticketsGrid.innerHTML = lista.map((t) => {
      const cfgEstado = estadoConfig[t.estado] || estadoConfig.en_espera;
      const esUrgente = t.prioridad === "urgente";
      const fechaTexto = t.fecha_creacion ? new Date(t.fecha_creacion).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" }) : "";
      const telClean = t.telefono ? t.telefono.replace(/\\s+/g, "") : "";
      const telLinkHtml = telClean ? `
        <div class="flex items-center gap-2 mt-1 text-xs">
          <a href="tel:${escapeHtml(telClean)}" class="text-cyan-400 hover:underline flex items-center gap-1 font-mono">
            <span>📞</span> ${escapeHtml(t.telefono)}
          </a>
          <a href="https://wa.me/34${escapeHtml(telClean)}" target="_blank" rel="noopener noreferrer" class="text-emerald-400 hover:underline flex items-center gap-1 font-mono">
            <span>💬</span> WhatsApp
          </a>
        </div>
      ` : "";

      const distribuidorHtml = t.distribuidor ? `
        <span class="bg-iot-panel text-iot-tealLight border border-iot-border px-2 py-0.5 rounded text-[10px] font-mono">
          ${escapeHtml(t.distribuidor)}
        </span>
      ` : "";

      return `
        <div class="glass-panel p-5 rounded-2xl border border-iot-border flex flex-col justify-between gap-4 shadow-lg hover:border-iot-teal/40 transition-all card-ticket" data-id="${t.id}">
          
          <!-- Encabezado de la Tarjeta -->
          <div>
            <div class="flex items-start justify-between gap-2 mb-2.5">
              <div class="flex items-center flex-wrap gap-2">
                <span class="font-mono text-xs font-bold text-iot-tealLight bg-iot-teal/15 px-2.5 py-1 rounded-lg border border-iot-teal/30">
                  #${escapeHtml(t.numero_ticket)}
                </span>
                <span class="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full border ${cfgEstado.class}">
                  ${cfgEstado.label}
                </span>
                ${esUrgente ? '<span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse">🚨 URGENTE</span>' : ''}
              </div>

              <span class="text-[11px] font-mono text-iot-textSec shrink-0">
                ${escapeHtml(fechaTexto)}
              </span>
            </div>

            <!-- Instalador y Obra -->
            <div class="mb-3">
              <div class="flex items-center gap-2 flex-wrap">
                <h4 class="text-base font-sora font-bold text-iot-text">
                  👤 ${escapeHtml(t.instalador)}
                </h4>
                ${distribuidorHtml}
              </div>
              ${t.obra ? `<p class="text-xs text-iot-textSec font-mono mt-0.5">📍 Obra: <strong class="text-iot-text">${escapeHtml(t.obra)}</strong></p>` : ''}
              ${telLinkHtml}
              ${t.email ? `<span class="bg-iot-bg px-2.5 py-1 rounded-lg border border-iot-border text-sky-400">✉️ ${escapeHtml(t.email)}</span>` : ''}
            </div>

            <!-- Dispositivo y Motor -->
            <div class="flex items-center gap-2 flex-wrap mb-3 text-xs font-mono">
              ${t.dispositivo ? `<span class="bg-iot-bg px-2.5 py-1 rounded-lg border border-iot-border text-iot-textSec">📟 ${escapeHtml(t.dispositivo)}</span>` : ''}
              ${t.motor ? `<span class="bg-iot-bg px-2.5 py-1 rounded-lg border border-iot-border text-iot-textSec">⚙️ ${escapeHtml(t.motor)}</span>` : ''}
            </div>

            <!-- Síntoma y Solución -->
            <div class="flex flex-col gap-2 text-xs">
              <div class="bg-red-500/10 p-3 rounded-xl border border-red-500/20 text-red-200">
                <strong class="text-red-400 block mb-0.5">⚠️ Síntoma Reportado:</strong>
                ${escapeHtml(t.sintoma)}
              </div>

              ${t.diagnostico ? `
                <div class="bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/20 text-amber-200">
                  <strong class="text-amber-400">🔍 Causa:</strong> ${escapeHtml(t.diagnostico)}
                </div>
              ` : ''}

              ${t.solucion ? `
                <div class="bg-iot-bg/90 p-3 rounded-xl border border-iot-border text-iot-text">
                  <strong class="text-iot-tealLight block mb-1">🛠️ Solución Indicada:</strong>
                  <p class="leading-relaxed text-iot-textSec whitespace-pre-line">${escapeHtml(t.solucion)}</p>
                </div>
              ` : ''}

              ${t.notas ? `
                <div class="bg-iot-panel/60 p-2.5 rounded-xl border border-iot-border/70 text-iot-textSec text-[11px] italic">
                  📝 Notas: ${escapeHtml(t.notas)}
                </div>
              ` : ''}
            </div>
          </div>

          <!-- Pie de Tarjeta: Cambio de Estado y Acciones Rápidas -->
          <div class="pt-3 border-t border-iot-border/60 flex flex-wrap items-center justify-between gap-2.5">
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-mono text-iot-textSec">Estado:</span>
              <select class="select-estado-ticket bg-iot-bg border border-iot-border rounded-lg px-2.5 py-1 text-xs text-iot-text focus:outline-none focus:border-iot-teal transition-colors" data-id="${t.id}">
                <option value="en_espera" ${t.estado === 'en_espera' ? 'selected' : ''}>⏳ En Espera</option>
                <option value="resuelto" ${t.estado === 'resuelto' ? 'selected' : ''}>✅ Resuelto</option>
                <option value="rma_pendiente" ${t.estado === 'rma_pendiente' ? 'selected' : ''}>📦 RMA</option>
                <option value="descartado" ${t.estado === 'descartado' ? 'selected' : ''}>❌ Descartado</option>
              </select>
            </div>

            <div class="flex items-center gap-1.5 flex-wrap">
              <button type="button" class="btn-ticket-detalle p-2 rounded-lg bg-iot-teal/15 hover:bg-iot-teal/25 text-iot-tealLight border border-iot-teal/30 text-xs transition-colors flex items-center gap-1 font-mono font-semibold cursor-pointer" title="Ver detalle e historial de notas" data-id="${t.id}">
                🔍 Detalle
              </button>
              <button type="button" class="btn-ticket-pdf p-2 rounded-lg bg-red-600/15 hover:bg-red-600/25 text-red-300 border border-red-500/30 text-xs transition-colors flex items-center gap-1 font-mono font-semibold" title="Descargar Ficha Oficial SAT / RMA en PDF (A4)" data-id="${t.id}" data-numero="${t.numero_ticket}">
                📄 PDF
              </button>
              <button type="button" class="btn-ticket-email p-2 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-xs transition-colors flex items-center gap-1 font-mono font-semibold" title="Enviar informe técnico en PDF por correo electrónico" data-id="${t.id}" data-email="${escapeHtml(t.email || '')}" data-numero="${t.numero_ticket}">
                📧 Email
              </button>
              <button type="button" class="btn-ticket-wp p-2 rounded-lg bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-300 border border-emerald-500/30 text-xs transition-colors" title="Copiar resumen para WhatsApp" data-id="${t.id}">
                💬 WhatsApp
              </button>
              <button type="button" class="btn-ticket-editar p-2 rounded-lg bg-iot-bg hover:bg-iot-hover text-iot-textSec hover:text-white border border-iot-border text-xs transition-colors" title="Editar ticket" data-id="${t.id}">
                ✏️ Editar
              </button>
              <button type="button" class="btn-ticket-eliminar p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs transition-colors" title="Eliminar ticket" data-id="${t.id}">
                🗑️
              </button>
            </div>
          </div>

        </div>
      `;
    }).join("");

    // Listeners del select de cambio rápido de estado
    ticketsGrid.querySelectorAll(".select-estado-ticket").forEach(sel => {
      sel.addEventListener("change", async (e) => {
        const ticketId = sel.dataset.id;
        const nuevoEstado = e.target.value;
        try {
          const res = await fetchAuth(`/api/sat/tickets/${ticketId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ estado: nuevoEstado })
          });
          if (res && res.ok) {
            cargarTicketsSAT();
          } else {
            alert("Error al actualizar el estado del ticket.");
          }
        } catch (err) {
          console.error(err);
        }
      });
    });

    // Listeners Descargar PDF Oficial A4
    ticketsGrid.querySelectorAll(".btn-ticket-pdf").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.id;
        const num = btn.dataset.numero;
        descargarPdfTicket(id, num, btn);
      });
    });

    // Listeners Enviar Email con PDF Adjunto desde Tarjeta
    ticketsGrid.querySelectorAll(".btn-ticket-email").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.id);
        const t = ticketsCargados.find(item => item.id === id);
        let destEmail = t ? (t.email || "") : (btn.dataset.email || "");

        if (!destEmail) {
          destEmail = prompt("Introduce el correo electrónico del instalador o cliente para enviar el informe PDF:");
          if (!destEmail || !destEmail.trim()) return;
        } else {
          if (!confirm(`¿Enviar el Parte SAT #${t ? t.numero_ticket : id} con PDF adjunto a ${destEmail}?`)) return;
        }

        const origHtml = btn.innerHTML;
        btn.innerHTML = "⏳ Enviando...";
        btn.disabled = true;

        try {
          const res = await fetchAuth(`/api/sat/tickets/${id}/enviar-email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: destEmail.trim() })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            btn.innerHTML = "✅ ¡Enviado!";
            setTimeout(() => {
              btn.innerHTML = origHtml;
              btn.disabled = false;
              cargarTicketsSAT();
            }, 3000);
          } else {
            alert("Resultado del envío: " + (data.resultado?.mensaje || data.resultado?.error || data.detail || "Error al enviar correo"));
            btn.innerHTML = origHtml;
            btn.disabled = false;
          }
        } catch (err) {
          console.error(err);
          alert("Error de red al enviar el correo electrónico.");
          btn.innerHTML = origHtml;
          btn.disabled = false;
        }
      });
    });

    // Listeners WhatsApp de cada tarjeta
    ticketsGrid.querySelectorAll(".btn-ticket-wp").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const t = ticketsCargados.find(item => item.id === id);
        if (!t) return;

        const texto = `*📋 TICKET SAT IOT FENSTER #${t.numero_ticket}*
👤 *Instalador:* ${t.instalador}${t.obra ? `\n📍 *Obra:* ${t.obra}` : ""}${t.dispositivo ? `\n📟 *Dispositivo:* ${t.dispositivo}` : ""}
⚠️ *Incidencia:* ${t.sintoma}
${t.diagnostico ? `🔍 *Diagnóstico:* ${t.diagnostico}\n` : ""}${t.solucion ? `🛠️ *Solución:* ${t.solucion}\n` : ""}📌 *Estado:* ${t.estado === "resuelto" ? "Resuelto" : "En Espera"}

_Soporte Técnico IoT Fenster_`;

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(texto).then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = "✅ ¡Copiado!";
            setTimeout(() => { btn.innerHTML = orig; }, 2500);
          });
        } else {
          alert(texto);
        }
      });
    });

    // Listeners Detalle / Historial
    ticketsGrid.querySelectorAll(".btn-ticket-detalle").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        abrirModalTicketDetalle(id);
      });
    });

    ticketsGrid.querySelectorAll(".card-ticket").forEach(card => {
      const h4 = card.querySelector("h4");
      if (h4) {
        h4.classList.add("cursor-pointer", "hover:text-iot-tealLight", "transition-colors");
        h4.addEventListener("click", () => {
          const id = parseInt(card.dataset.id);
          abrirModalTicketDetalle(id);
        });
      }
    });

    // Listeners Editar
    ticketsGrid.querySelectorAll(".btn-ticket-editar").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const t = ticketsCargados.find(item => item.id === id);
        if (t) abrirModalTicket(t, true);
      });
    });

    // Listeners Eliminar
    ticketsGrid.querySelectorAll(".btn-ticket-eliminar").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.id);
        const t = ticketsCargados.find(item => item.id === id);
        const num = t ? t.numero_ticket : id;
        if (!confirm(`¿Seguro que deseas eliminar el ticket #${num}?`)) return;
        try {
          const res = await fetchAuth(`/api/sat/tickets/${id}`, {
            method: "DELETE"
          });
          if (res && res.ok) {
            cargarTicketsSAT();
          } else {
            alert("No se pudo eliminar el ticket.");
          }
        } catch (err) {
          console.error(err);
        }
      });
    });
  }

  async function descargarPdfTicket(ticketId, numeroTicket, btnEl) {
    let originalHtml = "";
    if (btnEl) {
      originalHtml = btnEl.innerHTML;
      btnEl.innerHTML = "⏳ Generando...";
      btnEl.disabled = true;
    }
    try {
      const res = await fetchAuth(`/api/sat/tickets/${ticketId}/pdf`);
      if (res && res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Parte_SAT_${numeroTicket}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        if (btnEl) btnEl.innerHTML = "✅ Descargado";
      } else {
        alert("Error al generar el PDF del ticket.");
        if (btnEl) btnEl.innerHTML = originalHtml;
      }
    } catch (e) {
      console.error(e);
      alert("Error de red al descargar el PDF.");
      if (btnEl) btnEl.innerHTML = originalHtml;
    } finally {
      if (btnEl) {
        setTimeout(() => {
          btnEl.innerHTML = originalHtml;
          btnEl.disabled = false;
        }, 2000);
      }
    }
  }

  window.abrirModalTicket = abrirModalTicket;
function abrirModalTicket(datos = {}, esEdicion = false) {
    if (!modalTicket || !formTicket) return;
    const elTitulo = document.getElementById("modal-ticket-titulo");
    const elId = document.getElementById("ticket-id");
    const elInstalador = document.getElementById("ticket-instalador");
    const elEmail = document.getElementById("ticket-email");
    const elTel = document.getElementById("ticket-telefono");
    const elObra = document.getElementById("ticket-obra");
    const elDist = document.getElementById("ticket-distribuidor");
    const elDisp = document.getElementById("ticket-dispositivo");
    const elMotor = document.getElementById("ticket-motor");
    const elSintoma = document.getElementById("ticket-sintoma");
    const elDiag = document.getElementById("ticket-diagnostico");
    const elSol = document.getElementById("ticket-solucion");
    const elEstado = document.getElementById("ticket-estado");
    const elPrio = document.getElementById("ticket-prioridad");
    const elNotas = document.getElementById("ticket-notas");
    const btnEmailModal = document.getElementById("btn-ticket-enviar-email");

    if (elTitulo) elTitulo.textContent = esEdicion ? `Editar Ticket #${datos.numero_ticket || ''}` : "Nuevo Ticket de Asistencia SAT";
    if (elId) elId.value = esEdicion ? datos.id : "";
    if (elInstalador) elInstalador.value = datos.instalador || "";
    if (elEmail) elEmail.value = datos.email || "";
    if (elTel) elTel.value = datos.telefono || "";
    if (elObra) elObra.value = datos.obra || "";
    if (elDist) elDist.value = datos.distribuidor || "";
    if (elDisp) elDisp.value = datos.dispositivo || "Connect-1";
    if (elMotor) elMotor.value = datos.motor || "";
    if (elSintoma) elSintoma.value = datos.sintoma || "";
    if (elDiag) elDiag.value = datos.diagnostico || "";
    if (elSol) elSol.value = datos.solucion || "";
    if (elEstado) elEstado.value = datos.estado || "en_espera";
    if (elPrio) elPrio.value = datos.prioridad || "normal";
    if (elNotas) elNotas.value = datos.notas || "";

    if (btnEmailModal) {
      if (esEdicion && datos.id) {
        btnEmailModal.classList.remove("hidden");
        btnEmailModal.onclick = async () => {
          const correo = (elEmail ? elEmail.value.trim() : "") || prompt("Introduce el correo electrónico para enviar el PDF:");
          if (!correo) return;
          const origText = btnEmailModal.innerHTML;
          btnEmailModal.innerHTML = "⏳ Enviando...";
          btnEmailModal.disabled = true;
          try {
            const resp = await fetchAuth(`/api/sat/tickets/${datos.id}/enviar-email`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: correo })
            });
            const resData = await resp.json();
            if (resp.ok && resData.ok) {
              btnEmailModal.innerHTML = "✅ Correo Enviado";
              setTimeout(() => { btnEmailModal.innerHTML = origText; btnEmailModal.disabled = false; }, 3000);
            } else {
              alert("Error: " + (resData.resultado?.mensaje || resData.resultado?.error || "Fallo en envío"));
              btnEmailModal.innerHTML = origText;
              btnEmailModal.disabled = false;
            }
          } catch (e) {
            alert("Error de red al enviar correo.");
            btnEmailModal.innerHTML = origText;
            btnEmailModal.disabled = false;
          }
        };
      } else {
        btnEmailModal.classList.add("hidden");
      }
    }

    modalTicket.classList.remove("hidden");
    setTimeout(() => {
      if (elInstalador && !esEdicion) elInstalador.focus();
    }, 100);
  }

  function cerrarModalTicket() {
    if (modalTicket) modalTicket.classList.add("hidden");
    if (formTicket) formTicket.reset();
  }

  if (btnTicketNuevo) btnTicketNuevo.addEventListener("click", () => abrirModalTicket());
  if (btnCerrarModalTicket) btnCerrarModalTicket.addEventListener("click", cerrarModalTicket);
  if (btnCancelarModalTicket) btnCancelarModalTicket.addEventListener("click", cerrarModalTicket);

  if (modalTicket) {
    modalTicket.addEventListener("click", (e) => {
      if (e.target === modalTicket) cerrarModalTicket();
    });
  }

  if (formTicket) {
    formTicket.addEventListener("submit", async (e) => {
      e.preventDefault();
      const elId = document.getElementById("ticket-id");
      const esEdicion = !!(elId && elId.value);
      const ticketId = elId ? elId.value : "";

      const payload = {
        instalador: document.getElementById("ticket-instalador").value.trim(),
        telefono: document.getElementById("ticket-telefono").value.trim(),
        email: document.getElementById("ticket-email") ? document.getElementById("ticket-email").value.trim() : "",
        obra: document.getElementById("ticket-obra").value.trim(),
        distribuidor: document.getElementById("ticket-distribuidor").value,
        dispositivo: document.getElementById("ticket-dispositivo").value,
        motor: document.getElementById("ticket-motor").value.trim(),
        sintoma: document.getElementById("ticket-sintoma").value.trim(),
        diagnostico: document.getElementById("ticket-diagnostico").value.trim(),
        solucion: document.getElementById("ticket-solucion").value.trim(),
        estado: document.getElementById("ticket-estado").value,
        prioridad: document.getElementById("ticket-prioridad").value,
        notas: document.getElementById("ticket-notas").value.trim(),
      };

      try {
        const url = esEdicion ? `/api/sat/tickets/${ticketId}` : "/api/sat/tickets";
        const method = esEdicion ? "PUT" : "POST";
        const res = await fetchAuth(url, {
          method: method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res && res.ok) {
          cerrarModalTicket();
          if (tabTickets) tabTickets.click();
          cargarTicketsSAT();
        } else if (res) {
          const err = await res.json();
          alert("Error: " + (err.detail || "No se pudo guardar el ticket"));
        }
      } catch (err) {
        console.error(err);
        alert("Error de red al guardar el ticket");
      }
    });
  }

  // Filtros de estado de los tickets
  filtroEstadoBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filtroEstadoBtns.forEach(b => {
        b.classList.remove("bg-iot-teal", "text-white");
        b.classList.add("bg-iot-bg", "text-iot-textSec");
      });
      btn.classList.add("bg-iot-teal", "text-white");
      btn.classList.remove("bg-iot-bg", "text-iot-textSec");
      estadoTicketFiltroActivo = btn.dataset.estado;
      cargarTicketsSAT(true);
    });
  });

  // Búsqueda reactiva de tickets
  if (ticketsInput) {
    let debounceTimer;
    ticketsInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        cargarTicketsSAT(true);
      }, 250);
    });
  }

  // Paginación anterior / siguiente
  const btnPagAnt = document.getElementById("btn-ticket-pag-anterior");
  const btnPagSig = document.getElementById("btn-ticket-pag-siguiente");
  if (btnPagAnt) {
    btnPagAnt.addEventListener("click", () => {
      if (paginaActualTickets > 1) {
        paginaActualTickets--;
        cargarTicketsSAT();
      }
    });
  }
  if (btnPagSig) {
    btnPagSig.addEventListener("click", () => {
      const totalPaginas = Math.ceil(totalTickets / limiteTickets);
      if (paginaActualTickets < totalPaginas) {
        paginaActualTickets++;
        cargarTicketsSAT();
      }
    });
  }

  // Exportar listado de tickets a CSV
  const btnExportCsv = document.getElementById("btn-ticket-export-csv");
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", async () => {
      const q = ticketsInput ? encodeURIComponent(ticketsInput.value.trim()) : "";
      const estadoParam = estadoTicketFiltroActivo !== "todos" ? `&estado=${estadoTicketFiltroActivo}` : "";
      const origHtml = btnExportCsv.innerHTML;
      btnExportCsv.innerHTML = "<span>⏳</span> Exportando...";
      btnExportCsv.disabled = true;
      try {
        const res = await fetchAuth(`/api/sat/tickets/export/csv?q=${q}${estadoParam}`);
        if (res && res.ok) {
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `tickets_sat_${new Date().toISOString().slice(0,10)}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          btnExportCsv.innerHTML = "<span>✅</span> ¡Descargado!";
        } else {
          alert("Error al exportar los tickets a CSV.");
          btnExportCsv.innerHTML = origHtml;
        }
      } catch (e) {
        console.error(e);
        alert("Error de conexión al exportar CSV.");
      } finally {
        setTimeout(() => {
          btnExportCsv.innerHTML = origHtml;
          btnExportCsv.disabled = false;
        }, 1800);
      }
    });
  }

  // -------------------------------------------------------------------
  // Detalle de Ticket SAT con Historial de Eventos & Comentarios
  // -------------------------------------------------------------------
  let ticketDetalleActivoId = null;

  async function abrirModalTicketDetalle(ticketId) {
    ticketDetalleActivoId = ticketId;
    const modal = document.getElementById("modal-ticket-detalle");
    if (!modal) return;

    let ticket = ticketsCargados.find(t => t.id === ticketId);
    if (!ticket) {
      try {
        const res = await fetchAuth(`/api/sat/tickets/${ticketId}`);
        if (res && res.ok) ticket = await res.json();
      } catch (e) { console.error(e); }
    }
    if (!ticket) return;

    const elNum = document.getElementById("modal-ticket-det-num");
    const elSub = document.getElementById("modal-ticket-det-sub");
    const elInst = document.getElementById("modal-ticket-det-instalador");
    const elTel = document.getElementById("modal-ticket-det-telefono");
    const elMail = document.getElementById("modal-ticket-det-email");
    const elObra = document.getElementById("modal-ticket-det-obra");
    const elDist = document.getElementById("modal-ticket-det-distribuidor");
    const elDispMotor = document.getElementById("modal-ticket-det-disp-motor");
    const elSintoma = document.getElementById("modal-ticket-det-sintoma");
    const elDiag = document.getElementById("modal-ticket-det-diagnostico");
    const badgeEstado = document.getElementById("modal-ticket-det-badge-estado");
    const badgePrio = document.getElementById("modal-ticket-det-badge-prioridad");
    const selEstado = document.getElementById("modal-ticket-det-select-estado");

    if (elNum) elNum.textContent = ticket.numero_ticket || `#${ticket.id}`;
    if (elSub) elSub.textContent = `${ticket.dispositivo || 'Connect-1'} · ${ticket.instalador || '-'}`;
    if (elInst) elInst.textContent = ticket.instalador || "-";
    if (elTel) elTel.textContent = ticket.telefono || "-";
    if (elMail) elMail.textContent = ticket.email || "-";
    if (elObra) elObra.textContent = ticket.obra || "-";
    if (elDist) elDist.textContent = ticket.distribuidor || "-";
    if (elDispMotor) elDispMotor.textContent = `${ticket.dispositivo || '-'} / ${ticket.motor || '-'}`;
    if (elSintoma) elSintoma.textContent = ticket.sintoma || "-";
    if (elDiag) elDiag.textContent = (ticket.diagnostico ? `${ticket.diagnostico}\n\n` : '') + (ticket.solucion || '');

    if (badgePrio) {
      if (ticket.prioridad === "urgente") {
        badgePrio.classList.remove("hidden");
        badgePrio.className = "text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border bg-red-500/20 text-red-300 border-red-500/40 animate-pulse";
      } else {
        badgePrio.classList.add("hidden");
      }
    }

    if (badgeEstado) {
      badgeEstado.textContent = ticket.estado;
      badgeEstado.className = `text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
        ticket.estado === 'resuelto' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
        ticket.estado === 'rma_pendiente' ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' :
        ticket.estado === 'descartado' ? 'bg-slate-500/20 text-slate-300 border-slate-500/40' :
        'bg-amber-500/20 text-amber-300 border-amber-500/40'
      }`;
    }
    if (selEstado) selEstado.value = ticket.estado;

    const btnPdf = document.getElementById("modal-ticket-det-btn-pdf");
    if (btnPdf) {
      btnPdf.onclick = (e) => {
        e.preventDefault();
        descargarPdfTicket(ticket.id, ticket.numero_ticket);
      };
    }

    const btnEmail = document.getElementById("modal-ticket-det-btn-email");
    if (btnEmail) {
      btnEmail.onclick = async () => {
        let emailDest = ticket.email;
        if (!emailDest) {
          emailDest = prompt("Introduce el correo electrónico para enviar el parte PDF:");
          if (!emailDest || !emailDest.trim()) return;
        }
        btnEmail.disabled = true;
        btnEmail.textContent = "⏳ Enviando...";
        try {
          const res = await fetchAuth(`/api/sat/tickets/${ticket.id}/enviar-email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailDest.trim() })
          });
          const d = await res.json();
          if (res.ok && d.ok) {
            btnEmail.textContent = "✅ ¡Enviado!";
            setTimeout(() => { btnEmail.textContent = "📧 Reenviar Email"; btnEmail.disabled = false; }, 2000);
            cargarComentariosTicket(ticket.id);
          } else {
            alert("Error al enviar email: " + (d.detail || "Error en el servidor"));
            btnEmail.textContent = "📧 Reenviar Email";
            btnEmail.disabled = false;
          }
        } catch (e) {
          btnEmail.textContent = "📧 Reenviar Email";
          btnEmail.disabled = false;
        }
      };
    }

    cargarComentariosTicket(ticket.id);

    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  async function cargarComentariosTicket(ticketId) {
    const container = document.getElementById("modal-ticket-timeline-container");
    const numEl = document.getElementById("modal-ticket-det-num-comentarios");
    if (!container) return;

    container.innerHTML = `<div class="text-iot-textSec font-mono text-center py-4 text-xs">Cargando historial...</div>`;
    try {
      const res = await fetchAuth(`/api/sat/tickets/${ticketId}/comentarios`);
      if (res && res.ok) {
        const comentarios = await res.json();
        if (numEl) numEl.textContent = `${comentarios.length} eventos`;

        if (!comentarios || comentarios.length === 0) {
          container.innerHTML = `<div class="text-iot-textSec text-center py-6 text-xs italic">Sin notas ni eventos registrados aún.</div>`;
          return;
        }

        const iconMap = {
          creacion: "📋",
          cambio_estado: "🔄",
          email_enviado: "📧",
          nota: "📝",
          seguimiento: "📞",
          taller: "🔧"
        };

        container.innerHTML = comentarios.map(c => {
          const icon = iconMap[c.tipo] || "💬";
          const fechaStr = c.fecha ? new Date(c.fecha).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" }) : "";
          const autorStr = c.autor ? c.autor.split("@")[0] : "Sistema";

          let badgeClass = "bg-iot-bg text-iot-textSec border-iot-border";
          if (c.tipo === "cambio_estado") badgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/30";
          else if (c.tipo === "email_enviado") badgeClass = "bg-sky-500/10 text-sky-300 border-sky-500/30";
          else if (c.tipo === "creacion") badgeClass = "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";

          return `
            <div class="p-2.5 rounded-xl border ${badgeClass} flex flex-col gap-1 shadow-sm">
              <div class="flex items-center justify-between text-[10px] font-mono">
                <span class="font-bold flex items-center gap-1">${icon} ${escapeHtml(autorStr)}</span>
                <span class="opacity-70">${escapeHtml(fechaStr)}</span>
              </div>
              <p class="text-xs text-iot-text leading-relaxed whitespace-pre-wrap">${escapeHtml(c.texto)}</p>
            </div>
          `;
        }).join("");
        container.scrollTop = container.scrollHeight;
      }
    } catch (e) {
      console.error(e);
      container.innerHTML = `<div class="text-red-400 text-center py-4 text-xs">Error al cargar historial.</div>`;
    }
  }

  // Listeners del modal detalle
  const btnCerrarModalTicketDet = document.getElementById("btn-cerrar-modal-ticket-det");
  if (btnCerrarModalTicketDet) {
    btnCerrarModalTicketDet.addEventListener("click", () => {
      const modal = document.getElementById("modal-ticket-detalle");
      if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
      }
    });
  }

  const modalTicketDetalle = document.getElementById("modal-ticket-detalle");
  if (modalTicketDetalle) {
    modalTicketDetalle.addEventListener("click", (e) => {
      if (e.target === modalTicketDetalle) {
        modalTicketDetalle.classList.add("hidden");
        modalTicketDetalle.classList.remove("flex");
      }
    });
  }

  const btnPublicarComentario = document.getElementById("btn-guardar-ticket-comentario");
  if (btnPublicarComentario) {
    btnPublicarComentario.addEventListener("click", async () => {
      if (!ticketDetalleActivoId) return;
      const txtArea = document.getElementById("modal-ticket-nuevo-comentario-txt");
      const tipoSel = document.getElementById("modal-ticket-tipo-comentario");
      const texto = txtArea ? txtArea.value.trim() : "";
      const tipo = tipoSel ? tipoSel.value : "nota";
      if (!texto) return;

      btnPublicarComentario.disabled = true;
      try {
        const res = await fetchAuth(`/api/sat/tickets/${ticketDetalleActivoId}/comentarios`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto: texto, tipo: tipo })
        });
        if (res && res.ok) {
          if (txtArea) txtArea.value = "";
          cargarComentariosTicket(ticketDetalleActivoId);
        } else {
          alert("Error al agregar la nota.");
        }
      } catch (e) {
        console.error(e);
      } finally {
        btnPublicarComentario.disabled = false;
      }
    });
  }

  const selDetEstado = document.getElementById("modal-ticket-det-select-estado");
  if (selDetEstado) {
    selDetEstado.addEventListener("change", async (e) => {
      if (!ticketDetalleActivoId) return;
      const nuevoEstado = e.target.value;
      try {
        const res = await fetchAuth(`/api/sat/tickets/${ticketDetalleActivoId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ estado: nuevoEstado })
        });
        if (res && res.ok) {
          cargarTicketsSAT();
          cargarComentariosTicket(ticketDetalleActivoId);
          const badgeEstado = document.getElementById("modal-ticket-det-badge-estado");
          if (badgeEstado) {
            badgeEstado.textContent = nuevoEstado;
            badgeEstado.className = `text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
              nuevoEstado === 'resuelto' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
              nuevoEstado === 'rma_pendiente' ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' :
              nuevoEstado === 'descartado' ? 'bg-slate-500/20 text-slate-300 border-slate-500/40' :
              'bg-amber-500/20 text-amber-300 border-amber-500/40'
            }`;
          }
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  // -------------------------------------------------------------------
  // -------------------------------------------------------------------
  // 3. MÓDULO INTERACTIVO: COMENZAR ASISTENCIA SAT (12 MÓDULOS)
  // -------------------------------------------------------------------
  let currentAsistenciaData = null;
  let debounceTimerAsistencia = null;

  function inicializarModuloAsistencia() {
    const container = document.getElementById("subvista-asistencia");
    if (!container) return;

    // Single choice buttons (.btn-asist-choice)
    const choiceBtns = container.querySelectorAll(".btn-asist-choice");
    choiceBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const parent = btn.parentElement;
        if (parent) {
          parent.querySelectorAll(".btn-asist-choice").forEach(b => {
            b.classList.remove("bg-iot-teal", "text-white", "border-iot-teal", "shadow-sm");
            b.classList.add("bg-iot-bg", "text-iot-textSec", "border-iot-border");
          });
        }
        btn.classList.remove("bg-iot-bg", "text-iot-textSec", "border-iot-border");
        btn.classList.add("bg-iot-teal", "text-white", "border-iot-teal", "shadow-sm");

        const field = btn.dataset.field;
        const val = btn.dataset.value;

        // React to partner choice
        if (field === "partner") {
          const alertBox = document.getElementById("asist-alerta-partner");
          const txtEq = document.getElementById("asist-texto-equivalencia");
          const inputMod = document.getElementById("asist-input-modelo-comercial");
          if (val && (val.includes("GreenTeQ") || val.includes("VBH"))) {
            if (alertBox) alertBox.classList.remove("hidden");
            if (txtEq) txtEq.textContent = "Equivalencia detectada: VBH GreenTeQ Wave 1/2 = Connect-1/2";
            if (inputMod) inputMod.value = "GreenTeQ Wave 1";
          } else if (val && (val.includes("ICON") || val.includes("Procomsa"))) {
            if (alertBox) alertBox.classList.remove("hidden");
            if (txtEq) txtEq.textContent = "Equivalencia detectada: Procomsa ICON 1/2 = Connect-1/2";
            if (inputMod) inputMod.value = "ICON 1";
          } else if (val && (val.includes("Kömmerling") || val.includes("Konect"))) {
            if (alertBox) alertBox.classList.remove("hidden");
            if (txtEq) txtEq.textContent = "Equivalencia detectada: Kömmerling Konect Box / Shutter";
            if (inputMod) inputMod.value = "Konect Shutter";
          } else {
            if (alertBox) alertBox.classList.add("hidden");
            if (inputMod) inputMod.value = "";
          }
        }

        // Update state matrix notice
        actualizarAvisoInferencia();

        // Trigger debounced evaluation
        ejecutarEvaluacionAsistenciaDebounced();
      });
    });

    // Multiple symptoms buttons (.btn-asist-sintoma)
    const sintomaBtns = container.querySelectorAll(".btn-asist-sintoma");
    sintomaBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        btn.classList.toggle("is-checked");
        const checkIcon = btn.querySelector(".check-icon");
        if (btn.classList.contains("is-checked")) {
          btn.classList.remove("bg-iot-bg", "text-iot-textSec", "border-iot-border");
          btn.classList.add("bg-iot-teal/20", "text-iot-tealLight", "border-iot-teal/60", "font-bold");
          if (checkIcon) {
            checkIcon.textContent = "✓";
            checkIcon.classList.add("bg-iot-teal", "text-slate-950", "border-iot-teal");
          }
        } else {
          btn.classList.remove("bg-iot-teal/20", "text-iot-tealLight", "border-iot-teal/60", "font-bold");
          btn.classList.add("bg-iot-bg", "text-iot-textSec", "border-iot-border");
          if (checkIcon) {
            checkIcon.textContent = "";
            checkIcon.classList.remove("bg-iot-teal", "text-slate-950", "border-iot-teal");
          }
        }
        ejecutarEvaluacionAsistenciaDebounced();
      });
    });

    // Device dropdown
    const selectDisp = document.getElementById("asist-select-dispositivo");
    if (selectDisp) {
      selectDisp.addEventListener("change", (e) => {
        const disp = e.target.value;
        const lbl = document.getElementById("asist-lbl-disp-especifico");
        if (lbl) lbl.textContent = disp;

        const fC1 = document.getElementById("asist-funcional-c1");
        const fC2 = document.getElementById("asist-funcional-c2");
        const fCwall = document.getElementById("asist-funcional-cwall");
        const fWalarm = document.getElementById("asist-funcional-walarm");

        if (fC1) fC1.classList.toggle("hidden", disp !== "Connect-1");
        if (fC2) fC2.classList.toggle("hidden", disp !== "Connect-2");
        if (fCwall) fCwall.classList.toggle("hidden", disp !== "C-Wall");
        if (fWalarm) fWalarm.classList.toggle("hidden", disp !== "WAlarm");

        ejecutarEvaluacionAsistenciaDebounced();
      });
    }

    // Inputs, selects & checkboxes with change listeners
    const otherInputs = container.querySelectorAll("select, input[type='checkbox'], input[type='radio'], input[type='text'], textarea");
    otherInputs.forEach(input => {
      input.addEventListener("input", () => ejecutarEvaluacionAsistenciaDebounced());
      input.addEventListener("change", () => ejecutarEvaluacionAsistenciaDebounced());
    });

    // Botón Reiniciar
    const btnLimpiar = document.getElementById("btn-asist-limpiar");
    if (btnLimpiar) {
      btnLimpiar.addEventListener("click", () => {
        sintomaBtns.forEach(btn => {
          btn.classList.remove("is-checked", "bg-iot-teal/20", "text-iot-tealLight", "border-iot-teal/60", "font-bold");
          btn.classList.add("bg-iot-bg", "text-iot-textSec", "border-iot-border");
          const checkIcon = btn.querySelector(".check-icon");
          if (checkIcon) {
            checkIcon.textContent = "";
            checkIcon.classList.remove("bg-iot-teal", "text-slate-950", "border-iot-teal");
          }
        });
        const txt = document.getElementById("asist-textarea-descripcion");
        if (txt) txt.value = "";
        const mod = document.getElementById("asist-input-modelo-comercial");
        if (mod) mod.value = "";
        container.querySelectorAll(".chk-asist-accion").forEach(c => c.checked = false);
        ejecutarEvaluacionAsistencia();
      });
    }

    // Botón Descargar Dictamen en PDF Oficial Directo (Sin requerir email)
    const btnDescargarPdf = document.getElementById("btn-asist-descargar-pdf");
    if (btnDescargarPdf) {
      btnDescargarPdf.addEventListener("click", async () => {
        const inputInstalador = document.getElementById("asist-input-instalador");
        const inputTel = document.getElementById("asist-input-telefono");
        const inputObra = document.getElementById("asist-input-obra");
        const selectDisp = document.getElementById("asist-select-dispositivo");

        const instalador = inputInstalador?.value.trim() || "Técnico SAT";
        const telefono = inputTel?.value.trim() || "";
        const obra = inputObra?.value.trim() || "";
        const dispositivo = selectDisp ? selectDisp.value : "Connect-1";

        const prefill = (currentAsistenciaData && currentAsistenciaData.ticket_prefill) ? currentAsistenciaData.ticket_prefill : {};
        const diagTitulo = (currentAsistenciaData && currentAsistenciaData.diagnostico_titulo) || prefill.sintoma || "Incidencia técnica diagnosticada";
        const diagCausa = (currentAsistenciaData && currentAsistenciaData.causa_raiz) || prefill.diagnostico || "";
        const pasosTexto = (currentAsistenciaData && currentAsistenciaData.pasos_accion) 
          ? currentAsistenciaData.pasos_accion.map((p, idx) => `${idx + 1}. ${p.paso}`).join("\n")
          : (prefill.solucion || "");

        const partnerVal = container.querySelector("#asist-group-partner .btn-asist-choice.bg-iot-teal")?.dataset.value || "";

        const payload = {
          instalador: instalador,
          email: "",
          telefono: telefono || prefill.telefono || "",
          obra: obra || prefill.obra || "",
          distribuidor: partnerVal || prefill.distribuidor || "",
          dispositivo: dispositivo || prefill.dispositivo || "Connect-1",
          motor: prefill.motor || "",
          sintoma: diagTitulo,
          diagnostico: diagCausa,
          solucion: pasosTexto,
          estado: "resuelto",
          prioridad: "normal",
          notas: `Dictamen técnico generado desde Asistencia SAT.`,
          enviar_email: false,
          manual_info: currentAsistenciaData ? currentAsistenciaData.manual_recomendado : null
        };

        const origHtml = btnDescargarPdf.innerHTML;
        btnDescargarPdf.innerHTML = `
          <svg class="animate-spin w-4 h-4 text-slate-950 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Generando PDF...</span>
        `;
        btnDescargarPdf.disabled = true;

        try {
          const res = await fetchAuth("/api/sat/tickets/auto-registrar-enviar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al generar el PDF");
          }

          const data = await res.json();
          const ticket = data.ticket;

          if (data.pdf_url) {
            const resPdf = await fetchAuth(data.pdf_url);
            if (resPdf.ok) {
              const blob = await resPdf.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = data.pdf_filename || `Parte_SAT_${ticket.numero_ticket}.pdf`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              window.URL.revokeObjectURL(url);
            }
          }

          btnDescargarPdf.innerHTML = `<span>✅</span> ¡PDF Descargado!`;
          setTimeout(() => {
            btnDescargarPdf.innerHTML = origHtml;
            btnDescargarPdf.disabled = false;
          }, 3000);

          cargarStatsTickets();
        } catch (err) {
          console.error(err);
          alert("Error al descargar PDF: " + err.message);
          btnDescargarPdf.innerHTML = origHtml;
          btnDescargarPdf.disabled = false;
        }
      });
    }

    // Botón Guardar en Tickets SAT
    const btnGuardarTicket = document.getElementById("btn-asist-guardar-ticket");
    if (btnGuardarTicket) {
      btnGuardarTicket.addEventListener("click", async () => {
        const inputInstalador = document.getElementById("asist-input-instalador");
        const inputTel = document.getElementById("asist-input-telefono");
        const inputObra = document.getElementById("asist-input-obra");
        const selectDisp = document.getElementById("asist-select-dispositivo");

        let instalador = inputInstalador?.value.trim() || "";
        if (!instalador) {
          instalador = prompt("Introduce el nombre del instalador o cliente:") || "Instalador SAT";
          if (inputInstalador) inputInstalador.value = instalador;
        }

        const prefill = (currentAsistenciaData && currentAsistenciaData.ticket_prefill) ? currentAsistenciaData.ticket_prefill : {};
        const diagTitulo = (currentAsistenciaData && currentAsistenciaData.diagnostico_titulo) || prefill.sintoma || "Incidencia técnica diagnosticada";
        const diagCausa = (currentAsistenciaData && currentAsistenciaData.causa_raiz) || prefill.diagnostico || "";
        const pasosTexto = (currentAsistenciaData && currentAsistenciaData.pasos_accion) 
          ? currentAsistenciaData.pasos_accion.map((p, idx) => `${idx + 1}. ${p.paso}`).join("\n")
          : (prefill.solucion || "");

        const partnerVal = container.querySelector("#asist-group-partner .btn-asist-choice.bg-iot-teal")?.dataset.value || "";

        const payload = {
          instalador: instalador,
          email: "",
          telefono: inputTel?.value.trim() || prefill.telefono || "",
          obra: inputObra?.value.trim() || prefill.obra || "",
          distribuidor: partnerVal || prefill.distribuidor || "",
          dispositivo: (selectDisp ? selectDisp.value : "Connect-1") || prefill.dispositivo || "Connect-1",
          motor: prefill.motor || "",
          sintoma: diagTitulo,
          diagnostico: diagCausa,
          solucion: pasosTexto,
          estado: "en_espera",
          prioridad: "normal",
          notas: `Ticket registrado desde Asistencia SAT para seguimiento técnico.`,
          enviar_email: false,
          manual_info: currentAsistenciaData ? currentAsistenciaData.manual_recomendado : null
        };

        const origHtml = btnGuardarTicket.innerHTML;
        btnGuardarTicket.innerHTML = "<span>⏳ Guardando...</span>";
        btnGuardarTicket.disabled = true;

        try {
          const res = await fetchAuth("/api/sat/tickets/auto-registrar-enviar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          if (!res.ok) throw new Error("No se pudo registrar el ticket");
          const data = await res.json();
          const ticket = data.ticket;

          btnGuardarTicket.innerHTML = `<span>✅</span> Guardado #${ticket.numero_ticket}`;
          
          setTimeout(() => {
            btnGuardarTicket.innerHTML = origHtml;
            btnGuardarTicket.disabled = false;
            if (tabTickets) tabTickets.click();
            cargarTicketsSAT();
          }, 1000);

        } catch (e) {
          alert("Error: " + e.message);
          btnGuardarTicket.innerHTML = origHtml;
          btnGuardarTicket.disabled = false;
        }
      });
    }

    // Botón Copiar WhatsApp
    const btnWhatsApp = document.getElementById("btn-asist-copiar-whatsapp");
    if (btnWhatsApp) {
      btnWhatsApp.addEventListener("click", () => {
        if (!currentAsistenciaData) {
          alert("No hay diagnóstico generado.");
          return;
        }

        const titulo = currentAsistenciaData.diagnostico_titulo || "Dictamen Técnico SAT";
        const causa = currentAsistenciaData.causa_raiz || "";
        const pasos = (currentAsistenciaData.pasos_accion || []).map((p, idx) => `${idx + 1}. ${p.paso}`).join("\n");
        const manual = currentAsistenciaData.manual_recomendado ? `\n\n📄 *Manual Oficial:* ${currentAsistenciaData.manual_recomendado.nombre} (Pág. ${currentAsistenciaData.manual_recomendado.pagina})` : "";

        const textoWp = currentAsistenciaData.whatsapp_template || `*🩺 RESOLUCIÓN TÉCNICA SAT - IOT FENSTER*
*Incidencia:* ${titulo}
*Causa Raíz:* ${causa}

*🛠️ Pasos de Resolución:*
${pasos}${manual}

_Generado desde el Buscador de Manuales IoT Fenster_`;

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textoWp).then(() => {
            const orig = btnWhatsApp.innerHTML;
            btnWhatsApp.innerHTML = "<span>✅</span> ¡Copiado!";
            setTimeout(() => { btnWhatsApp.innerHTML = orig; }, 2500);
          }).catch(() => {
            alert(textoWp);
          });
        } else {
          alert(textoWp);
        }
      });
    }

    // Botón Abrir Simulador
    const btnAbrirSim = document.getElementById("btn-asist-abrir-simulador");
    if (btnAbrirSim) {
      btnAbrirSim.addEventListener("click", () => {
        abrirVistaDirecta("esquemas");
      });
    }

    // Botón Ver Manual PDF
    const btnVerManual = document.getElementById("btn-asist-ver-manual");
    if (btnVerManual) {
      btnVerManual.addEventListener("click", () => {
        if (currentAsistenciaData && currentAsistenciaData.manual_recomendado) {
          const man = currentAsistenciaData.manual_recomendado;
          if (typeof abrirVisorPDF === "function") {
            abrirVisorPDF(man.nombre || man.archivo, man.archivo, man.pagina || 1, 1, man.dispositivo || "", "tecnico");
          } else {
            window.open(`/manuales/${encodeURIComponent(man.archivo)}#page=${man.pagina}`, "_blank");
          }
        }
      });
    }

    // Primera evaluación inicial automática
    ejecutarEvaluacionAsistencia();
  }

  function actualizarAvisoInferencia() {
    const container = document.getElementById("subvista-asistencia");
    if (!container) return;

    const btnFisico = container.querySelector("#asist-group-control-fisico .btn-asist-choice.bg-iot-teal");
    const btnApp = container.querySelector("#asist-group-control-app .btn-asist-choice.bg-iot-teal");
    const btnAparicion = container.querySelector("#asist-group-app-aparicion .btn-asist-choice.bg-iot-teal");
    const inferenciaTexto = document.getElementById("asist-inferencia-texto");
    if (!inferenciaTexto) return;

    const fisico = btnFisico ? btnFisico.dataset.value : "Sí";
    const app = btnApp ? btnApp.dataset.value : "Sí";
    const aparicion = btnAparicion ? btnAparicion.dataset.value : "Sí";

    if (fisico === "Sí" && (app === "No" || aparicion === "Aparece pero offline")) {
      inferenciaTexto.textContent = "Control Físico OK + App KO ➔ Problema de conectividad, red Wi-Fi o servidor Cloud.";
    } else if (fisico === "No" && app === "No") {
      inferenciaTexto.textContent = "Control Físico KO + App KO ➔ Fallo general de alimentación 230V, fusible o motor bloqueado.";
    } else if (fisico === "No" && app === "Sí") {
      inferenciaTexto.textContent = "Control Físico KO + App OK ➔ Relés conmutan pero motor no se mueve (revisar común neutro azul o FC).";
    } else if (aparicion === "No") {
      inferenciaTexto.textContent = "App no muestra dispositivo tras vinculación ➔ Fallo de registro backend o red 5 GHz aislada.";
    } else {
      inferenciaTexto.textContent = "Control Físico OK + App OK (Parámetros normales o ajuste fino de configuración).";
    }
  }

  function ejecutarEvaluacionAsistenciaDebounced() {
    if (debounceTimerAsistencia) clearTimeout(debounceTimerAsistencia);
    debounceTimerAsistencia = setTimeout(() => {
      ejecutarEvaluacionAsistencia();
    }, 350);
  }

  async function ejecutarEvaluacionAsistencia() {
    const container = document.getElementById("subvista-asistencia");
    if (!container) return;

    const getChoiceValue = (groupId, def) => {
      const el = container.querySelector(`#${groupId} .btn-asist-choice.bg-iot-teal`);
      return el ? el.dataset.value : def;
    };

    const partner = getChoiceValue("asist-group-partner", "IoT Fenster / MySmartWindow");
    const numAfectados = getChoiceValue("asist-group-num-afectados", "1");
    const area = getChoiceValue("asist-group-area", "Dispositivo / electrónica");
    const vinculado = getChoiceValue("asist-group-vinculado", "Sí");
    const appAparicion = getChoiceValue("asist-group-app-aparicion", "Sí");
    const controlFisico = getChoiceValue("asist-group-control-fisico", "Sí");
    const controlApp = getChoiceValue("asist-group-control-app", "Sí");
    const reproducibilidad = getChoiceValue("asist-group-reproducibilidad", "Siempre");

    const selectDisp = document.getElementById("asist-select-dispositivo");
    const dispositivo = selectDisp ? selectDisp.value : "Connect-1";

    const inputModelo = document.getElementById("asist-input-modelo-comercial");
    const modeloComercial = inputModelo ? inputModelo.value.trim() : "";

    // Actualizar Chips de Contexto en Vivo en el Panel Derecho
    const chipDisp = document.getElementById("asist-chip-disp");
    const chipPartner = document.getElementById("asist-chip-partner");
    const chipControl = document.getElementById("asist-chip-control");
    const chipWifi = document.getElementById("asist-chip-wifi");

    if (chipDisp) chipDisp.textContent = modeloComercial ? `${dispositivo} (${modeloComercial})` : dispositivo;
    if (chipPartner) chipPartner.textContent = partner.split("/")[0].trim();
    if (chipControl) chipControl.textContent = `${controlFisico === 'Sí' ? 'Físico OK' : 'Físico KO'} · ${controlApp === 'Sí' ? 'App OK' : 'App KO'}`;

    // Síntomas multi-select
    const sintomas = [];
    container.querySelectorAll("#asist-sintomas-grid .btn-asist-sintoma.is-checked").forEach(b => {
      sintomas.push(b.dataset.sintoma);
    });

    // Wi-Fi
    const wifiTipo = document.getElementById("asist-wifi-tipo")?.value || "Dual 2,4/5 GHz";
    const wifiSSID = document.getElementById("asist-wifi-ssid-sep")?.value || "No";
    const wifiGen = document.getElementById("asist-wifi-gen")?.value || "Wi-Fi 5";
    const wifiSeg = document.getElementById("asist-wifi-seg")?.value || "WPA2";
    const wifiOp = document.getElementById("asist-wifi-operadora")?.value || "";
    const wifiRouter = document.getElementById("asist-wifi-router")?.value || "";
    const wifiRSSI = document.getElementById("asist-wifi-rssi")?.value || "Bueno";
    const wifiMesh = document.getElementById("asist-wifi-mesh")?.value || "Ninguno";

    if (chipWifi) chipWifi.textContent = `${wifiTipo.replace('Dual 2,4/5 GHz', 'Dual 2.4/5G')} (${wifiSeg})`;

    // App
    const appSO = getChoiceValue("asist-group-app-so", "Android");
    const appMulti = getChoiceValue("asist-group-multimovil", "No probado");
    const soVersion = document.getElementById("asist-input-so-version")?.value.trim() || "";
    const appVersion = document.getElementById("asist-input-app-version")?.value.trim() || "";
    const appAct = document.getElementById("asist-app-actualizada")?.value || "Sí";

    // Alcance
    const numTotal = document.getElementById("asist-input-num-total")?.value || "4";
    const alcanceDist = document.getElementById("asist-alcance-distribucion")?.value || "Misma habitación";
    const alcanceTam = document.getElementById("asist-alcance-tamano")?.value || "75–150 m²";
    const alcanceObs = document.getElementById("asist-alcance-obstaculos")?.value || "Tabiques";

    // Hardware checklist específica (Bloque 8)
    const infoEspecifica = {
      hw_c1: {
        controla_persiana: document.getElementById("chk-c1-controla")?.checked ?? true,
        motor_responde: document.getElementById("chk-c1-motor")?.checked ?? true,
        oyen_reles: document.getElementById("chk-c1-reles")?.checked ?? true,
        calib_termina: document.getElementById("chk-c1-calib")?.checked ?? true
      },
      hw_c2: {
        oscilo: document.getElementById("chk-c2-oscilo")?.checked ?? false,
        apertura: document.getElementById("chk-c2-apertura")?.checked ?? false,
        temp: document.getElementById("chk-c2-temp")?.checked ?? false,
        humedad: document.getElementById("chk-c2-humedad")?.checked ?? false,
        co2: document.getElementById("chk-c2-co2")?.checked ?? false,
        voc: document.getElementById("chk-c2-voc")?.checked ?? false,
        impacto: document.getElementById("chk-c2-impacto")?.checked ?? false
      },
      hw_cwall: {
        tipo_mecanismo: container.querySelector('input[name="cwall-tipo"]:checked')?.value || "Persiana"
      },
      hw_walarm: {
        sensor: document.getElementById("chk-walarm-sensor")?.checked ?? true,
        sirena: document.getElementById("chk-walarm-sirena")?.checked ?? true
      }
    };

    // Momento, Detonante & Descripción (Bloques 9, 10, 11)
    const momento = document.getElementById("asist-select-momento")?.value || "Durante uso normal";
    const detonante = document.getElementById("asist-input-detonante")?.value.trim() || "";
    const descripcion = document.getElementById("asist-textarea-descripcion")?.value || "";

    // Acciones hechas (Bloque 12)
    const acciones = [];
    container.querySelectorAll(".chk-asist-accion:checked").forEach(c => {
      acciones.push(c.value);
    });

    const payload = {
      partner: partner,
      dispositivo: dispositivo,
      modelo_comercial: modeloComercial,
      num_dispositivos_afectados: numAfectados,
      area_incidencia: area,
      estado_vinculado: vinculado,
      estado_app: appAparicion,
      estado_control_fisico: controlFisico,
      estado_control_app: controlApp,
      sintomas_observados: sintomas,
      wifi_info: {
        tipo_red: wifiTipo,
        ssid_separados: wifiSSID,
        generacion: wifiGen,
        seguridad: wifiSeg,
        operadora: wifiOp,
        router_modelo: wifiRouter,
        rssi: wifiRSSI,
        repetidor_mesh: wifiMesh
      },
      app_info: {
        so: appSO,
        version_so: soVersion,
        version_app: appVersion,
        app_actualizada: appAct,
        mas_de_un_movil: appMulti
      },
      alcance_fisico: {
        num_total_dispositivos: numTotal,
        distribucion: alcanceDist,
        tamano_vivienda: alcanceTam,
        obstaculos: alcanceObs
      },
      info_especifica: infoEspecifica,
      momento_fallo: momento,
      reproducibilidad: reproducibilidad,
      accion_detonante: detonante,
      descripcion_detallada: descripcion,
      acciones_realizadas: acciones
    };

    try {
      const res = await fetch("/api/sat/asistencia-triage", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Error en la evaluación");
      const data = await res.json();
      currentAsistenciaData = data;

      // Actualizar Panel Derecho
      const resTitulo = document.getElementById("asist-res-titulo");
      const resCausa = document.getElementById("asist-res-causa");
      const resConfianzaNum = document.getElementById("asist-res-confianza-num");
      const resConfianzaBar = document.getElementById("asist-res-confianza-bar");
      const tagsContainer = document.getElementById("asist-res-tags-container");
      const pasosContainer = document.getElementById("asist-res-pasos-container");
      const manualNombre = document.getElementById("asist-res-manual-nombre");
      const manualSub = document.getElementById("asist-res-manual-sub");

      const confianzaVal = Math.round(data.confianza || 85);
      if (resTitulo) resTitulo.textContent = data.diagnostico_titulo || "Incidencia Diagnosticada";
      if (resCausa) resCausa.textContent = data.causa_raiz || "Comprobación recomendada.";
      if (resConfianzaNum) resConfianzaNum.textContent = `${confianzaVal}%`;
      if (resConfianzaBar) resConfianzaBar.style.width = `${Math.min(100, Math.max(10, confianzaVal))}%`;

      // Renderizar Top 3 Diagnósticos Sugeridos (Feedback Loop)
      const topDiagBox = document.getElementById("asist-top-diagnosticos-box");
      const topDiagContainer = document.getElementById("asist-top-diagnosticos-container");
      if (topDiagBox && topDiagContainer) {
        if (Array.isArray(data.top_diagnosticos) && data.top_diagnosticos.length > 0) {
          topDiagBox.classList.remove("hidden");
          topDiagBox.classList.add("flex");
          topDiagContainer.innerHTML = data.top_diagnosticos.map((item, idx) => `
            <div class="p-2.5 rounded-xl bg-iot-bg/80 border border-iot-border hover:border-iot-teal/50 transition-all flex items-start justify-between gap-2 text-xs">
              <div class="min-w-0">
                <span class="font-bold text-iot-text truncate block text-[11px]">${idx + 1}. ${escapeHtml(item.titulo || item.diagnostico)}</span>
                <span class="text-[10px] text-iot-textSec line-clamp-1 mt-0.5">${escapeHtml(item.solucion || "")}</span>
              </div>
              <span class="shrink-0 text-[10px] font-mono px-2 py-0.5 rounded-md bg-iot-teal/15 text-iot-tealLight border border-iot-teal/30 font-bold">
                ${item.confianza}%
              </span>
            </div>
          `).join("");
        } else {
          topDiagBox.classList.add("hidden");
          topDiagBox.classList.remove("flex");
        }
      }

      if (tagsContainer && Array.isArray(data.tags_solucion)) {
        tagsContainer.innerHTML = data.tags_solucion.map(tag => `
          <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold bg-iot-teal/15 text-iot-tealLight border border-iot-teal/30">
            ${escapeHtml(tag)}
          </span>
        `).join("");
      }

      if (pasosContainer && Array.isArray(data.pasos_accion)) {
        let primerPendienteMarcado = false;
        pasosContainer.innerHTML = data.pasos_accion.map((p, idx) => {
          const esPendiente = !p.ya_probado;
          const esPrioritario = esPendiente && !primerPendienteMarcado;
          if (esPrioritario) primerPendienteMarcado = true;

          return `
          <div class="flex items-start gap-2.5 p-3 rounded-xl border text-xs transition-all ${
            p.ya_probado
              ? 'bg-iot-bg/40 border-iot-border/40 opacity-50'
              : esPrioritario
                ? 'bg-iot-teal/15 border-iot-teal/60 text-white shadow-md'
                : 'bg-iot-bg/80 border-iot-border text-iot-text'
          }">
            <span class="flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center font-mono font-bold text-[11px] ${
              p.ya_probado
                ? 'bg-white/10 text-iot-textSec'
                : esPrioritario
                  ? 'bg-iot-teal text-slate-950 font-extrabold shadow-sm'
                  : 'bg-iot-panel text-iot-tealLight border border-iot-border'
            }">
              ${p.ya_probado ? '✓' : idx + 1}
            </span>
            <div class="flex-1 leading-relaxed ${p.ya_probado ? 'line-through text-iot-textSec' : ''}">
              ${esPrioritario ? '<span class="inline-block px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase bg-iot-teal text-slate-950 rounded mr-1.5 align-middle shadow-sm">Recomendado</span>' : ''}
              ${escapeHtml(p.paso)}
            </div>
            ${p.ya_probado ? '<span class="text-[9px] font-mono px-2 py-0.5 rounded-full bg-white/10 text-iot-textSec uppercase font-semibold">Ya probado</span>' : ''}
          </div>
        `;
        }).join("");
      }

      if (data.manual_recomendado) {
        if (manualNombre) manualNombre.textContent = data.manual_recomendado.nombre || "Manual Oficial";
        if (manualSub) manualSub.textContent = `Página ${data.manual_recomendado.pagina || 1} • ${data.manual_recomendado.archivo || ""}`;
      }
    } catch (e) {
      console.warn("Error en evaluación de asistencia SAT:", e);
    }
  }
  window.ejecutarEvaluacionAsistencia = ejecutarEvaluacionAsistencia;

  // Ejecución inicial
  actualizarSimulador();
  renderizarWizardPaso("inicio");
  renderizarTriage();
  cargarTicketsSAT();
  cargarStatsTickets();
  inicializarModuloAsistencia();
}

// =====================================================================
// 🌐 MÓDULO LABORATORIO INTEGRAL & BANCO DE PRUEBAS UNIFICADO 230V + IOT
// =====================================================================
function inicializarLaboratorioIntegral() {
  if (typeof window.ejecutarInicializacionLaboratorio === 'function') {
    window.ejecutarInicializacionLaboratorio();
  }
}
window.inicializarLaboratorioIntegral = inicializarLaboratorioIntegral;

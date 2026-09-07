// ---------- Variables Globales y Estado ----------
let token = localStorage.getItem("iot_token");
let userRole = localStorage.getItem("iot_role");
let userEmail = localStorage.getItem("iot_email");
let isFirstLogin = false;

// ---------- Elementos de Login ----------
const loginModal = document.getElementById("login-modal");
const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");
const btnLogout = document.getElementById("btn-logout");
const userEmailDisplay = document.getElementById("user-email-display");
const userRoleDisplay = document.getElementById("user-role-display");

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
  
  if (response.status === 401 || response.status === 403) {
    cerrarSesion();
    throw new Error("No autorizado");
  }
  
  return response;
}

// ---------- Lógica de Autenticación ----------
function verificarSesion() {
  if (token && userRole && userEmail) {
    loginModal.classList.add("oculto");
    userEmailDisplay.textContent = userEmail;
    userRoleDisplay.textContent = "Rol: " + userRole;
    
    // RBAC: Mostrar u ocultar pestañas según el rol
    if (userRole === "admin") {
      tabSubir.classList.remove("hidden");
      tabBiblioteca.classList.remove("hidden");
      tabUsuarios.classList.remove("hidden");
    } else {
      tabSubir.classList.add("hidden");
      tabBiblioteca.classList.add("hidden");
      tabUsuarios.classList.add("hidden");
    }
    
    if (isFirstLogin) {
      passwordModal.classList.remove("hidden");
    }

    // Cargar datos iniciales
    cargarOpcionesFiltro();
    cargarSugerencias();
  } else {
    loginModal.classList.remove("oculto");
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

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.classList.add("hidden");
  
  const formData = new URLSearchParams();
  formData.append("username", loginEmail.value.trim());
  formData.append("password", loginPassword.value.trim());
  
  try {
    const resp = await fetch("/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });
    
    if (!resp.ok) {
      const errorData = await resp.json();
      throw new Error(errorData.detail || "Credenciales inválidas");
    }
    
    const data = await resp.json();
    token = data.access_token;
    userRole = data.role;
    userEmail = data.email;
    
    localStorage.setItem("iot_token", token);
    localStorage.setItem("iot_role", userRole);
    localStorage.setItem("iot_email", userEmail);
    
    loginEmail.value = "";
    loginPassword.value = "";

    // Revisar si es el primer login
    try {
      const respMe = await fetchAuth("/api/me");
      const meData = await respMe.json();
      if (meData.is_first_login) {
        passwordModal.classList.remove("hidden");
      }
    } catch(e) {
      console.error(e);
    }

    verificarSesion();
    
  } catch (err) {
    loginError.textContent = err.message;
    loginError.classList.remove("hidden");
  }
});

btnSkipPassword.addEventListener("click", () => {
  passwordModal.classList.add("hidden");
  isFirstLogin = false;
});

passwordForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const pwd = newPassword.value;
  if (!pwd) return;
  try {
    const resp = await fetchAuth("/api/usuarios/me/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });
    if (resp.ok) {
      passwordModal.classList.add("hidden");
      isFirstLogin = false;
      alert("Contraseña cambiada con éxito.");
    } else {
      alert("Error al cambiar contraseña.");
    }
  } catch (err) {
    alert("Error de red.");
  }
});

btnLogout.addEventListener("click", cerrarSesion);

// Iniciar app verificando sesión
verificarSesion();

// ---------- Navegación entre pestañas ----------
const pestanas = document.querySelectorAll(".pestana");
const vistas = {
  buscar: document.getElementById("vista-buscar"),
  subir: document.getElementById("vista-subir"),
  biblioteca: document.getElementById("vista-biblioteca"),
  usuarios: document.getElementById("vista-usuarios"),
};

pestanas.forEach((btn) => {
  btn.addEventListener("click", () => {
    pestanas.forEach((b) => b.classList.remove("activa"));
    btn.classList.add("activa");
    Object.values(vistas).forEach((v) => v.classList.remove("vista-activa"));
    vistas[btn.dataset.vista].classList.add("vista-activa");
    if (btn.dataset.vista === "biblioteca" && userRole === "admin") {
      cargarBiblioteca();
      cargarBibliotecaVideos();
    }
    if (btn.dataset.vista === "usuarios" && userRole === "admin") cargarUsuarios();
  });
});

// ---------- Buscar ----------
const inputBusqueda = document.getElementById("input-busqueda");
const btnBuscar = document.getElementById("btn-buscar");
const estadoBusqueda = document.getElementById("estado-busqueda");
const contenedorResultados = document.getElementById("resultados");
const filtroDispositivo = document.getElementById("filtro-dispositivo");
const filtroCategoria = document.getElementById("filtro-categoria");
const listaSugerencias = document.getElementById("lista-sugerencias");

let sugerenciasDisponibles = { nombres: [], dispositivos: [], categorias: [] };

async function cargarOpcionesFiltro() {
  try {
    const resp = await fetchAuth("/api/filtros");
    const data = await resp.json();
    filtroDispositivo.innerHTML = `<option value="">Todos los dispositivos</option>` +
      data.dispositivos.map((d) => `<option value="${d}">${d}</option>`).join("");
    filtroCategoria.innerHTML = `<option value="">Todas las categorías</option>` +
      data.categorias.map((c) => `<option value="${c}">${c}</option>`).join("");
    
    // Renderizar chips de etiquetas para soporte
    renderizarChipsEtiquetas(data.etiquetas || []);
  } catch (e) {}
}

function renderizarChipsEtiquetas(etiquetas) {
  const contenedor = document.getElementById("lista-chips-tags");
  if (!contenedor) return;

  const tagsParaMostrar = (etiquetas && etiquetas.length > 0)
    ? etiquetas
    : ["wifi", "red", "bateria", "instalacion", "conexion", "reset"];

  contenedor.innerHTML = tagsParaMostrar.map((tag) => `
    <button type="button" class="chip-tag bg-iot-panel hover:bg-iot-teal hover:text-iot-bg border border-iot-border hover:border-iot-teal text-iot-textSec hover:text-white px-3 py-1 rounded-lg text-xs font-mono transition-all flex items-center gap-1 shadow-sm active:scale-95" data-tag="${tag}">
      <span>#${tag}</span>
    </button>
  `).join("");

  contenedor.querySelectorAll(".chip-tag").forEach((btn) => {
    btn.addEventListener("click", () => {
      inputBusqueda.value = btn.dataset.tag;
      buscar();
    });
  });
}

async function cargarSugerencias() {
  try {
    const resp = await fetchAuth("/api/sugerencias");
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
  const textoNorm = texto.toLowerCase();
  const candidatos = [];

  sugerenciasDisponibles.nombres.forEach((n) => {
    if (n.toLowerCase().includes(textoNorm)) candidatos.push({ texto: n, tipo: "Manual" });
  });
  sugerenciasDisponibles.dispositivos.forEach((d) => {
    if (d.toLowerCase().includes(textoNorm)) candidatos.push({ texto: d, tipo: "Dispositivo" });
  });
  sugerenciasDisponibles.categorias.forEach((c) => {
    if (c.toLowerCase().includes(textoNorm)) candidatos.push({ texto: c, tipo: "Categoría" });
  });

  const unicos = candidatos.filter((c, i) => candidatos.findIndex((x) => x.texto === c.texto) === i).slice(0, 6);

  if (unicos.length === 0) {
    listaSugerencias.classList.remove("visible");
    return;
  }

  listaSugerencias.innerHTML = unicos
    .map((c) => `<div class="item-sugerencia px-4 py-3 cursor-pointer text-sm border-b border-iot-border last:border-0 hover:bg-iot-hover flex items-center justify-between" data-texto="${c.texto}">
      <span class="flex items-center gap-2">📄 ${c.texto}</span>
      <span class="tipo-sugerencia text-xs text-iot-tealLight bg-iot-teal/10 px-2 py-0.5 rounded-full font-mono">${c.tipo}</span>
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
  iframePlayer.src = urlEmbed;
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
const visorBtnPackObra = document.getElementById("visor-btn-pack-obra");
const visorBtnDescargar = document.getElementById("visor-btn-descargar");
const visorLinkExterno = document.getElementById("visor-link-externo");
const visorCargando = document.getElementById("visor-cargando");
const visorInfoArchivo = document.getElementById("visor-info-archivo");

let dispositivoActivoEnVisor = "";

function abrirVisorPDF(nombre, archivo, pagina = 1, paginasTotales = 1, dispositivo = "") {
  if (!modalVisorPdf) return;
  const token = localStorage.getItem("token") || "";
  dispositivoActivoEnVisor = dispositivo || "";

  if (visorTituloManual) visorTituloManual.textContent = nombre || archivo;
  if (visorPaginaChip) visorPaginaChip.textContent = `Pág. ${pagina} / ${paginasTotales || '?'}`;
  if (visorInfoArchivo) visorInfoArchivo.textContent = archivo;

  if (visorDispositivoChip) {
    if (dispositivo) {
      visorDispositivoChip.textContent = dispositivo;
      visorDispositivoChip.classList.remove("hidden");
    } else {
      visorDispositivoChip.classList.add("hidden");
    }
  }

  if (visorBtnPackObra) {
    if (dispositivo) {
      visorBtnPackObra.classList.remove("hidden");
    } else {
      visorBtnPackObra.classList.add("hidden");
    }
  }

  const urlPdfRaw = `/manuales/${encodeURIComponent(archivo)}?token=${token}`;
  const urlPdfConHash = `${urlPdfRaw}#page=${pagina}&zoom=page-width`;

  if (visorBtnDescargar) visorBtnDescargar.href = urlPdfRaw;
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
  const token = localStorage.getItem("token") || "";
  const textoOriginal = btnElement ? btnElement.innerHTML : "";
  if (btnElement) {
    btnElement.innerHTML = `<span>⏳</span> Generando ZIP...`;
    btnElement.disabled = true;
  }

  const url = `/api/dispositivos/${encodeURIComponent(dispositivo)}/pack?token=${token}`;
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
            <h4 class="font-sora font-bold text-sm text-iot-text">${d.dispositivo}</h4>
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
        Error al cargar dispositivos: ${err.message}
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

    if (r.tipo === "video") {
      tarjeta.className = "tarjeta-resultado glass-panel rounded-2xl p-6 shadow-xl hover:-translate-y-1 hover:shadow-red-500/10 transition-all flex flex-col md:flex-row gap-5 border border-red-500/20";
      
      const badgePrivacidad = r.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Técnico</span>`
        : '';

      const tagsBadges = r.etiquetas
        ? r.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="etiqueta bg-red-500/10 border border-red-500/30 text-red-300 px-2 py-0.5 rounded-md shadow-sm">🏷️ ${t}</span>`).join(' ')
        : '';

      tarjeta.innerHTML = `
        <div class="relative shrink-0 w-full md:w-56 h-32 rounded-xl overflow-hidden border border-iot-border bg-black group cursor-pointer video-thumb-trigger">
          <img class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 opacity-90 group-hover:opacity-100" src="${r.miniatura}" alt="${r.titulo}" loading="lazy">
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
                <span>▶ ${r.titulo}</span>
              </div>
              <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
                <span class="bg-red-600/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded text-xs font-semibold">🎥 Video Tutorial</span>
                ${badgePrivacidad}
                ${r.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${r.dispositivo}</span>` : ""}
                ${r.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${r.categoria}</span>` : ""}
                ${tagsBadges}
              </div>
            </div>
            <div class="resultado-fragmento text-sm text-iot-textSec leading-relaxed bg-iot-bg/50 p-3.5 rounded-xl border border-iot-border/50 mb-3">
              <span class="text-xs text-iot-tealLight font-mono block mb-1">🗣️ Explicado en el video (minuto ${r.tiempo_formateado}):</span>
              ${r.fragmento.replace(/<mark>/g, '<mark class="bg-red-500/30 text-white font-semibold rounded px-1">')}
            </div>
          </div>
          <div class="flex items-center justify-between text-xs pt-1">
            <span class="text-iot-textSec font-mono">Canal: <strong class="text-iot-text">${r.canal || 'MySmartWindow'}</strong></span>
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
      const urlConPagina = `/manuales/${encodeURIComponent(r.archivo)}?token=${token}#page=${r.pagina_encontrada}&zoom=page-width`;
      const urlRaw = `/manuales/${encodeURIComponent(r.archivo)}?token=${token}`;
      const infoPaginas = r.paginas_coincidentes > 1
        ? `<span>Pág. ${r.pagina_encontrada} de ${r.paginas} · coincide en ${r.paginas_coincidentes} páginas</span>`
        : `<span>Pág. ${r.pagina_encontrada} de ${r.paginas}</span>`;
      
      const badgePrivacidad = r.nivel_acceso === 'tecnico' 
        ? `<span class="text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded border border-orange-400/20 text-xs shadow-sm">🔒 Confidencial Técnico</span>`
        : '';

      const tagsBadges = r.etiquetas
        ? r.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="etiqueta bg-iot-teal/10 border border-iot-teal/30 text-iot-tealLight px-2 py-0.5 rounded-md shadow-sm">🏷️ ${t}</span>`).join(' ')
        : '';

      tarjeta.innerHTML = `
        <div class="relative shrink-0 w-24 h-32 rounded-xl overflow-hidden border border-iot-border bg-iot-bg hidden sm:block cursor-pointer group shadow-inner manual-thumb-trigger" title="Previsualizar en Visor (Pág. ${r.pagina_encontrada})">
          <img class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" src="/api/miniatura/${r.id}/${r.pagina_encontrada}" alt="" loading="lazy" onerror="this.style.display='none'">
          <div class="absolute inset-0 bg-iot-teal/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xl">
            👁️
          </div>
        </div>
        <div class="resultado-contenido flex-1 min-w-0">
          <div class="resultado-cabecera flex justify-between items-baseline gap-3 flex-wrap mb-3">
            <div class="flex items-center gap-2 flex-wrap">
              <a class="resultado-titulo font-sora font-bold text-xl text-iot-tealLight hover:text-iot-teal transition-colors flex items-center gap-2 cursor-pointer manual-title-trigger" href="${urlConPagina}" title="Abrir en Visor">
                📄 ${r.nombre}
              </a>
              <a href="${urlConPagina}" target="_blank" class="text-iot-textSec hover:text-iot-tealLight text-xs transition-colors p-1" title="Abrir en nueva pestaña externa">↗</a>
            </div>
            <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
              <span class="bg-iot-teal/20 text-iot-tealLight border border-iot-teal/30 px-2 py-0.5 rounded text-xs font-semibold">📄 Manual PDF</span>
              ${badgePrivacidad}
              ${r.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${r.dispositivo}</span>` : ""}
              ${r.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border text-iot-text px-2 py-0.5 rounded-md shadow-sm">${r.categoria}</span>` : ""}
              ${tagsBadges}
              <span class="text-iot-tealLight bg-iot-teal/10 px-2 py-0.5 rounded-md border border-iot-teal/20 shadow-sm">${infoPaginas}</span>
            </div>
          </div>
          <div class="resultado-fragmento text-sm text-iot-textSec leading-relaxed bg-iot-bg/50 p-4 rounded-xl border border-iot-border/50">${r.fragmento.replace(/<mark>/g, '<mark class="bg-iot-teal text-white rounded px-1">')}</div>
          
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
        abrirVisorPDF(r.nombre, r.archivo, r.pagina_encontrada, r.paginas, r.dispositivo);
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

async function buscar() {
  const q = inputBusqueda.value.trim();
  contenedorResultados.innerHTML = "";
  listaSugerencias.classList.remove("visible");
  if (filtrosTipoResultado) filtrosTipoResultado.classList.add("hidden");
  if (bannerPackObra) bannerPackObra.classList.add("hidden");

  if (!q) {
    estadoBusqueda.style.display = "block";
    estadoBusqueda.textContent = "Introduce tu consulta.";
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
      estadoBusqueda.textContent = "No se ha encontrado ninguna coincidencia.";
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
  }
}

btnBuscar.addEventListener("click", buscar);
inputBusqueda.addEventListener("keydown", (e) => {
  if (e.key === "Enter") buscar();
});

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
        ? m.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="bg-iot-teal/10 text-iot-tealLight border border-iot-teal/30 px-2 py-0.5 rounded text-[11px] font-mono">🏷️ ${t}</span>`).join(' ')
        : '';
        
      fila.innerHTML = `
        <div class="flex flex-col gap-1.5 flex-1 min-w-0">
          <a class="font-sora font-semibold text-iot-text hover:text-iot-tealLight transition-colors flex items-center gap-2 truncate text-lg manual-biblio-link cursor-pointer" href="/manuales/${encodeURIComponent(m.archivo)}?token=${token}" title="Previsualizar en Visor">📄 ${m.nombre}</a>
          <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
            ${badgePrivacidad}
            ${m.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${m.dispositivo}</span>` : ""}
            ${m.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${m.categoria}</span>` : ""}
            ${tagsBadges}
            <span class="text-iot-textSec/70 shrink-0">${m.paginas} pág.</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button class="boton-ver-biblio text-iot-tealLight hover:text-white text-xs bg-iot-teal/15 hover:bg-iot-teal/25 border border-iot-teal/30 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 shadow-sm font-sora cursor-pointer"
            data-nombre="${encodeURIComponent(m.nombre)}"
            data-archivo="${encodeURIComponent(m.archivo)}"
            data-paginas="${m.paginas}"
            data-dispositivo="${encodeURIComponent(m.dispositivo || '')}">
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
          decodeURIComponent(btn.dataset.dispositivo || '')
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
        ? v.etiquetas.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="bg-red-500/10 text-red-300 border border-red-500/30 px-2 py-0.5 rounded text-[11px] font-mono">🏷️ ${t}</span>`).join(' ')
        : '';

      fila.innerHTML = `
        <div class="flex items-center gap-4 flex-1 min-w-0">
          <div class="relative shrink-0 w-24 h-16 rounded-lg overflow-hidden border border-iot-border bg-black cursor-pointer video-thumb-player">
            <img class="w-full h-full object-cover group-hover:scale-105 transition-transform opacity-90" src="${v.miniatura_url}" alt="${v.titulo}">
            <div class="absolute inset-0 bg-black/20 hover:bg-black/0 flex items-center justify-center">
              <svg class="w-6 h-6 text-white drop-shadow" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </div>
          </div>
          <div class="flex flex-col gap-1 min-w-0">
            <div class="font-sora font-semibold text-iot-text hover:text-red-400 transition-colors cursor-pointer truncate text-base video-title-player" title="${v.titulo}">
              ▶ ${v.titulo}
            </div>
            <div class="resultado-meta text-xs text-iot-textSec flex gap-2 flex-wrap items-center font-mono">
              ${badgePrivacidad}
              ${badgeSubs}
              ${v.dispositivo ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${v.dispositivo}</span>` : ""}
              ${v.categoria ? `<span class="etiqueta bg-iot-bg border border-iot-border px-2 py-0.5 rounded-md shadow-sm">${v.categoria}</span>` : ""}
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
          <div class="font-semibold text-iot-text">${u.email}</div>
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

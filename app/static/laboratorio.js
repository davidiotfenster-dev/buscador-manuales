// =====================================================================
// 🌐 MÓDULO LABORATORIO INTEGRAL & BANCO DE PRUEBAS UNIFICADO 230V + IOT
// Plataforma IoT Fenster / MySmartWindow · Versión 2.5 Pro
// =====================================================================

(function () {
  "use strict";

  let labModuloInicializado = false;

  // ---------- Estado Global del Laboratorio ----------
  const state = {
    alimentacion230v: true,
    dispositivo: "connect-1",
    sentidoInvertido: false,       // Inversión física de cables en salida (Marrón ↔ Negro)
    sentidoInvertidoApp: false,    // Inversión por software desde la App MySmartWindow
    posicionPersiana: 50.0,        // 0% cerrada a 100% abierta
    posicionObjetivo: null,        // Consigna de la app o ciclo de calibración
    estadoMotor: "parado",         // "parado" | "subiendo" | "bajando"
    averiaActiva: null,            // Clave de avería activa o null
    wifiActivo: true,
    bandaWifi: "2.4",              // "2.4" o "5.0"
    cgnatActivo: false,
    faltaNeutro: false,            // Avería de falta de neutro en caja empotrada
    klixonDisparado: false,        // Klixon térmico del bobinado por uso >4min
    pulsadorModo: "monoestable",   // "monoestable" o "biestable"
    dhcpInestable: false,          // Caídas intermitentes por roaming
    fcUpLimit: 100,                // Límite carrera superior (ajustable FC ▲)
    fcDownLimit: 0,                // Límite carrera inferior (ajustable FC ▼)
    sondaActiva: "l_n",            // Sonda activa del multímetro DIN
    sobrecargaTermica: false,
    releK1Cerrado: false,          // Relé K1 (Subida ▲)
    releK2Cerrado: false,          // Relé K2 (Bajada ▼)
    pulsadorParedActivo: null,     // "up", "down", null
    velocidadPctPorSegundo: 8.0,   // Viaje 0-100 en ~12.5 s
    ultimoTimestamp: null,
    fullscreen: false,
    audioHabilitado: true,
    autoCalibrando: false,
    sensorVientoActivo: false,
    sensorLluviaActivo: false
  };

  // ---------- Sintetizador de Audio Realista (Web Audio API) ----------
  let audioCtx = null;
  let motorOscillator = null;
  let motorGainNode = null;

  function getAudioContext() {
    if (!audioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        audioCtx = new AudioCtxClass();
      }
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    return audioCtx;
  }

  function playRelayClick() {
    if (!state.audioHabilitado) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(120, now + 0.035);
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.04);
    } catch (e) {}
  }

  function startMotorHum() {
    if (!state.audioHabilitado) return;
    try {
      const ctx = getAudioContext();
      if (!ctx || motorOscillator) return;

      motorOscillator = ctx.createOscillator();
      motorGainNode = ctx.createGain();
      motorOscillator.type = "sawtooth";
      motorOscillator.frequency.setValueAtTime(50.0, ctx.currentTime); // 50 Hz zumbido de red

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(160, ctx.currentTime);

      motorGainNode.gain.setValueAtTime(0.001, ctx.currentTime);
      motorGainNode.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.2);

      motorOscillator.connect(filter);
      filter.connect(motorGainNode);
      motorGainNode.connect(ctx.destination);
      motorOscillator.start();
    } catch (e) {}
  }

  function stopMotorHum() {
    if (motorOscillator && motorGainNode && audioCtx) {
      try {
        const now = audioCtx.currentTime;
        motorGainNode.gain.linearRampToValueAtTime(0.001, now + 0.12);
        const oldOsc = motorOscillator;
        const oldGain = motorGainNode;
        motorOscillator = null;
        motorGainNode = null;
        setTimeout(() => {
          try {
            oldOsc.stop();
            oldOsc.disconnect();
            oldGain.disconnect();
          } catch (e) {}
        }, 130);
      } catch (e) {
        motorOscillator = null;
        motorGainNode = null;
      }
    }
  }

  function playBreakerSound(isOn) {
    if (!state.audioHabilitado) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(isOn ? 180 : 340, now);
      osc.frequency.exponentialRampToValueAtTime(45, now + 0.08);
      gain.gain.setValueAtTime(0.4, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.09);
    } catch (e) {}
  }

  function playAlarmSound() {
    if (!state.audioHabilitado) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "square";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(660, now + 0.1);
      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.23);
    } catch (e) {}
  }

  // ---------- Catálogo de Dispositivos para el Laboratorio ----------
  const LAB_CATALOGO_DISPOSITIVOS = {
    "connect-1": {
      titulo: "CONNECT-1",
      subtitulo: "Smart Motor Controller · 230V 5A",
      descripcion: "<strong class='text-iot-tealLight'>Connect-1:</strong> Alimentación directa 230V con relés de enclavamiento integrados para 1 motor tubular de 4 hilos. Antena Wi-Fi 2.4G integrada.",
      hasBus: false
    },
    "connect-2": {
      titulo: "CONNECT-2",
      subtitulo: "Doble Canal / Sensores · 230V",
      descripcion: "<strong class='text-iot-tealLight'>Connect-2:</strong> Dispone de salidas independientes para 2 motores o entradas auxiliares de sensores meteorológicos (anemómetro de viento / pluviómetro de lluvia).",
      hasBus: false
    },
    "c-wall": {
      titulo: "C-WALL",
      subtitulo: "Mecanismo Empotrado 60mm · Táctil 230V",
      descripcion: "<strong class='text-amber-400'>C-Wall (Neutro Obligatorio):</strong> Receptor inteligente empotrable. Debe disponer de Fase (L) y Neutro (N) directos en la caja de mecanismo de 60 mm.",
      hasBus: false
    },
    "c-pulsar": {
      titulo: "C-PULSAR",
      subtitulo: "Potencia en Cajón + Marco · Split 230V / 3.3V",
      descripcion: "<strong class='text-purple-400'>C-Pulsar (Split Potencia/Marco):</strong> Potencia 230V en el cajón superior y pulsador táctil de marco a <strong class='text-white'>3.3V de muy baja tensión</strong> por cable apantallado. ¡Prohibido meter 230V al marco!",
      hasBus: true
    },
    "connect-evo": {
      titulo: "CONNECT EVO",
      subtitulo: "Mecanismo Superficie de Marco · 230V",
      descripcion: "<strong class='text-iot-tealLight'>Connect EVO:</strong> Mecanismo de superficie con teclas mecánicas basculantes integradas y enclavamiento mecánico de seguridad.",
      hasBus: false
    }
  };

  // ---------- Catálogo Oficial de Averías Canónicas SAT ----------
  const LAB_DIAGNOSTICOS_AVERIAS = {
    "fase_invertida": {
      icono: "🔀",
      titulo: "Avería Canónica: Fases de Maniobra Invertidas (Marrón ↔ Negro)",
      mensaje: "Los cables marrón (subida) y negro (bajada) están conectados a la inversa en la salida del motor. Al pulsar SUBIR, el motor hace descender la persiana. Solución: Pulsa 'Swap Giro', permuta los bornes marrón y negro en la regleta, o activa 'Invertir Giro' en los ajustes de la App.",
      tipo: "alerta",
      manual: { nombre: "Problemas y Soluciones SAT", archivo: "Problemas_y_Soluciones_SAT.pdf", pagina: 1 }
    },
    "corte_termico": {
      icono: "⚡",
      titulo: "Avería Canónica: Corte de Suministro / Disparo de Magnetotérmico",
      mensaje: "El circuito de 230V AC se encuentra sin alimentación eléctrica. Los instrumentos marcan 0.0V y 0.0W. La persiana se detiene inmediatamente y la app móvil pasa a estado 'Sin Conexión'. Solución: Rearma la palanca del magnetotérmico PIA C10.",
      tipo: "peligro",
      manual: { nombre: "Manual Instalación Connect", archivo: "MANUAL_INSTALACION_CONNECT.pdf", pagina: 2 }
    },
    "wifi_incompatible": {
      icono: "📶",
      titulo: "Avería Canónica: Wi-Fi en Banda 5 GHz o CG-NAT de Operador",
      mensaje: "El router está emitiendo en banda exclusiva de 5 GHz o el proveedor (Digi, MásMóvil) aplica CG-NAT con aislamiento de clientes. La app pierde conexión con la nube. Sin embargo, ¡el pulsador físico de pared de 230V sigue funcionando de forma 100% autónoma!",
      tipo: "advertencia",
      manual: { nombre: "Requisitos Conectividad y CGNAT", archivo: "CONECTIVIDAD_REQUISITOS.pdf", pagina: 1 }
    },
    "cpulsar_bus_cortado": {
      icono: "🪛",
      titulo: "Avería Canónica: Cable de Bus de Marco Dañado por Tornillo",
      mensaje: "El cable apantallado de 4 hilos (3.3V) ha sido perforado por un tornillo de fijación de la ventana durante el montaje en obra. El pulsador táctil de marco parpadea en rojo/azul continuo y no responde. La maniobra por app y pulsador de pared se mantiene.",
      tipo: "peligro",
      manual: { nombre: "Manual Técnico C-Pulsar", archivo: "C-PULSAR_ES.pdf", pagina: 1 }
    },
    "bloqueo_mecanico": {
      icono: "🛑",
      titulo: "Avería Canónica: Bloqueo Mecánico / Sobrecarga del Motor (>2.2A)",
      mensaje: "La persiana se ha acuñado en las guías laterales. La potencia absorbida se dispara a más de 340W (>1.5A). Se ha activado la protección electrónica de sobreesfuerzo para evitar la rotura de flejes o destrucción del motor. Solución: Desatasca las lamas y revisa las guías.",
      tipo: "peligro",
      manual: { nombre: "Problemas y Soluciones SAT", archivo: "Problemas_y_Soluciones_SAT.pdf", pagina: 1 }
    },
    "falta_neutro": {
      icono: "🔌",
      titulo: "Avería Canónica: Falta Hilo de Neutro en Caja Empotrada (C-Wall)",
      mensaje: "En la caja de mecanismo de pared solo hay fase cortada sin neutro de retorno. C-Wall es un receptor inteligente activo 230V y REQUIERE obligatoriamente Fase (L) y Neutro (N) directos para alimentar su microprocesador. Solución: Pasa un hilo azul de neutro desde el cajón o caja de registro.",
      tipo: "peligro",
      manual: { nombre: "Manual Instalación C-Wall", archivo: "C-WALL_ES.pdf", pagina: 1 }
    },
    "klixon_motor": {
      icono: "🔥",
      titulo: "Avería Canónica: Klixon Térmico del Motor Disparado (>4 min uso)",
      mensaje: "El motor tubular ha funcionado continuamente durante más de 4 minutos en obra (pruebas repetitivas). El protector térmico bimetálico interno del bobinado se ha abierto por seguridad. Los relés hacen 'clic', pero el motor no gira. Solución: Deja enfriar el motor 20 minutos sin accionar.",
      tipo: "peligro",
      manual: { nombre: "Problemas y Soluciones SAT", archivo: "Problemas_y_Soluciones_SAT.pdf", pagina: 1 }
    },
    "pulsador_mono_bi": {
      icono: "⏱️",
      titulo: "Avería Canónica: Desconfiguración de Tecla (Monoestable vs Biestable)",
      mensaje: "El firmware espera un conmutador biestable fijo pero se ha instalado una tecla con muelle monoestable (o viceversa). La persiana requiere mantener apretado el pulsador o responde con retardo. Solución: En Ajustes > Configuración de Pulsador, fija 'Pulsador Monoestable'.",
      tipo: "alerta",
      manual: { nombre: "Problemas y Soluciones SAT", archivo: "Problemas_y_Soluciones_SAT.pdf", pagina: 1 }
    },
    "dhcp_lease_mesh": {
      icono: "📡",
      titulo: "Avería Canónica: Desconexiones Aleatorias Wi-Fi (DHCP / Roaming Mesh)",
      mensaje: "El router tiene una concesión DHCP demasiado corta o los nodos Wi-Fi Mesh provocan saltos de roaming agresivos. El dispositivo pasa a 'Fuera de Línea' intermitentemente. Solución: Fija una IP estática por reserva DHCP (MAC) y desactiva Fast Roaming en el nodo.",
      tipo: "advertencia",
      manual: { nombre: "Requisitos Conectividad y CGNAT", archivo: "CONECTIVIDAD_REQUISITOS.pdf", pagina: 1 }
    },
    "nominal": {
      icono: "💡",
      titulo: "Estado Nominal del Sistema",
      mensaje: "Tensión nominal 230V AC presente, relés abiertos en reposo (0.8 W standby). Puedes pulsar las teclas del interruptor de pared, accionar la app en el smartphone virtual o inducir averías canónicas para comprobar el diagnóstico SAT.",
      tipo: "normal",
      manual: { nombre: "Manual General Ecosistema", archivo: "MANUAL_INSTALACION_CONNECT.pdf", pagina: 1 }
    }
  };

  // =====================================================================
  // INICIALIZACIÓN PRINCIPAL DEL BANCO DE PRUEBAS
  // =====================================================================
  function inicializarLaboratorioIntegral() {
    if (labModuloInicializado) return;
    labModuloInicializado = true;

    // Elementos DOM del Dock
    const btnBreakerToggle = document.getElementById("btn-lab-breaker-toggle");
    const breakerLever = document.getElementById("lab-breaker-lever");
    const cuadroStatusBadge = document.getElementById("lab-cuadro-status-badge");
    const ledFaseCuadro = document.getElementById("lab-led-fase-cuadro");
    const txtFaseCuadro = document.getElementById("lab-txt-fase-cuadro");
    const btnDiffTest = document.getElementById("btn-lab-diff-test");
    const telemetriaVoltaje = document.getElementById("lab-telemetria-voltaje");
    const telemetriaPotencia = document.getElementById("lab-telemetria-potencia");
    const telemetriaCorriente = document.getElementById("lab-telemetria-corriente");
    const telemetriaFreq = document.getElementById("lab-telemetria-freq");
    const btnsSondas = document.querySelectorAll(".btn-lab-sonda");
    const badgeSondaActiva = document.getElementById("lab-badge-sonda-activa");

    // Configuración Dispositivo
    const selectDispositivo = document.getElementById("lab-select-dispositivo");
    const equipoInfoBadge = document.getElementById("lab-equipo-info-badge");
    const panelSensoresConnect2 = document.getElementById("lab-panel-sensores-connect2");
    const btnSensorViento = document.getElementById("btn-lab-sensor-viento");
    const btnSensorLluvia = document.getElementById("btn-lab-sensor-lluvia");
    const ledSensorViento = document.getElementById("lab-sensor-viento-led");
    const ledSensorLluvia = document.getElementById("lab-sensor-lluvia-led");

    // Inyector de Averías
    const btnsAverias = document.querySelectorAll(".btn-lab-averia");

    // Smartphone Virtual
    const phoneConnectionStatus = document.getElementById("lab-phone-connection-status");
    const phoneWifiIcon = document.getElementById("lab-phone-wifi-icon");
    const phoneRssiBadge = document.getElementById("lab-phone-rssi-badge");
    const phoneDeviceLbl = document.getElementById("lab-phone-device-lbl");
    const phonePosNum = document.getElementById("lab-phone-pos-num");
    const phoneMotorStateTxt = document.getElementById("lab-phone-motor-state-txt");
    const phoneSlider = document.getElementById("lab-phone-slider");
    const btnPhoneSubir = document.getElementById("btn-phone-subir");
    const btnPhoneParar = document.getElementById("btn-phone-parar");
    const btnPhoneBajar = document.getElementById("btn-phone-bajar");
    const btnPhoneAutoCalibrar = document.getElementById("btn-phone-auto-calibrar");
    const chkPhoneInvertirGiro = document.getElementById("chk-phone-invertir-giro");
    const phoneOfflineOverlay = document.getElementById("lab-phone-offline-overlay");

    // Botones de Cabecera
    const btnLabSoundToggle = document.getElementById("btn-lab-sound-toggle");
    const labSoundIcon = document.getElementById("lab-sound-icon");
    const labSoundTxt = document.getElementById("lab-sound-txt");
    const btnLabSwap = document.getElementById("btn-lab-swap-giro");
    const btnLabReset = document.getElementById("btn-lab-reset-nominal");
    const btnLabGenerarTicket = document.getElementById("btn-lab-generar-ticket");
    const btnLabWpShare = document.getElementById("btn-lab-wp-share");
    const btnLabFullscreen = document.getElementById("btn-lab-fullscreen");
    const labFsIcon = document.getElementById("lab-fs-icon");
    const labFsTexto = document.getElementById("lab-fs-texto");
    const labDiagramCard = document.getElementById("lab-diagram-card");

    // Elementos SVG
    const svgBreakerSwitch = document.getElementById("lab-svg-breaker-switch");
    const svgBreakerText = document.getElementById("lab-svg-breaker-text");
    const svgDevTitle = document.getElementById("lab-svg-dev-title");
    const svgDevSubtitle = document.getElementById("lab-svg-dev-subtitle");
    const svgDevLed = document.getElementById("lab-svg-dev-led");
    const svgContactK1 = document.getElementById("lab-svg-contact-k1");
    const svgContactK2 = document.getElementById("lab-svg-contact-k2");
    const svgK1Badge = document.getElementById("lab-svg-k1-badge");
    const svgK2Badge = document.getElementById("lab-svg-k2-badge");
    const svgLblOut1 = document.getElementById("lab-svg-lbl-out1");
    const svgLblOut2 = document.getElementById("lab-svg-lbl-out2");
    const svgCpulsarBus = document.getElementById("lab-svg-cpulsar-bus");
    const svgBtnWallUp = document.getElementById("lab-btn-wall-up");
    const svgBtnWallDown = document.getElementById("lab-btn-wall-down");
    const svgWifiWaves = document.getElementById("lab-svg-wifi-waves");
    const svgRouterCgnatStatus = document.getElementById("lab-svg-router-cgnat-status");
    const svgMotorRotor = document.getElementById("lab-svg-motor-rotor");
    const svgRotorTxt = document.getElementById("lab-svg-rotor-txt");
    const svgSlatsBg = document.getElementById("lab-svg-slats-bg");
    const svgSlatsLines = document.getElementById("lab-svg-slats-lines");
    const svgSlatsZocalo = document.getElementById("lab-svg-slats-zocalo");
    const svgPosBadge = document.getElementById("lab-svg-pos-badge");
    const svgPulsadorMarco = document.getElementById("lab-svg-pulsador-marco");
    const svgMarcoLed = document.getElementById("lab-svg-marco-led");
    const wireInL = document.getElementById("lab-wire-in-l");
    const wireInN = document.getElementById("lab-wire-in-n");
    const wireOutUp = document.getElementById("lab-wire-out-up");
    const wireOutDown = document.getElementById("lab-wire-out-down");
    const wireOutN = document.getElementById("lab-wire-out-n");
    const wireBusCpulsar = document.getElementById("lab-wire-bus-cpulsar");
    const chipDispositivo = document.getElementById("lab-diagrama-chip-dispositivo");
    const dot230v = document.getElementById("lab-dot-230v");
    const dotWifi = document.getElementById("lab-dot-wifi");
    const dotBus = document.getElementById("lab-dot-bus");

    // Puntos de Prueba en Bornes SVG
    const probePoints = {
      l: document.getElementById("lab-probe-point-l"),
      n: document.getElementById("lab-probe-point-n"),
      pe: document.getElementById("lab-probe-point-pe"),
      out1: document.getElementById("lab-probe-point-out1"),
      out2: document.getElementById("lab-probe-point-out2"),
      bus: document.getElementById("lab-probe-point-bus")
    };

    // Tornillos de Final de Carrera
    const screwFcUp = document.getElementById("lab-screw-fc-up");
    const screwFcDown = document.getElementById("lab-screw-fc-down");
    const txtFcUpVal = document.getElementById("lab-txt-fc-up-val");
    const txtFcDownVal = document.getElementById("lab-txt-fc-down-val");

    // Telemetría SCADA y Asesoría SAT
    const scadaKpiRelays = document.getElementById("lab-scada-kpi-relays");
    const scadaKpiMotor = document.getElementById("lab-scada-kpi-motor");
    const scadaFcStatus = document.getElementById("lab-scada-fc-status");
    const asesoriaCaja = document.getElementById("lab-asesoria-caja");
    const asesoriaIcono = document.getElementById("lab-asesoria-icono");
    const asesoriaTitulo = document.getElementById("lab-asesoria-titulo");
    const asesoriaMensaje = document.getElementById("lab-asesoria-mensaje");
    const btnLabVerManual = document.getElementById("btn-lab-ver-manual");

    // =====================================================================
    // CONTROL DE MANIOBRA & MÁQUINA DE ESTADOS
    // =====================================================================
    function iniciarManiobra(orden) {
      // 1. Validaciones de protección eléctrica y mecánica
      if (!state.alimentacion230v) {
        playRelayClick();
        actualizarAsesoria("corte_termico");
        return;
      }
      if (state.faltaNeutro) {
        playRelayClick();
        actualizarAsesoria("falta_neutro");
        return;
      }
      if (state.averiaActiva === "bloqueo_mecanico") {
        playAlarmSound();
        actualizarAsesoria("bloqueo_mecanico");
        return;
      }
      if (state.klixonDisparado) {
        playRelayClick();
        actualizarAsesoria("klixon_motor");
        return;
      }

      // 2. Sentido efectivo de rotación (inversión física XOR inversión app)
      const isInvertido = (state.sentidoInvertido !== state.sentidoInvertidoApp);
      const subiendoReal = isInvertido ? (orden === "bajar") : (orden === "subir");

      // 3. Verificación de finales de carrera fijados
      if (subiendoReal && state.posicionPersiana >= state.fcUpLimit) {
        if (scadaFcStatus) scadaFcStatus.textContent = `Final de carrera SUPERIOR activo (${state.fcUpLimit}% Abierta)`;
        pararManiobra();
        return;
      }
      if (!subiendoReal && state.posicionPersiana <= state.fcDownLimit) {
        if (scadaFcStatus) scadaFcStatus.textContent = `Final de carrera INFERIOR activo (${state.fcDownLimit}% Cerrada)`;
        pararManiobra();
        return;
      }

      // 4. Asignación rigurosa de la máquina de estados
      state.estadoMotor = subiendoReal ? "subiendo" : "bajando";

      // Conmutación de relés de potencia con interlock de seguridad
      if (orden === "subir") {
        state.releK1Cerrado = true;
        state.releK2Cerrado = false;
      } else if (orden === "bajar") {
        state.releK1Cerrado = false;
        state.releK2Cerrado = true;
      }

      playRelayClick();
      startMotorHum();
      actualizarVista();
    }

    function pararManiobra() {
      state.estadoMotor = "parado";
      state.releK1Cerrado = false;
      state.releK2Cerrado = false;
      state.posicionObjetivo = null;

      stopMotorHum();
      playRelayClick();
      actualizarVista();
    }

    // =====================================================================
    // BUCLE DE FÍSICA CONTINUA Y ANIMACIÓN (requestAnimationFrame)
    // =====================================================================
    function bucleAnimacion(timestamp) {
      if (!state.ultimoTimestamp) state.ultimoTimestamp = timestamp;
      const deltaMs = Math.min(100, timestamp - state.ultimoTimestamp);
      state.ultimoTimestamp = timestamp;

      if (state.estadoMotor !== "parado" &&
          state.alimentacion230v &&
          !state.faltaNeutro &&
          state.averiaActiva !== "bloqueo_mecanico" &&
          !state.klixonDisparado) {

        const deltaSeg = deltaMs / 1000.0;
        const incremento = state.velocidadPctPorSegundo * deltaSeg;

        if (state.estadoMotor === "subiendo") {
          state.posicionPersiana += incremento;
          if (state.posicionPersiana >= state.fcUpLimit) {
            state.posicionPersiana = state.fcUpLimit;
            pararManiobra();
            if (scadaFcStatus) scadaFcStatus.textContent = `Final de carrera SUPERIOR alcanzado (${state.fcUpLimit}%)`;
          }
        } else if (state.estadoMotor === "bajando") {
          state.posicionPersiana -= incremento;
          if (state.posicionPersiana <= state.fcDownLimit) {
            state.posicionPersiana = state.fcDownLimit;
            pararManiobra();
            if (scadaFcStatus) scadaFcStatus.textContent = `Final de carrera INFERIOR alcanzado (${state.fcDownLimit}%)`;
          }
        }

        // Parada de precisión si viene de objetivo de la app o calibración
        if (state.posicionObjetivo !== null) {
          if (Math.abs(state.posicionPersiana - state.posicionObjetivo) < 1.2) {
            state.posicionPersiana = state.posicionObjetivo;
            pararManiobra();
          }
        }

        actualizarVistaPersiana();
      }

      requestAnimationFrame(bucleAnimacion);
    }

    // =====================================================================
    // ACTUALIZACIÓN VISUAL DEL PAÑO DE PERSIANA SVG
    // =====================================================================
    function actualizarVistaPersiana() {
      const pct = Math.max(0, Math.min(100, state.posicionPersiana));
      const alturaLuz = 450; // Altura de luz de la ventana en el SVG
      // 0% (cerrada) -> altura 446px (cubre todo). 100% (abierta) -> altura 14px (recogida en zócalo).
      const alturaLamas = Math.max(14, Math.round(alturaLuz - (pct / 100.0) * (alturaLuz - 14)));

      if (svgSlatsBg) {
        svgSlatsBg.setAttribute("height", alturaLamas);
      }
      if (svgSlatsZocalo) {
        svgSlatsZocalo.setAttribute("y", Math.max(0, alturaLamas - 12));
      }
      if (svgPosBadge) {
        svgPosBadge.textContent = Math.round(pct) + "%";
      }
      if (phonePosNum) {
        phonePosNum.textContent = Math.round(pct);
      }
      if (phoneSlider && document.activeElement !== phoneSlider) {
        phoneSlider.value = Math.round(pct);
      }

      // Dibujo procedural de las lamas de aluminio extruido
      if (svgSlatsLines) {
        const numLamas = Math.floor(alturaLamas / 18);
        let linesHtml = "";
        for (let i = 1; i <= numLamas; i++) {
          const y = i * 18;
          if (y < alturaLamas - 12) {
            linesHtml += `<line x1="0" y1="${y}" x2="370" y2="${y}" stroke="#0f2233" stroke-width="2" />`;
            linesHtml += `<line x1="0" y1="${y + 1}" x2="370" y2="${y + 1}" stroke="#3b5670" stroke-width="0.7" opacity="0.6" />`;
          }
        }
        svgSlatsLines.innerHTML = linesHtml;
      }
    }

    // =====================================================================
    // ACTUALIZACIÓN GENERAL DE TELEMETRÍA Y ESTADO SCADA
    // =====================================================================
    function actualizarVista() {
      // 1. Cuadro Eléctrico 230V y Magnetotérmico
      if (state.alimentacion230v) {
        if (breakerLever) {
          breakerLever.classList.remove("translate-y-9", "bg-rose-500", "border-rose-300");
          breakerLever.classList.add("bg-emerald-500", "border-emerald-300");
          breakerLever.textContent = "ON";
        }
        if (cuadroStatusBadge) {
          cuadroStatusBadge.className = "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
          cuadroStatusBadge.textContent = "LÍNEA ACTIVA";
        }
        if (ledFaseCuadro) {
          ledFaseCuadro.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse";
        }
        if (txtFaseCuadro) {
          txtFaseCuadro.className = "text-[11px] font-mono text-emerald-300 font-semibold";
          txtFaseCuadro.textContent = "Tensión Presente (Fase L)";
        }
        if (svgBreakerSwitch) {
          svgBreakerSwitch.setAttribute("fill", "#10b981");
          svgBreakerSwitch.setAttribute("stroke", "#34d399");
        }
        if (svgBreakerText) {
          svgBreakerText.textContent = "ON";
        }
        if (dot230v) dot230v.className = "w-2 h-2 rounded-full bg-emerald-400";
        if (wireInL) wireInL.style.opacity = "1";
        if (wireInN) wireInN.style.opacity = state.faltaNeutro ? "0.2" : "1";
      } else {
        if (breakerLever) {
          breakerLever.classList.add("translate-y-9", "bg-rose-500", "border-rose-300");
          breakerLever.classList.remove("bg-emerald-500", "border-emerald-300");
          breakerLever.textContent = "OFF";
        }
        if (cuadroStatusBadge) {
          cuadroStatusBadge.className = "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30";
          cuadroStatusBadge.textContent = "SIN TENSIÓN (OFF)";
        }
        if (ledFaseCuadro) {
          ledFaseCuadro.className = "w-2.5 h-2.5 rounded-full bg-slate-600";
        }
        if (txtFaseCuadro) {
          txtFaseCuadro.className = "text-[11px] font-mono text-slate-400";
          txtFaseCuadro.textContent = "Circuito Abierto (0 V)";
        }
        if (svgBreakerSwitch) {
          svgBreakerSwitch.setAttribute("fill", "#ef4444");
          svgBreakerSwitch.setAttribute("stroke", "#f87171");
        }
        if (svgBreakerText) {
          svgBreakerText.textContent = "OFF";
        }
        if (dot230v) dot230v.className = "w-2 h-2 rounded-full bg-slate-600";
        if (wireInL) wireInL.style.opacity = "0";
        if (wireInN) wireInN.style.opacity = "0";
      }

      // 2. Multímetro Digital DIN con Sondas Interactivas
      let voltDisplay = "0.0 V";
      let potDisplay = "0.0 W";
      let ampDisplay = "0.00 A";

      if (state.alimentacion230v) {
        const fluct = (Math.random() * 0.4 - 0.2);
        const vRed = (230.2 + fluct).toFixed(1);

        if (state.sondaActiva === "l_n") {
          voltDisplay = state.faltaNeutro ? "18.4 V" : `${vRed} V`;
        } else if (state.sondaActiva === "l_pe") {
          voltDisplay = `${vRed} V`;
        } else if (state.sondaActiva === "n_pe") {
          voltDisplay = state.faltaNeutro ? "44.6 V" : "0.4 V";
        } else if (state.sondaActiva === "out_up") {
          voltDisplay = (state.releK1Cerrado && !state.faltaNeutro) ? `${vRed} V` : "0.0 V";
        } else if (state.sondaActiva === "out_down") {
          voltDisplay = (state.releK2Cerrado && !state.faltaNeutro) ? `${vRed} V` : "0.0 V";
        } else if (state.sondaActiva === "bus_cpulsar") {
          if (state.dispositivo !== "c-pulsar") {
            voltDisplay = "0.0 V (N/A)";
          } else if (state.averiaActiva === "cpulsar_bus_cortado") {
            voltDisplay = "0.2 V DC";
          } else {
            voltDisplay = "3.31 V DC";
          }
        }

        // Potencia e Intensidad según régimen
        if (state.faltaNeutro) {
          potDisplay = "0.0 W";
          ampDisplay = "0.00 A";
        } else if (state.averiaActiva === "bloqueo_mecanico") {
          potDisplay = "346.5 W";
          ampDisplay = "1.58 A";
        } else if (state.estadoMotor !== "parado") {
          const potMot = (134.0 + (Math.random() * 2 - 1)).toFixed(1);
          potDisplay = `${potMot} W`;
          ampDisplay = "0.61 A";
        } else {
          potDisplay = "0.8 W";
          ampDisplay = "0.02 A";
        }
      }

      if (telemetriaVoltaje) telemetriaVoltaje.textContent = voltDisplay;
      if (telemetriaPotencia) telemetriaPotencia.textContent = potDisplay;
      if (telemetriaCorriente) telemetriaCorriente.textContent = ampDisplay;
      if (telemetriaFreq) telemetriaFreq.textContent = state.alimentacion230v ? "50.0 Hz · RMS Real" : "0.0 Hz";

      if (badgeSondaActiva) {
        badgeSondaActiva.textContent = `SONDA: ${state.sondaActiva.toUpperCase().replace('_', '-')}`;
      }

      // 3. Dispositivo Central
      const infoDisp = LAB_CATALOGO_DISPOSITIVOS[state.dispositivo] || LAB_CATALOGO_DISPOSITIVOS["connect-1"];
      if (svgDevTitle) svgDevTitle.textContent = infoDisp.titulo;
      if (svgDevSubtitle) svgDevSubtitle.textContent = infoDisp.subtitulo;
      if (chipDispositivo) chipDispositivo.textContent = state.dispositivo.toUpperCase();
      if (equipoInfoBadge) equipoInfoBadge.innerHTML = infoDisp.descripcion;

      if (panelSensoresConnect2) {
        panelSensoresConnect2.classList.toggle("hidden", state.dispositivo !== "connect-2");
      }

      if (svgCpulsarBus) {
        svgCpulsarBus.style.opacity = infoDisp.hasBus ? "1" : "0.2";
      }
      if (wireBusCpulsar) {
        wireBusCpulsar.style.opacity = infoDisp.hasBus ? "1" : "0.2";
      }
      if (dotBus) {
        dotBus.className = infoDisp.hasBus ? "w-2 h-2 rounded-full bg-purple-400" : "w-2 h-2 rounded-full bg-slate-600";
      }

      // LED del dispositivo
      if (svgDevLed) {
        if (!state.alimentacion230v || state.faltaNeutro) {
          svgDevLed.setAttribute("fill", "#334155");
        } else if (state.averiaActiva === "bloqueo_mecanico" || state.averiaActiva === "cpulsar_bus_cortado" || state.klixonDisparado) {
          svgDevLed.setAttribute("fill", "#ef4444");
        } else if (state.averiaActiva === "wifi_incompatible" || state.dhcpInestable) {
          svgDevLed.setAttribute("fill", "#f59e0b");
        } else {
          svgDevLed.setAttribute("fill", "#10b981");
        }
      }

      // 4. Relés K1 y K2
      const tensionValida = state.alimentacion230v && !state.faltaNeutro;
      if (tensionValida && state.releK1Cerrado) {
        if (svgContactK1) svgContactK1.classList.add("relay-closed-k1");
        if (svgK1Badge) { svgK1Badge.textContent = "CERRADO"; svgK1Badge.setAttribute("fill", "#10b981"); }
        if (wireOutUp) wireOutUp.style.opacity = "1";
      } else {
        if (svgContactK1) svgContactK1.classList.remove("relay-closed-k1");
        if (svgK1Badge) { svgK1Badge.textContent = "ABIERTO"; svgK1Badge.setAttribute("fill", "#64748b"); }
        if (wireOutUp) wireOutUp.style.opacity = "0";
      }

      if (tensionValida && state.releK2Cerrado) {
        if (svgContactK2) svgContactK2.classList.add("relay-closed-k2");
        if (svgK2Badge) { svgK2Badge.textContent = "CERRADO"; svgK2Badge.setAttribute("fill", "#00b4d8"); }
        if (wireOutDown) wireOutDown.style.opacity = "1";
      } else {
        if (svgContactK2) svgContactK2.classList.remove("relay-closed-k2");
        if (svgK2Badge) { svgK2Badge.textContent = "ABIERTO"; svgK2Badge.setAttribute("fill", "#64748b"); }
        if (wireOutDown) wireOutDown.style.opacity = "0";
      }

      if (wireOutN) {
        wireOutN.style.opacity = (tensionValida && state.estadoMotor !== "parado") ? "1" : "0";
      }

      // Bornes de salida y Swap de giro
      if (svgLblOut1 && svgLblOut2) {
        if (state.sentidoInvertido) {
          svgLblOut1.textContent = "▲ (Negro)";
          svgLblOut2.textContent = "▼ (Marrón)";
        } else {
          svgLblOut1.textContent = "▲ (Marrón)";
          svgLblOut2.textContent = "▼ (Negro)";
        }
      }

      // 5. Motor Tubular y Rotor
      if (tensionValida && state.estadoMotor !== "parado" && state.averiaActiva !== "bloqueo_mecanico" && !state.klixonDisparado) {
        const subiendo = state.estadoMotor === "subiendo";
        if (svgMotorRotor) {
          svgMotorRotor.classList.remove("rotor-spin-cw", "rotor-spin-ccw");
          svgMotorRotor.classList.add(subiendo ? "rotor-spin-ccw" : "rotor-spin-cw");
        }
        if (svgRotorTxt) {
          svgRotorTxt.textContent = subiendo ? "▲ SUBIENDO" : "▼ BAJANDO";
          svgRotorTxt.setAttribute("fill", subiendo ? "#5eead4" : "#38bdf8");
        }
        if (phoneMotorStateTxt) {
          phoneMotorStateTxt.textContent = subiendo ? "Subiendo..." : "Bajando...";
        }
        if (scadaKpiMotor) {
          scadaKpiMotor.textContent = subiendo ? "Motor: 15 RPM · SUBIENDO (▲)" : "Motor: 15 RPM · BAJANDO (▼)";
          scadaKpiMotor.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-teal-900/40 text-teal-300 border border-teal-500/40";
        }
      } else {
        if (svgMotorRotor) svgMotorRotor.classList.remove("rotor-spin-cw", "rotor-spin-ccw");
        let txtMotor = "PARADO";
        let colorMotor = "#64748b";
        let kpiMotorTxt = "Motor: 0 RPM · PARADO";

        if (state.averiaActiva === "bloqueo_mecanico") {
          txtMotor = "BLOQUEADO";
          colorMotor = "#ef4444";
          kpiMotorTxt = "Motor: 0 RPM · SOBRECARGA >2.2A";
        } else if (state.klixonDisparado) {
          txtMotor = "TÉRMICO ABIERTO";
          colorMotor = "#f59e0b";
          kpiMotorTxt = "Motor: 0 RPM · KLIXON DISPARADO";
        }

        if (svgRotorTxt) {
          svgRotorTxt.textContent = txtMotor;
          svgRotorTxt.setAttribute("fill", colorMotor);
        }
        if (phoneMotorStateTxt) {
          phoneMotorStateTxt.textContent = txtMotor === "PARADO" ? "Parado" : `¡${txtMotor}!`;
        }
        if (scadaKpiMotor) {
          scadaKpiMotor.textContent = kpiMotorTxt;
          scadaKpiMotor.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700";
        }
      }

      // 6. Router Wi-Fi & Nube
      const wifiOk = state.wifiActivo && state.bandaWifi === "2.4" && !state.cgnatActivo && state.averiaActiva !== "wifi_incompatible" && !state.dhcpInestable;
      if (svgWifiWaves) {
        svgWifiWaves.style.display = wifiOk ? "block" : "none";
      }
      if (dotWifi) {
        dotWifi.className = wifiOk ? "w-2 h-2 rounded-full bg-cyan-400 animate-pulse" : "w-2 h-2 rounded-full bg-rose-500";
      }
      if (svgRouterCgnatStatus) {
        svgRouterCgnatStatus.textContent = (state.cgnatActivo || state.averiaActiva === "wifi_incompatible")
          ? "CG-NAT ACTIVO / 5 GHz (Sin salida MQTT)"
          : (state.dhcpInestable ? "ROAMING MESH / DHCP CONFLICT" : "IP Pública Directa (Sin CG-NAT)");
        svgRouterCgnatStatus.setAttribute("fill", wifiOk ? "#38bdf8" : "#ef4444");
      }

      // 7. Smartphone Virtual
      const phoneOnline = state.alimentacion230v && !state.faltaNeutro && wifiOk;
      if (phoneConnectionStatus) {
        phoneConnectionStatus.className = phoneOnline
          ? "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
          : "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30";
        phoneConnectionStatus.textContent = phoneOnline ? "🟢 ONLINE" : "🔴 OFFLINE";
      }
      if (phoneWifiIcon) {
        phoneWifiIcon.style.opacity = phoneOnline ? "1" : "0.3";
      }
      if (phoneRssiBadge) {
        phoneRssiBadge.textContent = phoneOnline ? (state.dhcpInestable ? "-79 dBm (Débil)" : "-62 dBm") : "---";
      }
      if (phoneDeviceLbl) {
        phoneDeviceLbl.textContent = `Persiana Salón (${state.dispositivo.toUpperCase()})`;
      }
      if (phoneOfflineOverlay) {
        phoneOfflineOverlay.classList.toggle("hidden", phoneOnline);
      }

      // 8. Pulsador de Marco C-Pulsar
      if (svgMarcoLed) {
        if (state.averiaActiva === "cpulsar_bus_cortado") {
          svgMarcoLed.setAttribute("fill", "#ef4444");
        } else {
          svgMarcoLed.setAttribute("fill", "#c084fc");
        }
      }

      // 9. Telemetría SCADA KPIs
      if (scadaKpiRelays) {
        const k1Txt = state.releK1Cerrado ? "K1 CERRADO (▲)" : "K1 ABIERTO";
        const k2Txt = state.releK2Cerrado ? "K2 CERRADO (▼)" : "K2 ABIERTO";
        scadaKpiRelays.textContent = `Relés: ${k1Txt} | ${k2Txt}`;
        scadaKpiRelays.className = (state.releK1Cerrado || state.releK2Cerrado)
          ? "text-[10px] font-mono px-2 py-0.5 rounded bg-teal-900/40 text-teal-300 border border-teal-500/40"
          : "text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700";
      }

      actualizarAsesoria(state.averiaActiva || "nominal");
      actualizarVistaPersiana();
    }

    // =====================================================================
    // ASESORÍA TÉCNICA DINÁMICA SAT
    // =====================================================================
    function actualizarAsesoria(claveAveria) {
      const diag = LAB_DIAGNOSTICOS_AVERIAS[claveAveria] || LAB_DIAGNOSTICOS_AVERIAS["nominal"];
      if (asesoriaIcono) asesoriaIcono.textContent = diag.icono;
      if (asesoriaTitulo) asesoriaTitulo.textContent = diag.titulo;
      if (asesoriaMensaje) asesoriaMensaje.textContent = diag.mensaje;

      if (asesoriaCaja) {
        if (diag.tipo === "peligro") {
          asesoriaCaja.className = "p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-200 flex flex-col sm:flex-row items-start justify-between gap-3 transition-all";
        } else if (diag.tipo === "alerta" || diag.tipo === "advertencia") {
          asesoriaCaja.className = "p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex flex-col sm:flex-row items-start justify-between gap-3 transition-all";
        } else {
          asesoriaCaja.className = "p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-xs text-cyan-200 flex flex-col sm:flex-row items-start justify-between gap-3 transition-all";
        }
      }

      if (btnLabVerManual) {
        if (diag.manual) {
          btnLabVerManual.classList.remove("hidden");
          btnLabVerManual.onclick = () => {
            if (typeof window.abrirVisorPDF === "function") {
              window.abrirVisorPDF(diag.manual.nombre, diag.manual.archivo, diag.manual.pagina, 10, "tecnico", state.dispositivo);
            }
          };
        } else {
          btnLabVerManual.classList.add("hidden");
        }
      }
    }

    // =====================================================================
    // MANEJADORES DE EVENTOS DEL CUADRO Y DOCK
    // =====================================================================
    if (btnBreakerToggle) {
      btnBreakerToggle.addEventListener("click", () => {
        state.alimentacion230v = !state.alimentacion230v;
        playBreakerSound(state.alimentacion230v);
        if (!state.alimentacion230v) {
          pararManiobra();
          actualizarAsesoria("corte_termico");
        } else {
          actualizarAsesoria(state.averiaActiva || "nominal");
        }
        actualizarVista();
      });
    }

    if (btnDiffTest) {
      btnDiffTest.addEventListener("click", () => {
        state.alimentacion230v = false;
        playBreakerSound(false);
        pararManiobra();
        actualizarAsesoria("corte_termico");
        actualizarVista();
      });
    }

    // Selector de Sondas de Multímetro
    btnsSondas.forEach((btn) => {
      btn.addEventListener("click", () => {
        state.sondaActiva = btn.dataset.sonda;
        btnsSondas.forEach((b) => {
          b.className = "btn-lab-sonda px-1.5 py-1 rounded border text-center transition-all bg-black/40 border-white/10 text-slate-400 hover:text-slate-200";
        });
        btn.className = "btn-lab-sonda px-1.5 py-1 rounded border text-center transition-all bg-teal-500/20 border-teal-500 text-teal-200 font-bold";
        actualizarVista();
      });
    });

    // Clic en Puntos de Prueba del SVG
    if (probePoints.l) probePoints.l.addEventListener("click", () => activarSonda("l_n"));
    if (probePoints.n) probePoints.n.addEventListener("click", () => activarSonda("n_pe"));
    if (probePoints.pe) probePoints.pe.addEventListener("click", () => activarSonda("l_pe"));
    if (probePoints.out1) probePoints.out1.addEventListener("click", () => activarSonda("out_up"));
    if (probePoints.out2) probePoints.out2.addEventListener("click", () => activarSonda("out_down"));
    if (probePoints.bus) probePoints.bus.addEventListener("click", () => activarSonda("bus_cpulsar"));

    function activarSonda(nombreSonda) {
      state.sondaActiva = nombreSonda;
      btnsSondas.forEach((b) => {
        if (b.dataset.sonda === nombreSonda) {
          b.className = "btn-lab-sonda px-1.5 py-1 rounded border text-center transition-all bg-teal-500/20 border-teal-500 text-teal-200 font-bold";
        } else {
          b.className = "btn-lab-sonda px-1.5 py-1 rounded border text-center transition-all bg-black/40 border-white/10 text-slate-400 hover:text-slate-200";
        }
      });
      actualizarVista();
    }

    // Selector de Dispositivo
    if (selectDispositivo) {
      selectDispositivo.addEventListener("change", (e) => {
        state.dispositivo = e.target.value;
        if (state.dispositivo === "c-wall" && state.averiaActiva === "falta_neutro") {
          state.faltaNeutro = true;
        } else {
          state.faltaNeutro = (state.averiaActiva === "falta_neutro");
        }
        actualizarVista();
      });
    }

    // Sensores Connect-2
    if (btnSensorViento) {
      btnSensorViento.addEventListener("click", () => {
        state.sensorVientoActivo = !state.sensorVientoActivo;
        if (ledSensorViento) {
          ledSensorViento.className = state.sensorVientoActivo ? "w-2 h-2 rounded-full bg-cyan-400 animate-ping" : "w-2 h-2 rounded-full bg-slate-600";
        }
        if (state.sensorVientoActivo) {
          // Maniobra automática de repliegue por seguridad (subir al 100%)
          iniciarManiobra("subir");
          if (scadaFcStatus) scadaFcStatus.textContent = "¡Seguridad Viento Activa! Subiendo persiana automáticamente.";
        }
      });
    }

    if (btnSensorLluvia) {
      btnSensorLluvia.addEventListener("click", () => {
        state.sensorLluviaActivo = !state.sensorLluviaActivo;
        if (ledSensorLluvia) {
          ledSensorLluvia.className = state.sensorLluviaActivo ? "w-2 h-2 rounded-full bg-cyan-400 animate-ping" : "w-2 h-2 rounded-full bg-slate-600";
        }
        if (state.sensorLluviaActivo) {
          // Maniobra automática de cierre por lluvia (bajar al 0%)
          iniciarManiobra("bajar");
          if (scadaFcStatus) scadaFcStatus.textContent = "¡Sensor de Lluvia Activo! Cerrando persiana automáticamente.";
        }
      });
    }

    // Inyector de Averías Canónicas
    btnsAverias.forEach((btn) => {
      btn.addEventListener("click", () => {
        const averia = btn.dataset.averia;

        if (state.averiaActiva === averia) {
          // Desactivar avería
          state.averiaActiva = null;
          state.sentidoInvertido = false;
          state.alimentacion230v = true;
          state.bandaWifi = "2.4";
          state.cgnatActivo = false;
          state.sobrecargaTermica = false;
          state.faltaNeutro = false;
          state.klixonDisparado = false;
          state.pulsadorModo = "monoestable";
          state.dhcpInestable = false;
        } else {
          // Activar avería seleccionada
          state.averiaActiva = averia;
          state.sentidoInvertido = (averia === "fase_invertida");
          state.alimentacion230v = (averia !== "corte_termico");
          state.bandaWifi = (averia === "wifi_incompatible") ? "5.0" : "2.4";
          state.cgnatActivo = (averia === "wifi_incompatible");
          state.sobrecargaTermica = (averia === "bloqueo_mecanico");
          state.faltaNeutro = (averia === "falta_neutro");
          state.klixonDisparado = (averia === "klixon_motor");
          state.pulsadorModo = (averia === "pulsador_mono_bi") ? "biestable" : "monoestable";
          state.dhcpInestable = (averia === "dhcp_lease_mesh");

          if (averia === "cpulsar_bus_cortado") {
            state.dispositivo = "c-pulsar";
            if (selectDispositivo) selectDispositivo.value = "c-pulsar";
          }
          if (averia === "falta_neutro") {
            state.dispositivo = "c-wall";
            if (selectDispositivo) selectDispositivo.value = "c-wall";
            activarSonda("n_pe");
          }
          if (averia === "bloqueo_mecanico" || averia === "corte_termico" || averia === "klixon_motor") {
            pararManiobra();
          }
        }

        // Refresco de LEDs en botones de averías
        btnsAverias.forEach((b) => {
          const led = b.querySelector(".averia-led");
          if (b.dataset.averia === state.averiaActiva) {
            b.classList.add("border-rose-500/60", "bg-rose-950/20");
            if (led) { led.className = "w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm averia-led animate-pulse shrink-0"; }
          } else {
            b.classList.remove("border-rose-500/60", "bg-rose-950/20");
            if (led) { led.className = "w-2.5 h-2.5 rounded-full bg-slate-600 averia-led shrink-0"; }
          }
        });

        actualizarVista();
      });
    });

    // Smartphone Virtual
    if (btnPhoneSubir) {
      btnPhoneSubir.addEventListener("click", () => {
        const wifiOk = state.wifiActivo && state.bandaWifi === "2.4" && !state.cgnatActivo && state.averiaActiva !== "wifi_incompatible" && !state.dhcpInestable;
        if (!wifiOk || !state.alimentacion230v || state.faltaNeutro) return;
        iniciarManiobra("subir");
      });
    }

    if (btnPhoneParar) {
      btnPhoneParar.addEventListener("click", () => {
        pararManiobra();
      });
    }

    if (btnPhoneBajar) {
      btnPhoneBajar.addEventListener("click", () => {
        const wifiOk = state.wifiActivo && state.bandaWifi === "2.4" && !state.cgnatActivo && state.averiaActiva !== "wifi_incompatible" && !state.dhcpInestable;
        if (!wifiOk || !state.alimentacion230v || state.faltaNeutro) return;
        iniciarManiobra("bajar");
      });
    }

    if (phoneSlider) {
      phoneSlider.addEventListener("input", (e) => {
        const wifiOk = state.wifiActivo && state.bandaWifi === "2.4" && !state.cgnatActivo && state.averiaActiva !== "wifi_incompatible" && !state.dhcpInestable;
        if (!wifiOk || !state.alimentacion230v || state.faltaNeutro) return;
        const targetPct = parseFloat(e.target.value);
        state.posicionObjetivo = targetPct;
        if (targetPct > state.posicionPersiana) {
          iniciarManiobra("subir");
        } else if (targetPct < state.posicionPersiana) {
          iniciarManiobra("bajar");
        }
      });
    }

    if (chkPhoneInvertirGiro) {
      chkPhoneInvertirGiro.addEventListener("change", (e) => {
        state.sentidoInvertidoApp = e.target.checked;
        actualizarVista();
      });
    }

    if (btnPhoneAutoCalibrar) {
      btnPhoneAutoCalibrar.addEventListener("click", () => {
        if (state.autoCalibrando) return;
        state.autoCalibrando = true;
        const origText = btnPhoneAutoCalibrar.innerHTML;
        btnPhoneAutoCalibrar.innerHTML = "<span>⏳</span> Calibrando recorrido...";
        btnPhoneAutoCalibrar.disabled = true;

        // Rutina oficial: 1) Subir hasta FC arriba -> 2) Pausa -> 3) Bajar hasta FC abajo -> 4) Posición nominal 50%
        iniciarManiobra("subir");
        const intervaloCalib = setInterval(() => {
          if (state.posicionPersiana >= state.fcUpLimit) {
            clearInterval(intervaloCalib);
            setTimeout(() => {
              iniciarManiobra("bajar");
              const intervaloBajar = setInterval(() => {
                if (state.posicionPersiana <= state.fcDownLimit) {
                  clearInterval(intervaloBajar);
                  setTimeout(() => {
                    state.posicionObjetivo = 50;
                    iniciarManiobra("subir");
                    state.autoCalibrando = false;
                    btnPhoneAutoCalibrar.innerHTML = "<span>✅</span> ¡Calibrado!";
                    setTimeout(() => {
                      btnPhoneAutoCalibrar.innerHTML = origText;
                      btnPhoneAutoCalibrar.disabled = false;
                    }, 2000);
                  }, 800);
                }
              }, 200);
            }, 800);
          }
        }, 200);
      });
    }

    // Pulsador de Pared 230V
    if (svgBtnWallUp) {
      svgBtnWallUp.addEventListener("click", () => {
        if (state.pulsadorModo === "biestable") {
          // En modo biestable fija la marcha o para
          if (state.estadoMotor === "subiendo") pararManiobra();
          else iniciarManiobra("subir");
        } else {
          if (state.estadoMotor === "subiendo") pararManiobra();
          else iniciarManiobra("subir");
        }
      });
    }

    if (svgBtnWallDown) {
      svgBtnWallDown.addEventListener("click", () => {
        if (state.pulsadorModo === "biestable") {
          if (state.estadoMotor === "bajando") pararManiobra();
          else iniciarManiobra("bajar");
        } else {
          if (state.estadoMotor === "bajando") pararManiobra();
          else iniciarManiobra("bajar");
        }
      });
    }

    // Pulsador de Marco C-Pulsar
    if (svgPulsadorMarco) {
      svgPulsadorMarco.addEventListener("click", () => {
        if (state.averiaActiva === "cpulsar_bus_cortado") {
          playAlarmSound();
          actualizarAsesoria("cpulsar_bus_cortado");
          return;
        }
        if (state.estadoMotor === "parado") {
          iniciarManiobra(state.posicionPersiana < 50 ? "subir" : "bajar");
        } else {
          pararManiobra();
        }
      });
    }

    // Tornillos de Ajuste de Finales de Carrera (FC ▲ y FC ▼)
    if (screwFcUp) {
      screwFcUp.addEventListener("click", () => {
        // Cicla topes superiores entre 100%, 90% y 80%
        state.fcUpLimit = (state.fcUpLimit === 100) ? 90 : (state.fcUpLimit === 90 ? 80 : 100);
        if (txtFcUpVal) txtFcUpVal.textContent = `${state.fcUpLimit}%`;
        if (scadaFcStatus) scadaFcStatus.textContent = `Ajustado FC Superior a ${state.fcUpLimit}%`;
        playRelayClick();
      });
    }

    if (screwFcDown) {
      screwFcDown.addEventListener("click", () => {
        // Cicla topes inferiores entre 0%, 10% y 20%
        state.fcDownLimit = (state.fcDownLimit === 0) ? 10 : (state.fcDownLimit === 10 ? 20 : 0);
        if (txtFcDownVal) txtFcDownVal.textContent = `${state.fcDownLimit}%`;
        if (scadaFcStatus) scadaFcStatus.textContent = `Ajustado FC Inferior a ${state.fcDownLimit}%`;
        playRelayClick();
      });
    }

    // Botones de Cabecera: Sonido, Swap, Reset, Generar Ticket, WhatsApp, Fullscreen
    if (btnLabSoundToggle) {
      btnLabSoundToggle.addEventListener("click", () => {
        state.audioHabilitado = !state.audioHabilitado;
        if (labSoundIcon) labSoundIcon.textContent = state.audioHabilitado ? "🔊" : "🔇";
        if (labSoundTxt) labSoundTxt.textContent = state.audioHabilitado ? "Audio ON" : "Silencio";
        if (!state.audioHabilitado) stopMotorHum();
      });
    }

    if (btnLabSwap) {
      btnLabSwap.addEventListener("click", () => {
        state.sentidoInvertido = !state.sentidoInvertido;
        playRelayClick();
        actualizarVista();
      });
    }

    if (btnLabReset) {
      btnLabReset.addEventListener("click", () => {
        state.alimentacion230v = true;
        state.sentidoInvertido = false;
        state.sentidoInvertidoApp = false;
        state.averiaActiva = null;
        state.bandaWifi = "2.4";
        state.cgnatActivo = false;
        state.sobrecargaTermica = false;
        state.faltaNeutro = false;
        state.klixonDisparado = false;
        state.pulsadorModo = "monoestable";
        state.dhcpInestable = false;
        state.fcUpLimit = 100;
        state.fcDownLimit = 0;
        state.posicionPersiana = 50;
        state.sondaActiva = "l_n";
        pararManiobra();

        if (chkPhoneInvertirGiro) chkPhoneInvertirGiro.checked = false;
        if (txtFcUpVal) txtFcUpVal.textContent = "100%";
        if (txtFcDownVal) txtFcDownVal.textContent = "0%";

        btnsAverias.forEach((b) => {
          b.classList.remove("border-rose-500/60", "bg-rose-950/20");
          const led = b.querySelector(".averia-led");
          if (led) led.className = "w-2.5 h-2.5 rounded-full bg-slate-600 averia-led shrink-0";
        });

        activarSonda("l_n");
        actualizarVista();
      });
    }

    // Botón Generar Ticket SAT desde el Laboratorio
    if (btnLabGenerarTicket) {
      btnLabGenerarTicket.addEventListener("click", () => {
        const diag = LAB_DIAGNOSTICOS_AVERIAS[state.averiaActiva || "nominal"];
        const ticketData = {
          instalador: "Soporte Técnico Laboratorio",
          dispositivo: state.dispositivo.toUpperCase(),
          motor: "Mecánico 4 Hilos 230V",
          obra: "Banco de Pruebas Laboratorio",
          sintoma: state.averiaActiva ? diag.titulo : `Comportamiento en banco de pruebas: persiana al ${Math.round(state.posicionPersiana)}%`,
          diagnostico: diag.mensaje,
          solucion: `Parámetros registrados: Voltaje=${telemetriaVoltaje ? telemetriaVoltaje.textContent : "230V"}, Potencia=${telemetriaPotencia ? telemetriaPotencia.textContent : "0W"}. Consultar manual ${diag.manual ? diag.manual.nombre : "Connect"}.`,
          estado: "en_espera",
          prioridad: (diag.tipo === "peligro") ? "urgente" : "normal"
        };

        if (typeof window.abrirModalTicket === "function") {
          window.abrirModalTicket(ticketData, false);
        } else if (typeof window.abrirVistaDirecta === "function") {
          window.abrirVistaDirecta("tickets");
        }
      });
    }

    // Botón Copiar a WhatsApp
    if (btnLabWpShare) {
      btnLabWpShare.addEventListener("click", () => {
        const diag = LAB_DIAGNOSTICOS_AVERIAS[state.averiaActiva || "nominal"];
        const textoWp = `*🔬 INFORME TÉCNICO DE LABORATORIO - IOT FENSTER*
*Dispositivo:* ${state.dispositivo.toUpperCase()}
*Estado 230V:* ${state.alimentacion230v ? "Activo (PIA ON)" : "Sin Tensión (PIA OFF)"}
*Lectura Multímetro (${state.sondaActiva.toUpperCase()}):* ${telemetriaVoltaje ? telemetriaVoltaje.textContent : "230V"} | ${telemetriaPotencia ? telemetriaPotencia.textContent : "0W"}
*Posición Persiana:* ${Math.round(state.posicionPersiana)}%
*Giro Invertido:* ${state.sentidoInvertido ? "SÍ (Cables permutados)" : "NO (Estándar)"}

*🔍 Diagnóstico:*
${diag.titulo}
${diag.mensaje}

_Emitido desde el Laboratorio de Simulación Técnica IoT Fenster_`;

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textoWp).then(() => {
            const orig = btnLabWpShare.innerHTML;
            btnLabWpShare.innerHTML = "<span>✅</span> ¡Copiado!";
            setTimeout(() => { btnLabWpShare.innerHTML = orig; }, 2500);
          });
        } else {
          alert(textoWp);
        }
      });
    }

    // Pantalla Completa
    if (btnLabFullscreen && labDiagramCard) {
      btnLabFullscreen.addEventListener("click", () => {
        state.fullscreen = !state.fullscreen;
        if (state.fullscreen) {
          labDiagramCard.classList.add("lab-fullscreen");
          if (labFsIcon) labFsIcon.textContent = "✕";
          if (labFsTexto) labFsTexto.textContent = "Salir Pantalla Completa";
        } else {
          labDiagramCard.classList.remove("lab-fullscreen");
          if (labFsIcon) labFsIcon.textContent = "⛶";
          if (labFsTexto) labFsTexto.textContent = "Pantalla Completa";
        }
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && state.fullscreen) {
          state.fullscreen = false;
          labDiagramCard.classList.remove("lab-fullscreen");
          if (labFsIcon) labFsIcon.textContent = "⛶";
          if (labFsTexto) labFsTexto.textContent = "Pantalla Completa";
        }
      });
    }

    // Inicializar estado visual y arrancar bucle de animación continua
    actualizarVista();
    requestAnimationFrame(bucleAnimacion);
  }

  // Exposición en ámbito global para index.html y app.js
  window.inicializarLaboratorioIntegral = inicializarLaboratorioIntegral;
  window.ejecutarInicializacionLaboratorio = inicializarLaboratorioIntegral;

  // Auto-arranque si la vista está activa o tras cargar el DOM
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      const vistaLab = document.getElementById("vista-laboratorio");
      if (vistaLab && vistaLab.classList.contains("vista-activa")) {
        inicializarLaboratorioIntegral();
      }
    });
  } else {
    const vistaLab = document.getElementById("vista-laboratorio");
    if (vistaLab && vistaLab.classList.contains("vista-activa")) {
      inicializarLaboratorioIntegral();
    }
  }

})();

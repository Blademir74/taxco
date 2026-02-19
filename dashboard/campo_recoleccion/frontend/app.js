// Configuración
const API_URL = 'https://taxco-backend-api.onrender.com/api';
// Para pruebas locales: 'http://localhost:8000/api'

const STORAGE_KEY = 'diagnosticos_pendientes';

let seccionesData = []; // guardar el listado con insights

document.addEventListener('DOMContentLoaded', function() {
    cargarSecciones();
    mostrarPendientes();
    if ('geolocation' in navigator) {
        obtenerUbicacion();
    }
});

async function cargarSecciones() {
    try {
        const response = await fetch(`${API_URL}/secciones`);
        seccionesData = await response.json();
        const select = document.getElementById('seccion');
        select.innerHTML = '<option value="">Selecciona una sección</option>';
        seccionesData.forEach(s => {
            const option = document.createElement('option');
            option.value = s.seccion;
            option.textContent = `Sección ${s.seccion}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error cargando secciones:', error);
        mostrarAlerta('No se pudieron cargar las secciones. Verifica tu conexión.', 'warning');
    }
}

function mostrarAlerta(mensaje, tipo) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo}`;
    alertDiv.textContent = mensaje;
    document.querySelector('.container').prepend(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

// Mostrar insight cuando se selecciona una sección
document.getElementById('seccion').addEventListener('change', function(e) {
    const seccion = parseInt(e.target.value);
    if (!seccion) {
        document.getElementById('insight-seccion').innerHTML = '';
        return;
    }
    const data = seccionesData.find(s => s.seccion === seccion);
    if (data && data.insight) {
        document.getElementById('insight-seccion').innerHTML = `
            <div class="insight-box">
                <strong>🔍 Insight:</strong> ${data.insight}
            </div>
        `;
    } else {
        document.getElementById('insight-seccion').innerHTML = '';
    }
});

// Obtener ubicación GPS
function obtenerUbicacion() {
    navigator.geolocation.getCurrentPosition(
        position => {
            document.getElementById('latitud').value = position.coords.latitude;
            document.getElementById('longitud').value = position.coords.longitude;
        },
         error => {
                // Error controlado: no se pudo obtener ubicación, pero no detenemos el flujo
                console.warn('Error de geolocalización:', error.message);
                // No mostramos alerta al usuario para no molestar, solo registro
            }
    );
}

// Capturar foto con la cámara
document.getElementById('btn-camera').addEventListener('click', function() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                document.getElementById('foto-base64').value = ev.target.result;
                mostrarAlerta('Foto capturada y lista para enviar.', 'success');
            };
            reader.onerror = function() {
                console.error('Error al leer el archivo');
                mostrarAlerta('Error al procesar la foto.', 'danger');
            };
            reader.readAsDataURL(file);
        }
    };
    
    input.onerror = function() {
        console.error('Error al acceder a la cámara');
        mostrarAlerta('No se pudo acceder a la cámara. Verifica permisos.', 'danger');
    };
    
    input.click();
});
// Guardar en LocalStorage (offline)
function guardarOffline(diagnostico) {
    let pendientes = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    pendientes.push(diagnostico);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pendientes));
    mostrarAlerta('Diagnóstico guardado localmente. Se sincronizará automáticamente cuando haya conexión.', 'success');
    mostrarPendientes();
    // Intentar sincronización en segundo plano si hay sync manager
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
        navigator.serviceWorker.ready.then(reg => {
            reg.sync.register('sync-diagnosticos');
        });
    }
}

// Sincronizar manualmente
async function sincronizar() {
    const pendientes = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    if (pendientes.length === 0) {
        mostrarAlerta('No hay datos pendientes de sincronizar.', 'info');
        return;
    }

    const btn = document.querySelector('.btn-sync');
    btn.disabled = true;
    btn.textContent = 'Sincronizando...';

    let exitosos = 0;
    for (let diag of pendientes) {
        try {
            const response = await fetch(`${API_URL}/recoleccion`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(diag)
            });
            if (response.ok) {
                exitosos++;
            } else {
                console.error('Error en diagnóstico:', diag);
            }
        } catch (error) {
            console.error('Error de red:', error);
        }
    }

    if (exitosos === pendientes.length) {
        localStorage.removeItem(STORAGE_KEY);
        mostrarAlerta(`¡Sincronización completa! ${exitosos} diagnósticos enviados.`, 'success');
    } else {
        const nuevosPendientes = pendientes.slice(exitosos);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(nuevosPendientes));
        mostrarAlerta(`Se sincronizaron ${exitosos} de ${pendientes.length}. Los restantes se mantienen locales.`, 'warning');
    }

    btn.disabled = false;
    btn.textContent = 'Sincronizar datos pendientes';
    mostrarPendientes();
}

function mostrarPendientes() {
    const pendientes = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    const span = document.getElementById('pendientes-count');
    if (span) span.textContent = pendientes.length;
}

// Manejar envío del formulario
document.getElementById('diagnosticoForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const seccion = parseInt(document.getElementById('seccion').value);
    if (!seccion) {
        mostrarAlerta('Debes seleccionar una sección.', 'danger');
        return;
    }

    // Validar género obligatorio
    const esMujer = document.querySelector('input[name="genero"]:checked');
    if (!esMujer) {
        mostrarAlerta('Debes indicar el género de la persona.', 'danger');
        return;
    }

    const agua = parseInt(document.querySelector('input[name="agua"]:checked')?.value || 3);
    const basura = parseInt(document.querySelector('input[name="basura"]:checked')?.value || 3);
    const seguridad = parseInt(document.querySelector('input[name="seguridad"]:checked')?.value || 3);

    const carencias = {
        falta_agua: document.getElementById('falta_agua').checked,
        falta_drenaje: document.getElementById('falta_drenaje').checked,
        rezago_educativo: document.getElementById('rezago_educativo').checked
    };

    const simpatizante = {
        nombre: document.getElementById('nombre').value,
        contacto: document.getElementById('contacto').value,
        es_mujer: esMujer.value === 'femenino',
        notas: document.getElementById('notas').value
    };

    const fotoBase64 = document.getElementById('foto-base64').value;
    const evidencia = fotoBase64 ? {
        foto_base64: fotoBase64,
        comentario: document.getElementById('comentario-foto').value
    } : null;

    const latitud = parseFloat(document.getElementById('latitud').value) || null;
    const longitud = parseFloat(document.getElementById('longitud').value) || null;

    const diagnostico = {
        seccion: seccion,
        sentimiento: { agua, basura, seguridad },
        carencias: carencias,
        simpatizante: simpatizante,
        evidencia: evidencia,
        latitud: latitud,
        longitud: longitud,
        fecha_recoleccion: new Date().toISOString()
    };

    // Intentar envío directo
    try {
        const response = await fetch(`${API_URL}/recoleccion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(diagnostico)
        });
        if (response.ok) {
            mostrarAlerta('Diagnóstico enviado correctamente.', 'success');
            this.reset();
            document.getElementById('foto-base64').value = '';
            document.getElementById('insight-seccion').innerHTML = '';
            // Reiniciar GPS
            obtenerUbicacion();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Error en el servidor');
        }
    } catch (error) {
        console.warn('Error de conexión, guardando localmente:', error);
        guardarOffline(diagnostico);
        this.reset();
        document.getElementById('foto-base64').value = '';
        document.getElementById('insight-seccion').innerHTML = '';
    }
});
// Campo "Ubicación" (class="o_geo_location" en la vista): al tocarlo vacío,
// pide el GPS del teléfono y escribe el nombre del lugar (calle, número, colonia, ciudad).

function setStatus(input, text) {
    input.placeholder = text;
}

function fillLocation(input, address) {
    if (input.value) {
        return; // el técnico ya escribió algo mientras tanto
    }
    input.value = address;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
}

async function onPosition(input, position) {
    const params = new URLSearchParams({
        lat: position.coords.latitude,
        lon: position.coords.longitude,
    });
    try {
        const response = await fetch(`/gestion_servicios/reverse_geocode?${params}`, {
            credentials: "same-origin",
        });
        const data = response.ok ? await response.json() : {};
        if (data.address) {
            setStatus(input, input.dataset.geoPlaceholder);
            fillLocation(input, data.address);
        } else {
            setStatus(input, "No se encontró el nombre del lugar. Escríbelo a mano.");
        }
    } catch {
        setStatus(input, "No se pudo obtener la dirección. Intenta de nuevo o escríbela a mano.");
    } finally {
        delete input.dataset.geoLocating;
    }
}

function onError(input, error) {
    delete input.dataset.geoLocating;
    setStatus(
        input,
        error.code === error.PERMISSION_DENIED
            ? "Permiso de ubicación denegado. Actívalo en el navegador y vuelve a tocar aquí."
            : "No se pudo obtener la ubicación. Intenta de nuevo o escríbela a mano."
    );
}

document.addEventListener("focusin", (ev) => {
    const input = ev.target;
    if (!(input instanceof HTMLInputElement) || !input.closest(".o_geo_location")) {
        return;
    }
    if (input.value || input.readOnly || input.dataset.geoLocating) {
        return;
    }
    if (!("geoPlaceholder" in input.dataset)) {
        input.dataset.geoPlaceholder = input.placeholder;
    }
    if (!navigator.geolocation) {
        setStatus(input, "Este dispositivo no permite obtener la ubicación.");
        return;
    }
    input.dataset.geoLocating = "1";
    setStatus(input, "Buscando tu ubicación…");
    navigator.geolocation.getCurrentPosition(
        (position) => onPosition(input, position),
        (error) => onError(input, error),
        { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
    );
});
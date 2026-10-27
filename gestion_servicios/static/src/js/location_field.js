import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { onMounted, onWillUnmount, useRef } from "@odoo/owl";

// Campo "Ubicación": al tocarlo vacío, pide el GPS del teléfono y escribe
// el nombre del lugar (calle, número, colonia, ciudad).
export class GeoLocationField extends CharField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.geoInput = useRef("input");
        this.locating = false;
        this.onFocus = this.onFocus.bind(this);
        onMounted(() => this.geoInput.el?.addEventListener("focus", this.onFocus));
        onWillUnmount(() => this.geoInput.el?.removeEventListener("focus", this.onFocus));
    }

    hasValue() {
        return Boolean(this.props.record.data[this.props.name] || this.geoInput.el?.value);
    }

    onFocus() {
        if (this.props.readonly || this.locating || this.hasValue()) {
            return;
        }
        if (!navigator.geolocation) {
            this.notification.add(_t("Este dispositivo no permite obtener la ubicación."), {
                type: "warning",
            });
            return;
        }
        this.locating = true;
        this.notification.add(_t("Buscando tu ubicación…"), { type: "info" });
        navigator.geolocation.getCurrentPosition(
            (position) => this.onPosition(position),
            (error) => this.onError(error),
            { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
        );
    }

    async onPosition(position) {
        try {
            const address = await this.orm.call("servicio.inspeccion", "reverse_geocode", [
                position.coords.latitude,
                position.coords.longitude,
            ]);
            if (!address) {
                this.notification.add(
                    _t("No se encontró el nombre del lugar. Escríbelo a mano."),
                    { type: "warning" }
                );
            } else if (!this.hasValue()) {
                // Si el técnico ya escribió algo mientras tanto, no se lo borramos
                await this.props.record.update({ [this.props.name]: address });
            }
        } finally {
            this.locating = false;
        }
    }

    onError(error) {
        this.locating = false;
        const message =
            error.code === error.PERMISSION_DENIED
                ? _t("Permiso de ubicación denegado. Actívalo en el navegador y vuelve a tocar el campo.")
                : _t("No se pudo obtener la ubicación. Intenta de nuevo o escríbela a mano.");
        this.notification.add(message, { type: "warning" });
    }
}

registry.category("fields").add("geo_location_char", {
    ...charField,
    component: GeoLocationField,
});
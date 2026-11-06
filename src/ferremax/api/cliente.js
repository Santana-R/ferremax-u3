"use strict";
const el = (id) => document.getElementById(id);
let quotes = [], selected = null, saving = false, fresh = false;
const date = (value) => new Intl.DateTimeFormat("es-MX", {
  dateStyle: "long", timeStyle: "short", timeZone: "America/Monterrey"
}).format(new Date(value)) + " (hora de Monterrey)";
const money = (value, currency) => {
  try { return new Intl.NumberFormat("es-MX", {style: "currency", currency}).format(value) + " " + currency; }
  catch { return Number(value).toFixed(2) + " " + currency; }
};
function message(title, text, error = false) {
  el("result-title").textContent = title; el("result-text").textContent = text;
  el("result").classList.toggle("error", error); el("result").hidden = false; el("result").focus();
}
function total() {
  const sums = new Map();
  for (const row of el("products").children) {
    const currency = row.querySelector("[data-field=moneda]").value.trim();
    const quantity = Number(row.querySelector("[data-field=cantidad]").value);
    const price = Number(row.querySelector("[data-field=precio_unitario]").value);
    sums.set(currency, (sums.get(currency) || 0) + quantity * price);
  }
  // Estimación visual. El servidor valida y guarda los importes con Decimal.
  el("total").textContent = [...sums].map(([c, v]) => money(v, c)).join(" + ");
}
function field(row, labelText, name, value, index) {
  const wrap = document.createElement("div"), label = document.createElement("label");
  const input = document.createElement("input");
  input.id = `${name}-${index}`; input.dataset.field = name; input.value = value;
  label.htmlFor = input.id; label.textContent = labelText; input.required = true;
  if (name === "moneda") input.readOnly = true;
  else {
    input.type = "number"; input.step = "any"; input.min = "0";
    if (name === "cantidad") input.addEventListener("input", () => input.setCustomValidity(Number(input.value) > 0 ? "" : "Indica una cantidad mayor que cero."));
  }
  input.addEventListener("input", total); wrap.append(label, input); row.append(wrap);
}
function choose() {
  selected = quotes.find(q => q.id === el("quote").value) || null;
  el("quote-details").hidden = !selected; el("renew-form").hidden = !selected;
  el("empty").hidden = !!selected; el("products").replaceChildren();
  el("fields").disabled = !selected || !selected.renovable || saving || !fresh;
  el("submit").disabled = el("fields").disabled;
  el("blocked").hidden = !selected || selected.renovable;
  if (!selected) return;
  el("folio").textContent = selected.folio; el("state").textContent = selected.estado;
  el("state").classList.toggle("current", !selected.renovable); el("expiry").textContent = date(selected.vencimiento);
  const explanation = selected.renovable ? "Esta cotización ya venció. Puedes renovar sus precios y condiciones."
    : selected.estado === "Vigente" ? "Esta cotización todavía está vigente y puedes seguir utilizándola. No necesita renovación."
    : "Esta cotización aún no ha sido emitida. Todavía no se puede renovar.";
  el("eligibility").textContent = explanation; el("blocked").textContent = explanation;
  el("conditions").value = selected.condiciones; el("days").value = "7"; el("reason").value = "";
  selected.partidas.forEach((p, i) => {
    const card = document.createElement("div"), title = document.createElement("div");
    card.className = "product"; title.className = "product-title"; title.textContent = "Producto " + p.sku; card.append(title);
    const fields = document.createElement("div"); fields.className = "product-fields";
    field(fields, "Cantidad", "cantidad", p.cantidad, i); field(fields, "Precio por unidad", "precio_unitario", p.precio_unitario, i);
    field(fields, "Moneda", "moneda", p.moneda, i); card.append(fields); el("products").append(card);
  });
  total();
}
async function load(preferred, reportError = true) {
  fresh = false; el("refresh").disabled = true; el("quote").disabled = true;
  el("fields").disabled = true; el("submit").disabled = true;
  el("load-status").textContent = "Estamos consultando tus cotizaciones.";
  try {
    const response = await fetch("/cliente/cotizaciones", {cache: "no-store"});
    if (!response.ok) throw new Error("unavailable");
    const body = await response.json(); quotes = body.cotizaciones; fresh = true;
    el("quote").replaceChildren(new Option("Selecciona una cotización", ""));
    for (const q of quotes) el("quote").add(new Option(q.folio + " · " + q.estado, q.id));
    if (preferred && quotes.some(q => q.id === preferred)) el("quote").value = preferred;
    el("quote").disabled = !quotes.length;
    el("load-status").textContent = quotes.length ? "Elige el folio que deseas revisar." : "Todavía no hay cotizaciones registradas.";
    choose(); return true;
  } catch {
    el("load-status").textContent = "No pudimos cargar las cotizaciones. Pulsa Actualizar cotizaciones para volver a intentarlo.";
    if (reportError) message("No pudimos consultar tus cotizaciones", "Inténtalo de nuevo en unos momentos. Tus datos no se han modificado.", true);
    return false;
  } finally { el("refresh").disabled = saving; }
}
function enable() {
  el("refresh").disabled = saving; el("quote").disabled = saving || !fresh || !quotes.length;
  el("fields").disabled = saving || !fresh || !selected || !selected.renovable;
  el("submit").disabled = el("fields").disabled;
}
el("quote").addEventListener("change", () => { el("result").hidden = true; choose(); });
el("refresh").addEventListener("click", async () => { await load(selected && selected.id); enable(); });
el("renew-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (saving || !fresh || !selected || !selected.renovable || !event.target.reportValidity()) return;
  if (!el("reason").value.trim() || !el("conditions").value.trim()) {
    message("Revisa los datos", "Escribe el motivo de la renovación y las condiciones acordadas con el cliente.", true); return;
  }
  const original = selected;
  const parts = [...el("products").children].map((row, i) => ({
    numero: original.partidas[i].numero, sku: original.partidas[i].sku,
    cantidad: row.querySelector("[data-field=cantidad]").value,
    precio_unitario: row.querySelector("[data-field=precio_unitario]").value, moneda: original.partidas[i].moneda
  }));
  const body = {dias_vigencia: Number(el("days").value), partidas: parts,
    motivo: el("reason").value.trim(), condiciones: el("conditions").value.trim()};
  saving = true; enable(); el("submit").textContent = "Guardando renovación…";
  el("save-status").textContent = "Espera la confirmación antes de cerrar esta página.";
  try {
    const response = await fetch(`/cotizaciones/${encodeURIComponent(original.id)}/versiones/${original.version}/revalidar`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
    });
    const result = await response.json();
    if (!response.ok) {
      const copy = {
        "Ya existe la siguiente versión de esta cotización. Usa la versión más reciente.": "Esta cotización ya se renovó. Actualiza las cotizaciones para consultar la información más reciente.",
        "La cotización todavía está vigente; esta operación revalida cotizaciones vencidas.": "Esta cotización todavía está vigente. Puedes seguir utilizándola sin renovarla.",
        "Cotización o versión no encontrada.": "No encontramos la cotización seleccionada. Actualiza las cotizaciones y vuelve a elegirla."
      };
      message("No se pudo renovar la cotización", copy[result.mensaje] || result.mensaje || "Revisa los datos e inténtalo de nuevo.", true);
      if (response.status === 409 || response.status === 404) await load(original.id, false);
      return;
    }
    const refreshed = await load(original.id, false);
    const updated = quotes.find(q => q.id === original.id && q.version === result.version);
    const expires = refreshed && updated ? " Puedes utilizarla hasta el " + date(updated.vencimiento) + "." : " Actualiza las cotizaciones para consultar su nueva vigencia.";
    message("Cotización renovada", "La cotización " + result.folio + " se renovó correctamente." + expires + " La cotización anterior quedó guardada en el historial.");
  } catch {
    fresh = false;
    message("Necesitamos comprobar la renovación", "Se interrumpió la conexión y no podemos confirmar si se guardó. Actualiza las cotizaciones antes de volver a intentarlo; así evitarás repetir la operación.", true);
  } finally {
    saving = false; el("submit").textContent = "Renovar cotización"; el("save-status").textContent = ""; enable();
  }
});
load();

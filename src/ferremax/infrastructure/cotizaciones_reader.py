"""Proyección de lectura para elegir cotizaciones sin conocer UUID/versiones."""

from ferremax.infrastructure.postgres import PostgresReader, _cotizacion


class PostgresCotizacionesReader(PostgresReader):
    def listar_actuales(self, ahora):
        filas = self._leer(
            "SELECT datos FROM (SELECT DISTINCT ON (id) id, version, folio, datos "
            "FROM ferremax_u3.cotizacion_version ORDER BY id, version DESC) actuales "
            "ORDER BY folio, id", (),
        )
        resultado = []
        for (documento,) in filas:
            c = _cotizacion(documento)
            estado = "Por emitir" if ahora < c.vigencia.emision else c.estado_en(ahora)
            resultado.append({
                "id": c.id, "version": c.version, "folio": c.folio,
                "estado": estado, "vencimiento": c.vigencia.vencimiento,
                "renovable": estado == "Vencida", "condiciones": c.condiciones,
                "partidas": [{"numero": p.numero, "sku": p.sku.valor,
                              "cantidad": str(p.cantidad),
                              "precio_unitario": str(p.precio.importe),
                              "moneda": p.precio.moneda} for p in c.partidas],
            })
        return resultado

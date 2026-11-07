"""Catálogos de selección para la vista de atención; consultas sin escrituras."""
from ferremax.infrastructure.postgres import PostgresReader, _pedido


class PostgresAtencionReader(PostgresReader):
    def catalogo(self):
        productos = self._leer('SELECT DISTINCT sku FROM ferremax_u3.inventario ORDER BY sku', ())
        ubicaciones = self._leer('SELECT DISTINCT ubicacion_id FROM ferremax_u3.inventario ORDER BY ubicacion_id', ())
        return {'productos': [r[0] for r in productos], 'ubicaciones': [r[0] for r in ubicaciones]}

    def pedidos(self):
        filas = self._leer('SELECT datos FROM ferremax_u3.pedido ORDER BY id', ())
        resultado = []
        codigos = [str(d['id']).replace('-', '').upper() for (d,) in filas]
        for (d,) in filas:
            p = _pedido(d)
            codigo = p.id.replace('-', '').upper()
            largo = 8
            while any(otro != codigo and otro.startswith(codigo[:largo]) for otro in codigos):
                largo += 4
            resultado.append({'id': p.id, 'referencia': 'PED-' + codigo[:largo],
                'estado': p.estado.value, 'cotizacion_folio': p.cotizacion_folio,
                'cotizacion_version': p.cotizacion_version, 'surtido': p.surtido,
                'total': str(p.total.importe), 'moneda': p.total.moneda,
                'partidas': [{'sku': a.sku.valor, 'cantidad': str(a.cantidad)} for a in p.partidas]})
        return resultado

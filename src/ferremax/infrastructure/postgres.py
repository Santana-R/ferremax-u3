from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from uuid import uuid4
from ferremax.domain.model import Cotizacion, Pedido, Partida, Dinero, SKU, Vigencia, EstadoPedido, InventarioUbicacion, ErrorNegocio

def _default(v):
    if isinstance(v,Decimal): return str(v)
    if isinstance(v,datetime): return v.isoformat()
    if isinstance(v,Enum): return v.value
    raise TypeError(type(v).__name__)
def datos(obj): return json.loads(json.dumps(asdict(obj),default=_default))
def _partida(d): return Partida(d['numero'],SKU(d['sku']['valor']),Decimal(d['cantidad']),Dinero(Decimal(d['precio']['importe']),d['precio']['moneda']))
def _cotizacion(d):
    return Cotizacion(d['id'],d['folio'],d['version'],d['cliente_id'],
      Vigencia(datetime.fromisoformat(d['vigencia']['emision']),datetime.fromisoformat(d['vigencia']['vencimiento'])),
      [_partida(p) for p in d['partidas']],d['condiciones'])
def _pedido(d):
    return Pedido(d['id'],d['cliente_id'],d['cotizacion_id'],d['cotizacion_folio'],d['cotizacion_version'],
      [_partida(p) for p in d['partidas']],EstadoPedido(d['estado']),d['surtido'],d.get('referencia_pago'))

class PgCotizaciones:
    def __init__(self,conn): self.conn=conn
    def obtener(self,id,version):
        r=self.conn.execute('SELECT datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid AND version=%s',(id,version)).fetchone()
        if r is None: raise ErrorNegocio('Cotizacion o version inexistente')
        return _cotizacion(r[0])
    def guardar_nueva_version(self,c):
        from psycopg.types.json import Jsonb
        from psycopg.errors import UniqueViolation
        try: self.conn.execute('INSERT INTO ferremax_u3.cotizacion_version(id,version,folio,datos) VALUES(%s::uuid,%s,%s,%s)',(c.id,c.version,c.folio,Jsonb(datos(c))))
        except UniqueViolation: raise ErrorNegocio('Version duplicada; vuelva a consultar')
class PgPedidos:
    def __init__(self,conn): self.conn=conn
    def obtener(self,id):
        r=self.conn.execute('SELECT datos FROM ferremax_u3.pedido WHERE id=%s::uuid FOR UPDATE',(id,)).fetchone()
        if r is None: raise ErrorNegocio('Pedido inexistente')
        return _pedido(r[0])
    def guardar(self,p):
        from psycopg.types.json import Jsonb
        self.conn.execute('INSERT INTO ferremax_u3.pedido(id,cotizacion_id,cotizacion_version,estado,datos) VALUES(%s::uuid,%s::uuid,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET estado=EXCLUDED.estado,datos=EXCLUDED.datos',
                          (p.id,p.cotizacion_id,p.cotizacion_version,p.estado.value,Jsonb(datos(p))))
class PgInventarios:
    def __init__(self,conn): self.conn=conn
    def obtener_para_actualizar(self,sku,ubicacion):
        r=self.conn.execute('SELECT existencia_fisica,en_transito FROM ferremax_u3.inventario WHERE sku=%s AND ubicacion_id=%s FOR UPDATE',(sku,ubicacion)).fetchone()
        if r is None: raise ErrorNegocio('SKU o ubicacion inexistente')
        reservas=self.conn.execute('SELECT pedido_id,cantidad FROM ferremax_u3.reserva WHERE sku=%s AND ubicacion_id=%s',(sku,ubicacion)).fetchall()
        return InventarioUbicacion(SKU(sku),ubicacion,r[0],r[1],{str(pid):q for pid,q in reservas})
    def guardar(self,i):
        i.validar()
        self.conn.execute('UPDATE ferremax_u3.inventario SET existencia_fisica=%s,comprometida=%s,en_transito=%s WHERE sku=%s AND ubicacion_id=%s',
                          (i.existencia_fisica,i.comprometida,i.en_transito,i.sku.valor,i.ubicacion_id))
        self.conn.execute('DELETE FROM ferremax_u3.reserva WHERE sku=%s AND ubicacion_id=%s',(i.sku.valor,i.ubicacion_id))
        for pid,q in i.reservas.items():
            self.conn.execute('INSERT INTO ferremax_u3.reserva(pedido_id,sku,ubicacion_id,cantidad) VALUES(%s::uuid,%s,%s,%s)',(pid,i.sku.valor,i.ubicacion_id,q))
    def ubicacion_reserva(self,id):
        filas=self.conn.execute('SELECT DISTINCT ubicacion_id FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid',(id,)).fetchall()
        if len(filas)!=1: raise ErrorNegocio('El prototipo requiere una ubicacion por pedido')
        return filas[0][0]
class PostgresUnitOfWork:
    def __init__(self,database_url): self.database_url,self.committed=database_url,False
    def __enter__(self):
        import psycopg
        self.conn=psycopg.connect(self.database_url,connect_timeout=10)
        try:
            self.conn.execute("SET LOCAL lock_timeout = '5s'")
            self.cotizaciones=PgCotizaciones(self.conn)
            self.pedidos=PgPedidos(self.conn)
            self.inventarios=PgInventarios(self.conn)
            return self
        except Exception:
            self.conn.close()
            raise
    def __exit__(self,exc_type,exc,traceback):
        try:
            if not self.committed: self.conn.rollback()
        finally: self.conn.close()
    def registrar(self,actor_id,accion,agregado_id,antes,despues,motivo,evento):
        from psycopg.types.json import Jsonb
        self.conn.execute('INSERT INTO ferremax_u3.auditoria(id,actor_id,accion,agregado_id,antes,despues,motivo,fecha) VALUES(%s::uuid,%s,%s,%s,%s,%s,%s,%s)',
           (str(uuid4()),actor_id,accion,agregado_id,Jsonb(antes),Jsonb(despues),motivo,evento.ocurrido))
        self.conn.execute('INSERT INTO ferremax_u3.outbox(id,tipo,agregado_id,datos,ocurrido) VALUES(%s::uuid,%s,%s,%s,%s)',
           (evento.id,evento.tipo,evento.agregado_id,Jsonb(evento.datos),evento.ocurrido))
    def commit(self):
        self.conn.commit()
        self.committed=True
class PostgresReader:
    def __init__(self,url): self.url=url
    def _leer(self,sql,params):
        import psycopg
        with psycopg.connect(self.url,connect_timeout=10) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            return conn.execute(sql,params).fetchall()
    def consultar_disponibilidad(self,sku):
        filas=self._leer('SELECT ubicacion_id,existencia_fisica,comprometida,en_transito,existencia_fisica-comprometida FROM ferremax_u3.inventario WHERE sku=%s ORDER BY ubicacion_id',(sku,))
        campos=['ubicacion_id','existencia_fisica','comprometida','en_transito','disponible']
        return [dict(zip(campos,map(str,fila))) for fila in filas]
    def consultar_pedido(self,id):
        filas=self._leer('SELECT datos FROM ferremax_u3.pedido WHERE id=%s::uuid',(id,))
        if not filas: raise ErrorNegocio('Pedido inexistente')
        p=_pedido(filas[0][0])
        return {'pedido_id':p.id,'estado':p.estado.value,'cotizacion_folio':p.cotizacion_folio,
                'cotizacion_version':p.cotizacion_version,'total':str(p.total.importe),'moneda':p.total.moneda}

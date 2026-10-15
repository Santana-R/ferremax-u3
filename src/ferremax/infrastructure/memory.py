from copy import deepcopy
from dataclasses import dataclass,field
from threading import RLock
from ferremax.domain.model import ErrorNegocio

@dataclass
class MemoryStore:
    datos: dict=field(default_factory=lambda:{'cotizaciones':{},'pedidos':{},'inventarios':{},'auditoria':[],'outbox':[]})
    lock: RLock=field(default_factory=RLock)
class MemoryCotizaciones:
    def __init__(self, datos): self.datos=datos
    def obtener(self, id, version):
        if (id,version) not in self.datos: raise ErrorNegocio('Cotizacion o version inexistente')
        return self.datos[(id,version)]
    def guardar_nueva_version(self, c):
        if (c.id,c.version) in self.datos: raise ErrorNegocio('Version duplicada; vuelva a consultar')
        self.datos[(c.id,c.version)]=c
class MemoryPedidos:
    def __init__(self, datos): self.datos=datos
    def obtener(self, id):
        if id not in self.datos: raise ErrorNegocio('Pedido inexistente')
        return self.datos[id]
    def guardar(self,p): self.datos[p.id]=p
class MemoryInventarios:
    def __init__(self, datos): self.datos=datos
    def obtener_para_actualizar(self,sku,ubicacion):
        if (sku,ubicacion) not in self.datos: raise ErrorNegocio('SKU o ubicacion inexistente')
        return self.datos[(sku,ubicacion)]
    def guardar(self,i): self.datos[(i.sku.valor,i.ubicacion_id)]=i
    def ubicacion_reserva(self,id):
        ubicaciones={i.ubicacion_id for i in self.datos.values() if id in i.reservas}
        if len(ubicaciones)!=1: raise ErrorNegocio('El prototipo requiere una ubicacion por pedido')
        return ubicaciones.pop()
class MemoryUnitOfWork:
    def __init__(self,store): self.store=store
    def __enter__(self):
        self.store.lock.acquire()
        self.datos=deepcopy(self.store.datos)
        self.cotizaciones=MemoryCotizaciones(self.datos['cotizaciones'])
        self.pedidos=MemoryPedidos(self.datos['pedidos'])
        self.inventarios=MemoryInventarios(self.datos['inventarios'])
        return self
    def __exit__(self,exc_type,exc,traceback): self.store.lock.release()
    def registrar(self,actor_id,accion,agregado_id,antes,despues,motivo,evento):
        self.datos['auditoria'].append({'actor_id':actor_id,'accion':accion,'agregado_id':agregado_id,
          'antes':antes,'despues':despues,'motivo':motivo,'fecha':evento.ocurrido.isoformat()})
        self.datos['outbox'].append(evento)
    def commit(self): self.store.datos=deepcopy(self.datos)
class MemoryReader:
    def __init__(self,store): self.store=store
    def consultar_disponibilidad(self,sku):
        with self.store.lock:
            return [{'ubicacion_id':i.ubicacion_id,'existencia_fisica':str(i.existencia_fisica),
              'comprometida':str(i.comprometida),'en_transito':str(i.en_transito),'disponible':str(i.disponible)}
              for (s,_),i in sorted(self.store.datos['inventarios'].items()) if s==sku]
    def consultar_pedido(self,id):
        with self.store.lock:
            p=MemoryPedidos(self.store.datos['pedidos']).obtener(id)
            return {'pedido_id':p.id,'estado':p.estado.value,'cotizacion_folio':p.cotizacion_folio,
                    'cotizacion_version':p.cotizacion_version,'total':str(p.total.importe),'moneda':p.total.moneda}

"""Datos simulados. No borra datos ni procesa cobros."""
import os
from uuid import uuid4
from ferremax.demo import crear_contexto
from ferremax.infrastructure.postgres import PostgresUnitOfWork
def main():
    store,c,_=crear_contexto(); c.folio='DEMO-'+uuid4().hex[:10]
    with PostgresUnitOfWork(os.environ['DATABASE_URL']) as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        for inv in store.datos['inventarios'].values():
            uow.conn.execute('INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica) VALUES(%s,%s,%s) ON CONFLICT(sku,ubicacion_id) DO NOTHING',
                             (inv.sku.valor,inv.ubicacion_id,inv.existencia_fisica))
        uow.commit()
    print('Cotizacion de demostracion:',c.id,'version',c.version)
if __name__=='__main__': main()

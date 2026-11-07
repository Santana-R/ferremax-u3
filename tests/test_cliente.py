"""La vista usa las operaciones existentes; los datos internos no se piden al usuario."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from ferremax.api.cliente import obtener_cotizaciones_reader
from ferremax.api.main import create_app
from ferremax.domain.model import Cotizacion, Dinero, Partida, SKU, Vigencia
from ferremax.infrastructure.cotizaciones_reader import PostgresCotizacionesReader
from ferremax.infrastructure.postgres import datos, PostgresUnitOfWork
from scripts.cargar_cotizacion_cliente_demo import CLIENTE_DEMO_ID, cargar_cliente_demo
from tests.test_api_revalidacion import AHORA, solicitud
from tests.test_api_revalidacion_postgres import preparar, versiones


def test_pantalla_y_javascript_disponibles_sin_base_y_openapi_conservado():
    with TestClient(create_app()) as client:
        page = client.get('/cliente')
        assert page.status_code == 200 and 'text/html' in page.headers['content-type']
        assert 'Renovar una cotización vencida' in page.text
        assert 'Folio de cotización' in page.text
        assert 'cotizacion_id' not in page.text
        assert client.get('/cliente/acciones.js').status_code == 200
        assert client.get('/docs').status_code == 200
        assert len(client.get('/openapi.json').json()['paths']) == 6


def test_sin_configuracion_hay_mensaje_util_en_lista_y_pantalla_accesible(monkeypatch):
    for name in ('DATABASE_URL', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app()) as client:
        response = client.get('/cliente/cotizaciones')
        assert response.status_code == 503
        assert response.json()['mensaje'].startswith('No pudimos cargar las cotizaciones')
        assert client.get('/cliente').status_code == 200


def test_lista_vacia_es_un_resultado_normal():
    class Lector:
        def listar_actuales(self, ahora): return []
    api = create_app(reloj=lambda: AHORA)
    api.dependency_overrides[obtener_cotizaciones_reader] = Lector
    with TestClient(api) as client:
        response = client.get('/cliente/cotizaciones')
        assert response.status_code == 200
        assert response.json() == {'cotizaciones': []}
        assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('emision,vencimiento,estado,renovable', [
    (-8, -1, 'Vencida', True), (-8, 0, 'Vencida', True),
    (-1, 1, 'Vigente', False), (1, 2, 'Por emitir', False),
])
def test_proyeccion_respeta_vencimiento_exclusivo_y_no_altera_cotizacion(monkeypatch, emision, vencimiento, estado, renovable):
    c = Cotizacion(str(uuid4()), '<img onerror=alert(1)>', 3, 'FICTICIO',
        Vigencia(AHORA+timedelta(days=emision), AHORA+timedelta(days=vencimiento)),
        [Partida(1, SKU('FER-API-DEMO'), '2.5', Dinero('120.00'))], 'Contado')
    original = deepcopy(datos(c))
    reader = PostgresCotizacionesReader('no-se-conecta')
    monkeypatch.setattr(reader, '_leer', lambda sql, params: [(original,)])
    row = reader.listar_actuales(AHORA)[0]
    assert row['estado'] == estado and row['renovable'] is renovable
    assert row['partidas'][0]['cantidad'] == '2.5'
    assert row['partidas'][0]['precio_unitario'] == '120.00'
    assert original == datos(c)


@pytest.fixture
def conexion():
    import os
    url = os.environ.get('TEST_DATABASE_URL')
    if not url: pytest.skip('La vista de cotizaciones requiere PostgreSQL para esta comprobación')
    return url


def test_seleccionar_por_folio_renovar_y_recargar_conserva_historial(conexion):
    c, entrada, ruta = preparar(conexion)
    antes = versiones(conexion, c.id)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        row = next(q for q in client.get('/cliente/cotizaciones').json()['cotizaciones'] if q['id'] == c.id)
        assert row['folio'] == c.folio and row['renovable'] and row['version'] == 1
        assert client.post(ruta, json=entrada).status_code == 201
        rows = [q for q in client.get('/cliente/cotizaciones').json()['cotizaciones'] if q['id'] == c.id]
        assert len(rows) == 1 and rows[0]['version'] == 2
        assert rows[0]['estado'] == 'Vigente' and not rows[0]['renovable']
        assert datetime.fromisoformat(rows[0]['vencimiento'].replace('Z', '+00:00')) == AHORA+timedelta(days=7)
        assert rows[0]['partidas'][0]['precio_unitario'] == '120.00'
    guardadas = versiones(conexion, c.id)
    assert len(guardadas) == 2 and guardadas[0] == antes[0]
    with PostgresUnitOfWork(conexion) as uow:
        assert uow.conn.execute('SELECT count(*) FROM ferremax_u3.pedido WHERE cotizacion_id=%s::uuid', (c.id,)).fetchone() == (0,)


def test_demo_de_cliente_no_reinicia_cotizacion_renovada(conexion):
    cargar_cliente_demo(conexion, AHORA)
    ruta = f'/cotizaciones/{CLIENTE_DEMO_ID}/versiones/1/revalidar'
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        assert client.post(ruta, json=solicitud()).status_code == 201
    antes = versiones(conexion, CLIENTE_DEMO_ID)
    cargar_cliente_demo(conexion, AHORA+timedelta(days=10))
    assert versiones(conexion, CLIENTE_DEMO_ID) == antes

@pytest.mark.parametrize('ruta,palabra', [('/cliente/catalogo','productos'),('/cliente/pedidos','pedidos')])
def test_catalogos_no_exponen_error_tecnico_sin_configuracion(monkeypatch, ruta, palabra):
    for name in ('DATABASE_URL', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app()) as client:
        response=client.get(ruta)
        assert response.status_code == 503
        assert palabra in response.json()['mensaje']
        assert client.get('/cliente/atencion.js').status_code == 200


def test_catalogos_reales_y_estados_de_pedidos(conexion):
    c, entrada, ruta = preparar(conexion)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        catalogo=client.get('/cliente/catalogo')
        assert catalogo.headers['cache-control']=='no-store'
        assert c.partidas[0].sku.valor in catalogo.json()['productos']
        assert 'S1' in catalogo.json()['ubicaciones']
        assert client.post(ruta,json=entrada).status_code==201
        pedido=client.post(ruta.replace('/1/revalidar','/2/convertir'),json={'aceptada':True}).json()
        pid=pedido['pedido_id']
        def leer():
            response=client.get('/cliente/pedidos')
            assert response.headers['cache-control']=='no-store'
            return next(p for p in response.json()['pedidos'] if p['id']==pid)
        assert leer()['estado']=='Pendiente'
        assert leer()['referencia'].startswith('PED-')
        assert leer()['total']=='240.00'
        pago={'referencia_pago':'PAGO-UI','pago_autorizado':False,'ubicacion_id':'S1'}
        assert client.post(f'/pedidos/{pid}/confirmar',json=pago).status_code==409
        assert leer()['estado']=='Pendiente'
        assert client.post(f'/pedidos/{pid}/confirmar',json={**pago,'pago_autorizado':True}).status_code==200
        assert leer()['estado']=='Confirmado'
        assert client.post(f'/pedidos/{pid}/cancelar',json={'motivo':'Solicitud del cliente'}).status_code==200
        assert leer()['estado']=='Cancelado'
        assert client.get(f'/pedidos/{pid}').json()['estado']=='Cancelado'


def test_referencias_de_pantalla_distinguen_prefijos_coincidentes(monkeypatch):
    from ferremax.infrastructure.atencion_reader import PostgresAtencionReader
    c=Cotizacion(str(uuid4()),'COT-REFERENCIAS',1,'FICTICIO',
        Vigencia(AHORA-timedelta(days=1),AHORA+timedelta(days=1)),
        [Partida(1,SKU('DEMO'),1,Dinero('10.00'))],'Contado')
    filas=[]
    for pid in ('aaaaaaaa-1111-4111-8111-111111111111','aaaaaaaa-2222-4222-8222-222222222222'):
        p=c.convertir(AHORA,True);p.id=pid;filas.append((datos(p),))
    reader=PostgresAtencionReader('no-se-conecta')
    monkeypatch.setattr(reader,'_leer',lambda sql, params:filas)
    pedidos=reader.pedidos()
    assert len({p['referencia'] for p in pedidos})==2
    assert all(len(p['referencia'])==16 for p in pedidos)
    monkeypatch.setattr(reader,'_leer',lambda sql, params:[])
    assert reader.pedidos()==[]
    assert reader.catalogo()=={'productos':[],'ubicaciones':[]}

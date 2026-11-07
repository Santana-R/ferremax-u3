"""Swagger presenta mensajes sin cambiar el contrato consumido por aplicaciones."""
from fastapi.testclient import TestClient
import pytest
from ferremax.api.main import create_app
from ferremax.api import schemas
from ferremax.api.swagger_claro import EJEMPLOS

@pytest.mark.parametrize('nombre,ejemplo',list(EJEMPLOS.items()))
def test_ejemplos_son_validos_para_el_contrato_real(nombre,ejemplo):
    assert getattr(schemas,nombre).model_validate(ejemplo)


def test_sigue_siendo_swagger_y_la_pantalla_independiente_ya_no_se_sirve():
    with TestClient(create_app()) as client:
        page=client.get('/docs')
        assert page.status_code==200
        assert 'SwaggerUIBundle' in page.text and 'FerreMaxPresentacion' in page.text
        assert 'Mostrar detalles técnicos' in page.text
        assert '5.34.1' in page.text
        assert client.get('/').url.path=='/docs'
        assert client.get('/cliente').url.path=='/docs'
        assert client.get('/cliente/acciones.js').status_code==404
        assert client.get('/cliente/cotizaciones').status_code==404
        assert client.get('/docs/presentacion.js').status_code==200
        spec=client.get('/openapi.json').json()
        assert len(spec['paths'])==6
        assert spec['paths']['/cotizaciones/{cotizacion_id}/versiones/{version}/revalidar']['post']['summary']=='Renovar cotización vencida'
        assert 'pedido_id' in spec['components']['schemas']['PedidoCreadoRespuesta']['required']
        assert spec==client.get('/openapi.json').json()

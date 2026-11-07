"""Presentación sencilla en Swagger; el contrato y las respuestas HTTP se conservan."""
from pathlib import Path
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse

VERSION_SWAGGER = '5.34.1'
ID = '11111111-1111-4111-8111-111111111111'
PID = '22222222-2222-4222-8222-222222222222'
EJEMPLOS = {
 'InventarioRespuesta': {'mensaje':'Disponibilidad del producto consultada.', 'sku':'FER-API-DEMO','encontrado':True,'ubicaciones':[{'ubicacion_id':'S1','existencia_fisica':'10','comprometida':'7','en_transito':'5','disponible':'3'}]},
 'CotizacionRevalidadaRespuesta': {'mensaje':'Se renovó la cotización y se conservó la anterior en el historial.','cotizacion_id':ID,'version_anterior':1,'folio':'COT-API-DEMO','version':2,'estado':'Vigente'},
 'PedidoCreadoRespuesta': {'mensaje':'Pedido creado. Sigue pendiente de confirmación; todavía no se han reservado productos.','pedido_id':PID,'estado':'Pendiente','cotizacion_id':ID,'cotizacion_folio':'COT-API-DEMO','cotizacion_version':2,'total':'240.00','moneda':'MXN','disponibilidad_consultada':[{'sku':'FER-API-DEMO','solicitada':'2','disponible':'10'}]},
 'PedidoConfirmadoRespuesta': {'mensaje':'El pedido se confirmó y sus productos quedaron reservados.','pedido_id':PID,'estado':'Confirmado','referencia_pago':'PAGO-DEMO-001','ubicacion_id':'S1'},
 'PedidoCanceladoRespuesta': {'mensaje':'El pedido se canceló y sus productos reservados volvieron a estar disponibles.','pedido_id':PID,'estado':'Cancelado'},
 'PedidoConsultaRespuesta': {'mensaje':'Pedido consultado.','pedido_id':PID,'estado':'Pendiente','cotizacion_folio':'COT-API-DEMO','cotizacion_version':2,'total':'240.00','moneda':'MXN'},
}


def configurar_swagger(api):
    def especificacion():
        if api.openapi_schema is None:
            doc = get_openapi(title=api.title,version=api.version,description=api.description,routes=api.routes)
            for path in doc['paths'].values():
                for op in path.values():
                    for code, response in op.get('responses',{}).items():
                        content = response.get('content',{}).get('application/json')
                        if not content: continue
                        ref = content.get('schema',{}).get('$ref','').split('/')[-1]
                        if ref in EJEMPLOS: content['example'] = EJEMPLOS[ref]
                        elif ref == 'MensajeError':
                            content['example'] = {'mensaje': {
                                '400':'Escribe el código del producto.',
                                '404':'No encontramos lo que buscas. Revisa los datos e inténtalo de nuevo.',
                                '409':'No se puede realizar esta operación en el estado actual. Revisa la cotización o el pedido.',
                                '422':'Revisa los datos proporcionados e inténtalo de nuevo.',
                                '503':'El servicio no está disponible por el momento. Inténtalo más tarde.',
                            }.get(code,'No pudimos completar la operación. Revisa los datos.')}
            api.openapi_schema=doc
        return api.openapi_schema
    api.openapi=especificacion

    @api.get('/',include_in_schema=False)
    @api.get('/cliente',include_in_schema=False)
    def inicio():
        return RedirectResponse('/docs')

    @api.get('/docs/presentacion.js',include_in_schema=False)
    def presentacion():
        return FileResponse(Path(__file__).with_name('swagger_claro.js'),media_type='text/javascript',headers={'Cache-Control':'no-store'})

    @api.get('/docs',include_in_schema=False)
    def documentacion():
        html=get_swagger_ui_html(openapi_url='/openapi.json',title='FerreMax · Swagger',
            swagger_js_url=f'https://cdn.jsdelivr.net/npm/swagger-ui-dist@{VERSION_SWAGGER}/swagger-ui-bundle.js',
            swagger_css_url=f'https://cdn.jsdelivr.net/npm/swagger-ui-dist@{VERSION_SWAGGER}/swagger-ui.css',
            swagger_ui_parameters={'defaultModelsExpandDepth':-1,'displayOperationId':False,'validatorUrl':None}).body.decode()
        style='''<style>
body:not(.detalles-tecnicos) .opblock-summary-path,body:not(.detalles-tecnicos) .opblock-summary-method,
body:not(.detalles-tecnicos) .curl-command,body:not(.detalles-tecnicos) .request-url,
body:not(.detalles-tecnicos) .live-responses-table .response-col_description>div:has(.headerline){display:none!important}
.swagger-ui .opblock .opblock-summary-description{font-size:16px;font-weight:600;flex:1}
.fm-opciones{padding-top:18px!important;padding-bottom:8px!important}.fm-opciones label{display:flex;gap:8px;align-items:center}.fm-opciones p{font-size:13px;color:#555}
</style>'''
        opciones='''<div class="swagger-ui"><div class="wrapper fm-opciones"><label><input id="detalles" type="checkbox">Mostrar detalles técnicos</label><p>Vista sencilla: se presenta el mensaje de cada respuesta. Activa los detalles para consultar las rutas y los datos completos de la API.</p></div></div>'''
        html=html.replace('</head>',style+'</head>').replace('<div id="swagger-ui">',opciones+'<div id="swagger-ui">')
        html=html.replace('    <script>','    <script src="/docs/presentacion.js"></script>\n    <script>')
        html=html.replace('SwaggerUIBundle({','SwaggerUIBundle({\n        plugins: [window.FerreMaxPresentacion],')
        html=html.replace('</body>','''<script>
document.getElementById('detalles').addEventListener('change',function(){document.body.classList.toggle('detalles-tecnicos',this.checked);document.dispatchEvent(new Event('ferremax:detalles'));});
</script></body>''')
        return HTMLResponse(html,headers={'Cache-Control':'no-store'})

from fastapi.responses import JSONResponse


def error_cliente(mensaje, estado, sku=None, cotizacion_id=None, pedido_id=None):
    contenido = {"mensaje": mensaje}
    if sku is not None:
        contenido["sku"] = sku
    if cotizacion_id is not None:
        contenido["cotizacion_id"] = str(cotizacion_id)
    if pedido_id is not None:
        contenido["pedido_id"] = str(pedido_id)
    return JSONResponse(status_code=estado, content=contenido)

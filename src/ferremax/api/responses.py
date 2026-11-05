from fastapi.responses import JSONResponse


def error_cliente(mensaje, estado, sku=None, cotizacion_id=None):
    contenido = {"mensaje": mensaje}
    if sku is not None:
        contenido["sku"] = sku
    if cotizacion_id is not None:
        contenido["cotizacion_id"] = str(cotizacion_id)
    return JSONResponse(status_code=estado, content=contenido)

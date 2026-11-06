# language: es
# Contrato de aceptación del análisis. No son step definitions ni pruebas BDD ejecutadas.
Característica: Procesos de FerreMax conservados e integrados al PIA
  El negocio controla cotizaciones, pedidos, inventario y sus procesos relacionados.
  El estado de cada criterio se conserva en USER_STORIES.md y trazabilidad_analisis.csv.

  @US01 @AC_US01_01 @implementado
  Escenario: AC-US01-01 - Consulta global
    Dado un SKU con inventario registrado por ubicación
    Cuando el vendedor consulta su disponibilidad
    Entonces se muestran existencia física, comprometida, en tránsito y disponible de cada ubicación registrada

  @US01 @AC_US01_02 @implementado
  Escenario: AC-US01-02 - SKU inexistente
    Dado un SKU que no tiene registros en el inventario consultable
    Cuando el vendedor consulta su disponibilidad
    Entonces se informa que no fue encontrado y no se inventan existencias

  @US02 @AC_US02_01 @implementado
  Escenario: AC-US02-01 - Cálculo de disponible
    Dado un SKU con 10 unidades físicas y 7 comprometidas en una ubicación
    Cuando se consulta esa ubicación
    Entonces el disponible mostrado es 3 unidades

  @US02 @AC_US02_02 @implementado
  Escenario: AC-US02-02 - El tránsito no es vendible
    Dado un SKU con 0 unidades disponibles y 5 en tránsito
    Cuando se consulta su disponibilidad
    Entonces el disponible permanece en 0 y las 5 unidades se muestran como tránsito

  @US03 @AC_US03_01 @disenado
  Escenario: AC-US03-01 - Emisión inicial
    Dado un cliente y partidas válidas con precios y condiciones
    Cuando el vendedor emite una cotización
    Entonces se asignan folio, versión, emisión, vencimiento, totales y estado vigente, se conserva la disponibilidad consultada y no se reserva inventario

  @US04 @AC_US04_01 @implementado
  Escenario: AC-US04-01 - Conversión de versión vencida
    Dado una versión de cotización cuyo vencimiento ya pasó
    Cuando el vendedor intenta convertirla en pedido
    Entonces se rechaza la conversión con indicación de revalidación, sin crear pedido ni reserva

  @US04 @AC_US04_02 @implementado
  Escenario: AC-US04-02 - Nueva versión con historial
    Dado una cotización vencida y nuevos precios, condiciones y vigencia válidos
    Cuando el vendedor solicita revalidarla
    Entonces se guarda una nueva versión vigente conservando intacta la anterior y sin crear pedido ni reserva

  @US04 @AC_US04_03 @implementado
  Escenario: AC-US04-03 - Instante exacto del vencimiento
    Dado una cotización cuyo vencimiento es el instante actual
    Cuando se intenta convertir esa versión
    Entonces se rechaza por falta de vigencia sin alterar los datos

  @US04 @AC_US04_04 @implementado
  Escenario: AC-US04-04 - Revalidaciones simultáneas
    Dado dos solicitudes concurrentes de revalidación para la misma versión vencida
    Cuando ambas intentan guardar la versión siguiente
    Entonces solo se conserva una versión nueva y la otra solicitud recibe un rechazo sin duplicar efectos

  @US05 @AC_US05_01 @implementado
  Escenario: AC-US05-01 - Conversión válida
    Dado una versión vigente de cotización que el cliente acepta
    Cuando el vendedor solicita convertirla
    Entonces se crea un pedido Pendiente ligado al folio y versión, conserva partidas y total, consulta disponibilidad y no reserva inventario

  @US05 @AC_US05_02 @implementado
  Escenario: AC-US05-02 - Aceptación obligatoria
    Dado una versión vigente que el cliente no ha aceptado
    Cuando el vendedor solicita convertirla
    Entonces se rechaza la conversión sin crear pedido ni reserva

  @US05 @AC_US05_03 @implementado
  Escenario: AC-US05-03 - Pendiente sin disponibilidad
    Dado una cotización vigente y aceptada con un producto registrado pero sin unidades disponibles
    Cuando se convierte la cotización
    Entonces se crea un pedido Pendiente y se informa la disponibilidad en 0 sin crear reserva

  @US06 @AC_US06_01 @simulado
  Escenario: AC-US06-01 - Pago autorizado y stock suficiente
    Dado un pedido Pendiente, referencia de pago autorizado y disponibilidad suficiente
    Cuando Caja confirma el pedido desde una ubicación
    Entonces se guardan Confirmado, su reserva, auditoría y evento en una sola transacción

  @US06 @AC_US06_02 @simulado
  Escenario: AC-US06-02 - Pago rechazado
    Dado un pedido Pendiente y un pago no autorizado
    Cuando Caja intenta confirmarlo
    Entonces el pedido permanece Pendiente sin reserva ni evento de confirmación nuevo

  @US06 @AC_US06_03 @simulado
  Escenario: AC-US06-03 - Referencia obligatoria
    Dado un pedido Pendiente sin referencia de pago válida
    Cuando Caja intenta confirmarlo
    Entonces se rechaza la solicitud y se conserva el estado anterior

  @US07 @AC_US07_01 @disenado
  Escenario: AC-US07-01 - Crédito normal suficiente
    Dado un cliente empresarial activo, sin bloqueo y con crédito disponible suficiente en la misma moneda
    Cuando solicita comprar a crédito
    Entonces se autoriza la condición normal y se registra la evaluación

  @US07 @AC_US07_02 @parcial
  Escenario: AC-US07-02 - Cliente bloqueado
    Dado un cliente empresarial bloqueado
    Cuando se evalúa una solicitud de crédito
    Entonces se obtiene EnRevision y no se confirma automáticamente el pedido

  @US08 @AC_US08_01 @disenado
  Escenario: AC-US08-01 - Excepción autorizada
    Dado una solicitud de crédito en revisión
    Cuando el responsable autoriza una excepción e indica el motivo
    Entonces se registran decisión, responsable, fecha y condición autorizada

  @US08 @AC_US08_02 @disenado
  Escenario: AC-US08-02 - Excepción rechazada
    Dado una solicitud de crédito en revisión
    Cuando el responsable rechaza la excepción con motivo
    Entonces el pedido no se confirma y el vendedor recibe el motivo

  @US09 @AC_US09_01 @implementado
  Escenario: AC-US09-01 - Reserva atómica
    Dado un pedido Pendiente con pago autorizado y unidades suficientes
    Cuando se confirma el pedido
    Entonces la reserva propia y el estado Confirmado se guardan juntos y el disponible disminuye por lo reservado

  @US09 @AC_US09_02 @implementado
  Escenario: AC-US09-02 - Competencia por la última unidad
    Dado dos pedidos con autorización de pago compiten por la última unidad disponible
    Cuando ambos intentan confirmarse concurrentemente
    Entonces solo uno obtiene la reserva y el otro recibe rechazo por disponibilidad, permaneciendo Pendiente

  @US09 @AC_US09_03 @implementado
  Escenario: AC-US09-03 - Reserva exactamente igual al disponible
    Dado 3 unidades disponibles y un pedido de 3 unidades con pago autorizado
    Cuando se confirma ese pedido
    Entonces se reservan 3 unidades y el disponible queda en 0

  @US09 @AC_US09_04 @implementado
  Escenario: AC-US09-04 - Solicitud mayor que el disponible
    Dado 3 unidades disponibles y un pedido de 4 unidades con pago autorizado
    Cuando se intenta confirmar el pedido
    Entonces se rechaza y el pedido almacenado permanece Pendiente sin alterar reservas ni registrar un éxito

  @US09 @AC_US09_05 @implementado
  Escenario: AC-US09-05 - Fallo en la segunda partida
    Dado un pedido con dos productos y disponibilidad insuficiente en el segundo
    Cuando la confirmación intenta reservar ambas partidas
    Entonces se revierte la reserva del primer producto junto con estado, referencia de pago y efectos de éxito

  @US09 @AC_US09_06 @implementado
  Escenario: AC-US09-06 - Confirmación repetida
    Dado un pedido ya Confirmado con su reserva persistida
    Cuando se vuelve a solicitar su confirmación
    Entonces se rechaza sin duplicar reserva ni evento ni reemplazar la referencia original

  @US10 @AC_US10_01 @implementado
  Escenario: AC-US10-01 - Cancelación libera solo lo propio
    Dado un pedido Confirmado, aún no surtido, con autorización y motivo, cuya reserva es de 2 unidades y comparte inventario con 7 unidades reservadas para otro pedido
    Cuando se cancela el pedido
    Entonces se liberan solo sus 2 unidades, se conservan las 7 ajenas y se guarda motivo, auditoría y evento

  @US10 @AC_US10_02 @disenado
  Escenario: AC-US10-02 - Reducción libera diferencia
    Dado un pedido Confirmado y aún no surtido con una partida reservada
    Cuando se autoriza reducir la cantidad de esa partida con motivo
    Entonces se libera solo la diferencia y se conserva el resto de la reserva y su trazabilidad

  @US10 @AC_US10_03 @implementado
  Escenario: AC-US10-03 - Rechazo después del surtido
    Dado un pedido Confirmado marcado como surtido
    Cuando se solicita cancelarlo con motivo
    Entonces se rechaza conservando estado, reservas y registros previos

  @US10 @AC_US10_04 @implementado
  Escenario: AC-US10-04 - Cancelación repetida
    Dado un pedido ya Cancelado y sin su reserva activa
    Cuando se solicita cancelarlo de nuevo
    Entonces se rechaza sin liberar cantidades adicionales ni duplicar el evento de cancelación

  @US10 @AC_US10_05 @implementado
  Escenario: AC-US10-05 - Liberación fallida revierte todo
    Dado un pedido con reserva de dos productos y una inconsistencia que impide liberar el segundo
    Cuando se intenta cancelar el pedido
    Entonces se revierte la primera liberación y se conservan estado y registros originales

  @US11 @AC_US11_01 @disenado
  Escenario: AC-US11-01 - Solicitud trazable
    Dado una sucursal sin unidades suficientes y otra ubicación con disponible
    Cuando el vendedor solicita una transferencia tras consultar primero almacén central y después otras sucursales
    Entonces se registra un folio con origen, destino, partidas, cantidades, pedido relacionado y estado Solicitado

  @US12 @AC_US12_01 @disenado
  Escenario: AC-US12-01 - Despacho autorizado
    Dado una transferencia autorizada y preparada
    Cuando almacén registra su salida
    Entonces la cantidad se registra en tránsito y se conservan responsable y fecha

  @US12 @AC_US12_02 @disenado
  Escenario: AC-US12-02 - Rechazo por faltante
    Dado una solicitud cuyo origen ya no tiene suficiente disponible
    Cuando almacén revisa la solicitud
    Entonces se rechaza con motivo y el pedido relacionado vuelve a evaluación

  @US13 @AC_US13_01 @disenado
  Escenario: AC-US13-01 - Recepción completa
    Dado una transferencia en tránsito con todas sus cantidades recibidas
    Cuando destino confirma la recepción
    Entonces disminuye tránsito, aumenta existencia física utilizable en destino y queda Recibida sin ocultar reservas ajenas

  @US13 @AC_US13_02 @disenado
  Escenario: AC-US13-02 - Diferencia de recepción
    Dado una transferencia cuya cantidad recibida difiere de la esperada
    Cuando destino registra lo efectivamente recibido
    Entonces queda una incidencia trazable y no se oculta la diferencia

  @US14 @AC_US14_01 @disenado
  Escenario: AC-US14-01 - Aceptación de parcial
    Dado un pedido con disponibilidad insuficiente
    Cuando el cliente acepta expresamente las cantidades surtibles
    Entonces se separan las cantidades surtibles y pendientes por partida y se conserva la aceptación

  @US14 @AC_US14_02 @disenado
  Escenario: AC-US14-02 - Rechazo de parcial
    Dado un pedido incompleto cuyo cliente no acepta el parcial
    Cuando se registra su decisión de esperar o cancelar
    Entonces se conserva la decisión y se libera únicamente lo que corresponda si hay una cancelación autorizada

  @US15 @AC_US15_01 @disenado
  Escenario: AC-US15-01 - Surtido correcto
    Dado un pedido Confirmado con reservas
    Cuando almacén prepara y verifica sus partidas
    Entonces se registran cantidades surtidas, faltantes, responsable y hora sin exceder lo reservado

  @US16 @AC_US16_01 @disenado
  Escenario: AC-US16-01 - Programación completa
    Dado un pedido surtido con entrega a domicilio y dirección validada
    Cuando se programa la entrega
    Entonces se asignan unidad, operador, ventana y estado Programado

  @US16 @AC_US16_02 @disenado
  Escenario: AC-US16-02 - Datos incompletos
    Dado una entrega sin dirección o contacto válido
    Cuando se intenta programar la salida
    Entonces se bloquea y se indican los datos faltantes

  @US17 @AC_US17_01 @disenado
  Escenario: AC-US17-01 - Entrega completada
    Dado una entrega en ruta realizada al destinatario
    Cuando el operador registra receptor, fecha, hora y evidencia
    Entonces la entrega y el pedido se cierran como entregados con su trazabilidad

  @US17 @AC_US17_02 @disenado
  Escenario: AC-US17-02 - Incidencia en ruta
    Dado una entrega que no pudo realizarse
    Cuando el operador registra motivo y evidencia
    Entonces la entrega queda con incidencia y el pedido no se cierra como entregado

  @US18 @AC_US18_01 @disenado
  Escenario: AC-US18-01 - Devolución elegible
    Dado un comprobante válido y un producto cuya categoría y condición cumplen la política configurada
    Cuando se autoriza la devolución
    Entonces se registran la decisión, el resultado financiero y el destino del inventario

  @US19 @AC_US19_01 @disenado
  Escenario: AC-US19-01 - Panel operativo
    Dado operaciones registradas en las cuatro ubicaciones del negocio
    Cuando el gerente consulta el panel con filtros de fecha y ubicación
    Entonces ve cotizaciones por vencer, bajo mínimo, transferencias, crédito en revisión, parciales y entregas pendientes

  @US20 @AC_US20_01 @disenado
  Escenario: AC-US20-01 - Consulta de bitácora protegida
    Dado una operación sensible modificada
    Cuando un auditor autorizado consulta su folio
    Entonces se muestran actor, fecha, hora, acción, valores anterior y nuevo y motivo, sin permitir que un usuario operativo altere la bitácora

  @US20 @AC_US20_02 @implementado
  Escenario: AC-US20-02 - Registro transaccional de cambio
    Dado un pedido Pendiente, pago autorizado y disponibilidad suficiente
    Cuando se confirma el pedido
    Entonces pedido, reserva, auditoría con actor y valores anterior/nuevo y evento se conservan en la misma transacción

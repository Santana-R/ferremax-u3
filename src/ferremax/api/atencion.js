"use strict";
let catalog = {productos:[],ubicaciones:[]}, orderRows = [], activeOrder = null;
let convertRows = [], mutationBusy = false, ordersFresh = false, uncertainCreate = false;
const friendly = {
  'Esta versión de la cotización no está vigente. Usa una versión vigente para crear el pedido.': 'Esta cotización ya no está vigente. Renueva sus precios y condiciones antes de crear el pedido.',
  'El cliente debe aceptar esta versión de la cotización antes de crear el pedido.': 'Confirma primero que el cliente acepta la cotización.',
};
function receipt(id, title, text, error=false) {
  const box=el(id); box.replaceChildren();
  const heading=document.createElement('h2'), paragraph=document.createElement('p');
  heading.textContent=title; paragraph.textContent=text; box.append(heading,paragraph);
  box.classList.toggle('error',error); box.hidden=false; box.focus();
}
async function api(path, body) {
  let response, data;
  try {
    response=await fetch(path,body===undefined ? {cache:'no-store'} : {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
    });
    data=await response.json();
  } catch {
    const error=new Error(body===undefined ? 'No pudimos consultar la información. Inténtalo de nuevo en unos momentos.' :
      'Se interrumpió la conexión y no podemos confirmar si se guardó. Actualiza y consulta el estado antes de volver a intentarlo.');
    error.uncertain=body!==undefined; throw error;
  }
  if (!response.ok) {
    const error=new Error(friendly[data.mensaje] || data.mensaje || 'No pudimos completar la operación. Revisa la información y vuelve a intentarlo.');
    error.status=response.status; throw error;
  }
  return data;
}
function optionList(select, items, title) {
  select.replaceChildren(new Option(title,''));
  for(const [value,label] of items)select.add(new Option(label,value));
  select.disabled=items.length===0;
}
function lockOrders() {
  el('confirm-submit').disabled=mutationBusy || !ordersFresh;
  el('cancel-submit').disabled=mutationBusy || !ordersFresh;
  el('order-select').disabled=mutationBusy || !ordersFresh || !orderRows.length;
  el('order-consult').disabled=mutationBusy || !activeOrder;
  el('orders-refresh').disabled=mutationBusy;
}
async function loadCatalog() {
  try {
    catalog=await api('/cliente/catalogo');
    optionList(el('product-select'),catalog.productos.map(p=>[p,p]),'Selecciona un producto');
    optionList(el('order-location'),catalog.ubicaciones.map(p=>[p,'Sucursal / almacén '+p]),'Selecciona una sucursal');
    el('inventory-submit').disabled=!catalog.productos.length;
    if(!catalog.productos.length)el('inventory-status').textContent='Todavía no hay productos registrados.';
  } catch(error) {el('inventory-status').textContent=error.message;}
}
function describeConvert() {
  const q=convertRows.find(q=>q.id===el('convert-select').value);
  el('accepted').checked=false;
  el('convert-submit').disabled=!q || q.estado!=='Vigente' || mutationBusy || uncertainCreate;
  el('accepted').disabled=!q || q.estado!=='Vigente' || mutationBusy || uncertainCreate;
  if(!q){el('convert-detail').textContent='Selecciona una cotización para revisar los productos y el importe.';return;}
  const totals=new Map();
  const lines=q.partidas.map(p=>{totals.set(p.moneda,(totals.get(p.moneda)||0)+Number(p.cantidad)*Number(p.precio_unitario));return p.cantidad+' unidades de '+p.sku+' a '+money(p.precio_unitario,p.moneda)+' por unidad';});
  el('convert-detail').textContent=lines.join('; ')+'. Total estimado: '+[...totals].map(([c,v])=>money(v,c)).join(' + ')+'. Condiciones: '+q.condiciones+'. '+
    (q.estado==='Vigente' ? 'Puedes utilizarla hasta el '+date(q.vencimiento)+'.' : q.estado==='Por emitir' ? 'Todavía no ha sido emitida.' : 'Esta cotización venció. Renuévala antes de crear el pedido.');
}
async function loadConvert() {
  el('convert-submit').disabled=true;el('convert-select').disabled=true;
  el('convert-status').textContent='Consultando cotizaciones…';
  try {
    convertRows=(await api('/cliente/cotizaciones')).cotizaciones;
    optionList(el('convert-select'),convertRows.map(q=>[q.id,q.folio+' · '+q.estado]),'Selecciona una cotización');
    el('convert-status').textContent=uncertainCreate ? 'Consulta tus pedidos antes de intentar crear otro; la solicitud anterior pudo guardarse.' : convertRows.length ? '' : 'Todavía no hay cotizaciones registradas.';
    describeConvert();
  }catch(error){el('convert-status').textContent=error.message;}
}
function showOrder(row) {
  activeOrder=row; el('order-detail').replaceChildren();
  el('confirm-form').hidden=!row || row.estado!=='Pendiente';
  el('cancel-form').hidden=!row || row.estado!=='Confirmado' || row.surtido;
  el('payment-ref').value='';el('payment-ok').value='false';el('cancel-reason').value='';el('cancel-ack').checked=false;
  if(row){
    for(const [label,value] of [['Pedido',row.referencia],['Estado',row.estado],['Cotización de origen',row.cotizacion_folio],['Importe',money(row.total,row.moneda)]]){
      const p=document.createElement('p'),strong=document.createElement('strong');strong.textContent=label+': ';p.append(strong,document.createTextNode(value));el('order-detail').append(p);
    }
    const note=document.createElement('p');note.className='notice';note.textContent=row.estado==='Pendiente' ? 'El pedido sigue pendiente. Confirma el pago y la disponibilidad para reservar sus productos.' : row.estado==='Cancelado' ? 'El pedido está cancelado. No puede confirmarse ni cancelarse otra vez.' : row.surtido ? 'El pedido ya fue surtido y no admite cancelación.' : 'El pedido está confirmado y tiene productos reservados. Puedes cancelarlo mientras no se haya surtido.';el('order-detail').append(note);
    const products=document.createElement('p');products.textContent='Productos: '+row.partidas.map(p=>p.cantidad+' unidades de '+p.sku).join('; ')+'.';el('order-detail').append(products);
  }
  lockOrders();
}
async function loadOrders(preferred) {
  ordersFresh=false;lockOrders();el('orders-status').textContent='Consultando pedidos…';
  try {
    orderRows=(await api('/cliente/pedidos')).pedidos;ordersFresh=true;uncertainCreate=false;
    optionList(el('order-select'),orderRows.map(p=>[p.id,p.referencia+' · '+p.cotizacion_folio+' · '+p.estado]),'Selecciona un pedido');
    if(preferred && orderRows.some(p=>p.id===preferred))el('order-select').value=preferred;
    el('orders-status').textContent=orderRows.length ? 'Selecciona un pedido para consultar su estado.' : 'Todavía no hay pedidos. Crea uno desde una cotización vigente.';
    showOrder(orderRows.find(p=>p.id===el('order-select').value)||null);return true;
  }catch(error){el('orders-status').textContent=error.message;lockOrders();return false;}
}
async function showView(name, preferred) {
  if(saving || mutationBusy)return;
  for(const section of document.querySelectorAll('.view'))section.hidden=section.id!=='view-'+name;
  for(const tab of document.querySelectorAll('.tab')){if(tab.dataset.view===name)tab.setAttribute('aria-current','page');else tab.removeAttribute('aria-current');}
  if(name==='inventory')await loadCatalog();
  if(name==='convert')await loadConvert();
  if(name==='orders'){await loadCatalog();await loadOrders(preferred);}
  if(name==='renew')await load(selected && selected.id);
}
for(const tab of document.querySelectorAll('.tab'))tab.addEventListener('click',()=>showView(tab.dataset.view));
document.querySelector('[data-view=renew]').setAttribute('aria-current','page');
el('convert-select').addEventListener('change',describeConvert);
el('order-select').addEventListener('change',()=>{el('order-result').hidden=true;showOrder(orderRows.find(p=>p.id===el('order-select').value)||null);});
el('orders-refresh').addEventListener('click',()=>loadOrders(activeOrder && activeOrder.id));
el('inventory-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!event.target.reportValidity())return;
  el('inventory-submit').disabled=true;el('inventory-status').textContent='Consultando disponibilidad…';el('inventory-result').replaceChildren();
  try{
    const result=await api('/inventario/'+encodeURIComponent(el('product-select').value));
    for(const u of result.ubicaciones){
      const card=document.createElement('section');card.className='stock-card';
      const title=document.createElement('h2');title.textContent='Sucursal / almacén '+u.ubicacion_id;
      const available=document.createElement('strong');available.textContent=u.disponible+' unidades disponibles';
      const detail=document.createElement('p');detail.textContent=u.existencia_fisica+' unidades en existencia; '+u.comprometida+' reservadas para pedidos; '+u.en_transito+' en traslado.';
      card.append(title,available,detail);el('inventory-result').append(card);
    }
    el('inventory-status').textContent='Disponibilidad actual de '+result.sku+'. La consulta no reserva productos.';
  }catch(error){el('inventory-status').textContent=error.message;}finally{el('inventory-submit').disabled=false;}
});
el('convert-form').addEventListener('submit',async event=>{
  event.preventDefault();const q=convertRows.find(q=>q.id===el('convert-select').value);
  if(mutationBusy || uncertainCreate || !q || q.estado!=='Vigente' || !event.target.reportValidity())return;
  mutationBusy=true;el('convert-submit').disabled=true;el('convert-select').disabled=true;el('convert-status').textContent='Creando el pedido…';
  let created;
  try{created=await api(`/cotizaciones/${encodeURIComponent(q.id)}/versiones/${q.version}/convertir`,{aceptada:el('accepted').checked});
    receipt('convert-result','Pedido creado','El pedido de la cotización '+created.cotizacion_folio+' se creó por '+money(created.total,created.moneda)+'. Sigue pendiente; todavía no se han reservado productos. Consúltalo en Pedidos.');
  }catch(error){uncertainCreate=!!error.uncertain;receipt('convert-result','No pudimos completar la solicitud',error.message,true);}
  finally{mutationBusy=false;el('convert-status').textContent='';el('accepted').checked=false;el('convert-select').disabled=false;el('convert-submit').disabled=!!created || uncertainCreate;}
  if(created){await showView('orders',created.pedido_id);receipt('order-result','Pedido creado','Tu pedido se creó por '+money(created.total,created.moneda)+'. Sigue pendiente: registra el pago y la sucursal para confirmarlo.');}
});
el('order-consult').addEventListener('click',async()=>{
  if(!activeOrder || mutationBusy)return;const id=activeOrder.id;
  el('order-consult').disabled=true;
  try{const result=await api('/pedidos/'+encodeURIComponent(id));
    // El estado mostrado se confirma con la consulta de negocio, no solo con el catálogo.
    const loaded=await loadOrders(id);
    if(loaded)receipt('order-result','Pedido consultado','El pedido de la cotización '+result.cotizacion_folio+' está '+result.estado.toLowerCase()+'. Su importe es '+money(result.total,result.moneda)+'.');
  }catch(error){ordersFresh=false;lockOrders();receipt('order-result','No pudimos consultar el pedido',error.message,true);}
});
async function mutateOrder(action, body, title, text) {
  if(mutationBusy || !ordersFresh || !activeOrder)return;
  const id=activeOrder.id;mutationBusy=true;lockOrders();
  el('orders-status').textContent='Guardando la operación…';
  try{
    await api('/pedidos/'+encodeURIComponent(id)+'/'+action,body);
    const loaded=await loadOrders(id);
    receipt('order-result',title,text+(loaded ? '' : ' Actualiza los pedidos para consultar su estado.'));
  }catch(error){
    if(error.uncertain)ordersFresh=false;
    if(error.status===409 || error.status===404){
      const paymentReference=el('payment-ref').value, paymentStatus=el('payment-ok').value;
      await loadOrders(id);
      if(activeOrder && activeOrder.id===id && activeOrder.estado==='Pendiente'){
        el('payment-ref').value=paymentReference;el('payment-ok').value=paymentStatus;
      }
    }
    receipt('order-result','No se pudo completar la operación',error.message,true);
  }finally{mutationBusy=false;el('orders-status').textContent='';lockOrders();}
}
el('confirm-form').addEventListener('submit',event=>{
  event.preventDefault();if(!event.target.reportValidity())return;
  if(!el('payment-ref').value.trim()){receipt('order-result','Revisa el pago','Escribe la referencia del pago.',true);return;}
  mutateOrder('confirmar',{referencia_pago:el('payment-ref').value.trim(),pago_autorizado:el('payment-ok').value==='true',ubicacion_id:el('order-location').value},'Pedido confirmado','El pedido se confirmó y sus productos quedaron reservados en la sucursal seleccionada.');
});
el('cancel-form').addEventListener('submit',event=>{
  event.preventDefault();if(!event.target.reportValidity())return;
  if(!el('cancel-reason').value.trim()){receipt('order-result','Revisa la cancelación','Escribe el motivo de la cancelación.',true);return;}
  mutateOrder('cancelar',{motivo:el('cancel-reason').value.trim()},'Pedido cancelado','El pedido se canceló y sus productos reservados volvieron a estar disponibles.');
});

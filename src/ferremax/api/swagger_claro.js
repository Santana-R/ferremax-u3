/* Solo modifica el componente visual de Swagger; no intercepta respuestas HTTP. */
(function(){
 function mensaje(data){
   if(Array.isArray(data.ubicaciones)){
     return 'Producto '+data.sku+'. '+data.ubicaciones.map(u=>'En '+u.ubicacion_id+' hay '+u.disponible+' unidades disponibles; '+u.comprometida+' reservadas y '+u.en_transito+' en traslado.').join(' ');
   }
   if(data.cotizacion_folio && data.total!==undefined){
     const importe=new Intl.NumberFormat('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(data.total));
     return data.estado==='Pendiente' && Array.isArray(data.disponibilidad_consultada)
       ? 'El pedido de la cotización '+data.cotizacion_folio+' se creó por '+importe+' '+data.moneda+'. Sigue pendiente; todavía no se han reservado productos.'
       : 'El pedido de la cotización '+data.cotizacion_folio+' está '+data.estado.toLowerCase()+'. Su importe es '+importe+' '+data.moneda+'.';
   }
   return data.mensaje;
 }
 window.FerreMaxPresentacion=function(system){
   const React=system.React;
   return {wrapComponents:{HighlightCode:(Original)=>function(props){
     const [tecnico,setTecnico]=React.useState(document.body.classList.contains('detalles-tecnicos'));
     React.useEffect(()=>{
       const actualizar=()=>setTecnico(document.body.classList.contains('detalles-tecnicos'));
       document.addEventListener('ferremax:detalles',actualizar);
       return ()=>document.removeEventListener('ferremax:detalles',actualizar);
     },[]);
     let contenido=props.children;
     if(!tecnico && typeof contenido==='string'){
       try{const data=JSON.parse(contenido);if(data && typeof data.mensaje==='string')contenido=JSON.stringify({mensaje:mensaje(data)},null,2);}catch{/* El resto de código de Swagger permanece igual. */}
     }
     return React.createElement(Original,props,contenido);
   }}};
 };
})();

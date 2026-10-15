"""Build the academic PDF deliverables from versioned sources.

Requires reportlab and PyMuPDF (only for artifact generation, not the demo).
"""
from pathlib import Path
import json, re, html, shutil, csv, io, math
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, LongTable, TableStyle, Preformatted, KeepTogether
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs'; OUT.mkdir(exist_ok=True)
DG=ROOT/'diagrams'; DG.mkdir(exist_ok=True)
DOC=ROOT/'docs'; QA=ROOT.parent/'qa'; QA.mkdir(exist_ok=True)
ASSETS=ROOT/'assets'
for n,f in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(n,'/usr/share/fonts/truetype/dejavu/'+f))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
NAVY=colors.HexColor('#123653'); TEAL=colors.HexColor('#007e86'); PALE=colors.HexColor('#edf5f6'); GRAY=colors.HexColor('#516273')
W,H=595.276,841.89; WIDTH=W-100
S=getSampleStyleSheet()
S.add(ParagraphStyle(name='Text',fontName='Body',fontSize=9.5,leading=14,spaceAfter=7,textColor=NAVY))
S.add(ParagraphStyle(name='TitleX',fontName='Bold',fontSize=23,leading=29,textColor=NAVY,spaceAfter=18))
S.add(ParagraphStyle(name='H1X',fontName='Bold',fontSize=15,leading=19,spaceBefore=14,spaceAfter=10,textColor=NAVY,keepWithNext=True))
S.add(ParagraphStyle(name='H2X',fontName='Bold',fontSize=11,leading=15,spaceBefore=9,spaceAfter=7,textColor=TEAL,keepWithNext=True))
S.add(ParagraphStyle(name='CellX',fontName='Body',fontSize=7.8,leading=11,textColor=NAVY))
S.add(ParagraphStyle(name='CellHead',fontName='Bold',fontSize=8,leading=11,textColor=colors.white))
S.add(ParagraphStyle(name='SmallX',fontName='Body',fontSize=8,leading=11,textColor=GRAY,spaceAfter=6))
S.add(ParagraphStyle(name='CodeX',fontName='Mono',fontSize=7.2,leading=10,textColor=NAVY,backColor=PALE,borderPadding=7,spaceAfter=8))

def plain(t):
    t=re.sub(r'<mention-date start="([^"]+)"[^>]*/>',r'\1',t)
    t=re.sub(r'<[^>]+>','',t)
    t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1 (\2)',t)
    return t.replace('**','').replace('`','').replace('\u2011','-').replace('–','-').replace('—','-')

def inline(t):
    t=re.sub(r'<mention-date start="([^"]+)"[^>]*/>',r'\1',t)
    t=re.sub(r'<[^>]+>','',t)
    t=t.replace('–','-').replace('—','-').replace('\u2011','-')
    t=html.escape(t)
    t=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',t)
    t=re.sub(r'`([^`]+)`',r'<font name="Mono">\1</font>',t)
    t=re.sub(r'\[([^\]]+)\]\((https?[^)]+)\)',r'<link href="\2" color="#007e86">\1</link> (\2)',t)
    return t

def table(xml):
    rows=[]
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',xml,re.S):
        rows.append([plain(x).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)])
    if not rows:return []
    n=len(rows[0]); weights={2:[.29,.71],3:[.2,.4,.4],4:[.15,.28,.28,.29],5:[.15,.23,.23,.25,.14],6:[.12,.15,.18,.19,.18,.18]}.get(n,[1/n]*n)
    widths=[WIDTH*x/sum(weights) for x in weights]
    data=[[Paragraph(inline(v),S['CellHead'] if i==0 else S['CellX']) for v in row] for i,row in enumerate(rows)]
    t=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.4,NAVY),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d7e0e7'))]))
    return [t,Spacer(1,9)]

def markdown(t):
    blocks=[]; chunks=re.split(r'(<table\b.*?</table>|```.*?```)',t,flags=re.S)
    for c in chunks:
        if c.startswith('<table'):blocks.extend(table(c));continue
        if c.startswith('```'):
            lines=c.splitlines()[1:-1]
            code=[]
            for ln in lines:
                # Preserve commands while wrapping long lines at whitespace.
                import textwrap
                for part in textwrap.wrap(ln,94,replace_whitespace=False,drop_whitespace=False) or [' ']:code.append(Preformatted(part,S['CodeX']))
            if len(code)<=20:
                if blocks and isinstance(blocks[-1],Paragraph) and blocks[-1].style.name=='H2X':code.insert(0,blocks.pop())
                blocks.append(KeepTogether(code))
            else:blocks.extend(code)
            continue
        for ln in c.splitlines():
            ln=ln.strip()
            if not ln or ln.startswith('<embed') or ln.startswith('<file'):continue
            if ln.startswith('### '):blocks.append(Paragraph(inline(ln[4:]),S['H2X']))
            elif ln.startswith('## '):blocks.append(Paragraph(inline(ln[3:]),S['H1X']))
            elif ln.startswith('# '):blocks.append(Paragraph(inline(ln[2:]),S['H1X']))
            elif ln.startswith(('- ','- [ ] ','- [x] ')):
                ln=re.sub(r'^- \[[ x]\] ','',ln)
                blocks.append(Paragraph('• '+inline(ln.removeprefix('- ')),S['Text']))
            else:blocks.append(Paragraph(inline(ln),S['Text']))
    return blocks

def footer(c,d):
    c.saveState(); c.setStrokeColor(TEAL);c.setLineWidth(.7);c.line(50,42,W-50,42)
    c.setFont('Body',7);c.setFillColor(GRAY);c.drawString(50,29,'FerreMax | Equipo 17 | CLNEG - Unidad 3');c.drawRightString(W-50,29,str(d.page))
    if d.page>1:
        c.setFont('Body',7);c.drawString(50,H-30,'FIME · Arquitectura del sistema · Octubre 2026')
    c.restoreState()

def cover(subtitle):
    return [Spacer(1,4),Image(str(ASSETS/'logo_11.jpeg'),width=143,height=68),Spacer(1,17),Paragraph('UNIVERSIDAD AUTÓNOMA DE NUEVO LEÓN',ParagraphStyle('Univ',parent=S['H2X'],alignment=1,fontSize=11)),Paragraph('Facultad de Ingeniería Mecánica y Eléctrica',ParagraphStyle('Fac',parent=S['Text'],alignment=1)),Spacer(1,20),Image(str(ASSETS/'logo_12.png'),width=112,height=63),Spacer(1,28),Paragraph('FerreMax',ParagraphStyle('CoverTitle',parent=S['TitleX'],alignment=1,fontSize=34,leading=40)),Paragraph(subtitle,ParagraphStyle('CoverSub',parent=S['H1X'],alignment=1,fontSize=18,leading=24)),Spacer(1,23),Paragraph('Componentes de lógica de negocio<br/>Unidad 3 · Diseño arquitectural del sistema con IA',ParagraphStyle('Course',parent=S['Text'],alignment=1)),Spacer(1,22),Paragraph('Profesor: Miguel Ángel Gómez Marroquín',ParagraphStyle('Prof',parent=S['Text'],alignment=1)),Spacer(1,15),Paragraph('Equipo 17<br/>Roberto Santana Trujillo · 2227084<br/>Isaías Leonardo Salazar Torres · 2227016',ParagraphStyle('Names',parent=S['Text'],alignment=1)),Spacer(1,20),Paragraph('Revisión: 16 de octubre de 2026<br/>Propuesta académica para revisión del equipo',ParagraphStyle('Date',parent=S['SmallX'],alignment=1)),PageBreak()]

def doc(path,story):
    SimpleDocTemplate(str(path),pagesize=(W,H),rightMargin=50,leftMargin=50,topMargin=52,bottomMargin=56,title=path.stem.replace('_',' '),author='Equipo 17 - FerreMax').build(story,onFirstPage=footer,onLaterPages=footer)

class Diagram:
    def __init__(self,id,title,w=780,h=900):
        self.id,self.w,self.h=id,w,h
        self.c=canvas.Canvas(str(DG/(id+'.pdf')),pagesize=(w,h));self.c.setTitle(title);self.c.setAuthor('Equipo 17 - FerreMax')
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
        self.nodes={};self.label(28,32,title,18,True)
    def label(self,x,y,text,size=12,bold=False,color=NAVY):
        c=self.c;c.setFillColor(color);c.setFont('Bold' if bold else 'Body',size);c.drawString(x,self.h-y-size*.2,text)
        self.svg.append(f'<text x="{x}" y="{y+size*.2}" font-family="DejaVu Sans" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color.hexval().replace("0x","#")}">{html.escape(text)}</text>')
    def line(self,x1,y1,x2,y2,dash=False,color=GRAY):
        c=self.c;c.setStrokeColor(color);c.setLineWidth(1);c.setDash([4,3] if dash else []);c.line(x1,self.h-y1,x2,self.h-y2);c.setDash([])
        self.svg.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color.hexval().replace("0x","#")}"'+(' stroke-dasharray="4 3"' if dash else '')+'/>')
    def rect(self,x,y,w,h,fill=PALE,stroke=TEAL):
        self.c.setFillColor(fill);self.c.setStrokeColor(stroke);self.c.setLineWidth(1);self.c.roundRect(x,self.h-y-h,w,h,6,fill=1,stroke=1)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill.hexval().replace("0x","#")}" stroke="{stroke.hexval().replace("0x","#")}"/>')
    def wrapped(self,x,y,text,width,size=12,bold=False):
        words=text.split();lines=[];line=''
        for word in words:
            new=(line+' '+word).strip()
            if pdfmetrics.stringWidth(new,'Bold' if bold else 'Body',size)>width and line:lines.append(line);line=word
            else:line=new
        if line:lines.append(line)
        for i,s in enumerate(lines):self.label(x,y+i*(size+4),s,size,bold)
        return len(lines)*(size+4)
    def node(self,id,x,y,w,h,title,body='',kind=''):
        self.nodes[id]=(x,y,w,h);self.rect(x,y,w,h)
        pos=y+20
        if kind:self.label(x+10,pos,kind,10,False,TEAL);pos+=18
        pos+=self.wrapped(x+10,pos,title,w-20,13,True)+6
        if body:
            self.line(x+1,pos-6,x+w-1,pos-6,color=TEAL)
            for s in body.split('\n'):pos+=self.wrapped(x+10,pos+7,s,w-20,12)+3
    def arrow(self,coords,label='',kind='ref',lx=None,ly=None):
        for a,b in zip(coords,coords[1:]):self.line(*a,*b,dash=kind in ('dep','impl'))
        x1,y1=coords[-2];x,y=coords[-1];a=math.atan2(y-y1,x-x1);length=11
        p=[(x,y),(x-length*math.cos(a-.4),y-length*math.sin(a-.4)),(x-length*math.cos(a+.4),y-length*math.sin(a+.4))]
        self.poly(p,colors.white if kind=='impl' else GRAY)
        if kind=='composition':
            x,y=coords[0];xx,yy=coords[1];a=math.atan2(yy-y,xx-x)
            self.poly([(x,y),(x+8*math.cos(a)-4*math.sin(a),y+8*math.sin(a)+4*math.cos(a)),(x+16*math.cos(a),y+16*math.sin(a)),(x+8*math.cos(a)+4*math.sin(a),y+8*math.sin(a)-4*math.cos(a))],NAVY)
        if label:self.wrapped(lx if lx is not None else (coords[0][0]+coords[-1][0])/2+5,ly if ly is not None else (coords[0][1]+coords[-1][1])/2-6,label,230,11)
    def poly(self,points,fill):
        c=self.c;p=c.beginPath();p.moveTo(points[0][0],self.h-points[0][1])
        for x,y in points[1:]:p.lineTo(x,self.h-y)
        p.close();c.setFillColor(fill);c.setStrokeColor(GRAY);c.drawPath(p,fill=1,stroke=1)
        self.svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{fill.hexval().replace("0x","#")}" stroke="#516273"/>')
    def finish(self):
        self.c.showPage();self.c.save();self.svg.append('</svg>');(DG/(self.id+'.svg')).write_text('\n'.join(self.svg))
        p=fitz.open(DG/(self.id+'.pdf'))[0];p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(DG/(self.id+'.png'))

def diagrams():
    d=Diagram('D01','D01 · Mapa general del dominio',780,780)
    for a in [('C',280,75,220,75,'Cotizacion','', 'RAÍZ'),('CC',25,220,210,75,'CuentaCredito','','RAÍZ · DISEÑO'),('P',280,220,220,75,'Pedido','','RAÍZ'),('T',545,220,210,75,'Transferencia','','RAÍZ · DISEÑO'),('E',25,445,210,75,'Entrega','','RAÍZ · DISEÑO'),('I',280,445,220,75,'InventarioUbicacion','','RAÍZ'),('D',545,445,210,75,'Devolucion','','RAÍZ · DISEÑO'),('U',280,650,220,75,'Producto y Ubicacion','','MAESTROS')]:d.node(*a)
    d.arrow([(390,150),(390,220)],'folio y versión',lx=405,ly=180)
    d.arrow([(235,255),(280,255)],'autorización',lx=26,ly=325)
    d.arrow([(390,295),(390,445)],'confirmación y reserva',lx=405,ly=355)
    d.arrow([(650,295),(650,370),(500,370),(500,460)],'movimientos confirmados',lx=540,ly=393)
    d.arrow([(280,280),(130,280),(130,445)],'surtido y destino',lx=27,ly=385)
    d.arrow([(500,280),(740,280),(740,435),(650,435),(650,445)],'comprobante de venta',lx=535,ly=315)
    d.arrow([(545,485),(500,485)],'reintegro o aislamiento',lx=528,ly=550)
    d.arrow([(390,650),(390,520)],'identidad del inventario',lx=404,ly=596)
    d.wrapped(28,754,'Las flechas representan referencias o colaboración entre agregados; no composición.',720,11);d.finish()
    d=Diagram('D02','D02 · Clases del dominio',780,1000)
    nodes=[('C',25,85,225,180,'Cotizacion','id · folio · version\ncliente_id\nrevalidar() · convertir()','RAÍZ'),('P',530,85,225,180,'Pedido','id · estado · cotizacion_version\nconfirmar() · cancelar()\ncantidades_por_sku()','RAÍZ'),('V',25,355,225,125,'Vigencia','emision · vencimiento\nesta_vigente()','VALUE OBJECT'),('Part',280,355,220,140,'Partida','numero · cantidad\nsku · precio','VALUE OBJECT'),('I',530,355,225,185,'InventarioUbicacion','sku · ubicacion_id\nexistencia_fisica · disponible\nreservar() · liberar()','RAÍZ'),('D',25,640,225,100,'Dinero','importe · moneda','VALUE OBJECT'),('S',530,640,225,100,'SKU','valor','VALUE OBJECT'),('CC',25,835,225,125,'CuentaCredito','cliente_id · activo · bloqueado\nevaluar()','RAÍZ · POLÍTICA NORMAL'),('PC',280,835,220,100,'PoliticaCredito','evaluar_normal()','SERVICIO DE DOMINIO')]
    for a in nodes:d.node(*a)
    d.arrow([(137,265),(137,355)],'1 / 1',kind='composition',lx=150,ly=310)
    d.arrow([(250,175),(390,175),(390,355)],'1 / 1..* contiene',kind='composition',lx=280,ly=230)
    d.arrow([(530,230),(450,230),(450,355)],'snapshot 1..*',kind='composition',lx=465,ly=302)
    d.arrow([(530,105),(505,105),(505,65),(250,65),(250,105)],'referencia ID y versión',kind='dep',lx=290,ly=58)
    d.arrow([(642,540),(642,640)],'identifica',lx=650,ly=591)
    d.arrow([(500,475),(515,475),(515,610),(595,610),(595,640)],'SKU',lx=525,ly=575)
    d.arrow([(305,495),(305,590),(137,590),(137,640)],'precio',lx=165,ly=579)
    d.arrow([(137,835),(137,740)],'límite y saldo',lx=148,ly=787)
    d.arrow([(280,893),(250,893)],'evalúa',kind='dep',lx=269,ly=816)
    d.arrow([(754,355),(772,355),(772,280),(754,280),(754,240)],'exige confirmado',kind='dep',lx=553,ly=338)
    d.wrapped(280,690,'Rombo: composición en la raíz. Trazo discontinuo: dependencia. Flecha simple: referencia. Cada Pedido conserva su propio snapshot de partidas.',225,11)
    d.finish()
    d=Diagram('D03','D03 · Aplicación y persistencia',780,1060)
    d.label(26,72,'APLICACIÓN · Contratos y coordinación',14,True,TEAL)
    for a in [('CS',25,100,225,110,'CotizacionService','revalidar() · convertir()','SERVICIO'),('PS',530,100,225,110,'PedidoService','confirmar() · cancelar()','SERVICIO'),('U',280,245,220,175,'UnitOfWork','cotizaciones · pedidos\ninventarios\nregistrar() · commit()','INTERFACE / PROTOCOL'),('CR',25,500,225,125,'CotizacionRepository','obtener()\nguardar_nueva_version()','INTERFACE / PROTOCOL'),('PR',280,500,220,125,'PedidoRepository','obtener() · guardar()','INTERFACE / PROTOCOL'),('IR',530,500,225,145,'InventarioRepository','obtener_para_actualizar()\nguardar() · ubicacion_reserva()','INTERFACE / PROTOCOL')]:d.node(*a)
    d.arrow([(250,180),(320,245)],'fábrica',kind='dep',lx=255,ly=214)
    d.arrow([(530,180),(460,245)],'fábrica',kind='dep',lx=480,ly=214)
    for x in [137,390,642]:d.arrow([(390,420),(390,460),(x,460),(x,500)])
    d.label(26,700,'INFRAESTRUCTURA · Implementa contratos de aplicación',14,True,TEAL)
    for a in [('PGC',25,735,225,70,'PgCotizaciones','','ADAPTADOR'),('PGP',280,735,220,70,'PgPedidos','','ADAPTADOR'),('PGI',530,735,225,70,'PgInventarios','','ADAPTADOR'),('PGU',150,890,225,75,'PostgresUnitOfWork','','ADAPTADOR TRANSACCIONAL'),('MU',445,890,240,75,'MemoryUnitOfWork','','ADAPTADOR LOCAL')]:d.node(*a)
    for x,y in [(137,625),(390,625),(642,645)]:d.arrow([(x,735),(x,y)],kind='impl')
    d.arrow([(150,925),(10,925),(10,439),(280,439),(280,390)],kind='impl')
    d.arrow([(685,925),(770,925),(770,439),(500,439),(500,390)],kind='impl')
    for x in [137,390,642]:d.arrow([(265,890),(265,850),(x,850),(x,805)],kind='composition')
    d.wrapped(28,1008,'Triángulo vacío y trazo discontinuo: implementación del contrato. Rombo: adaptadores contenidos por el UoW. El dominio se detalla en D02.',720,11);d.finish()

def sequence(id,title,events):
    # Five participants, with notes representing explicit domain invocations.
    xs=[70,250,430,610,800];names=['Caja','PedidoService','PostgresUnitOfWork','PgPedidos','PgInventarios']
    laid=[]
    for kind,a,b,height,text in events:
        width=abs(xs[a]-xs[b])+(80 if kind=='note' else -16)
        words=text.split();line='';count=1
        for word in words:
            attempt=(line+' '+word).strip()
            if pdfmetrics.stringWidth(attempt,'Body',14)>width and line:count+=1;line=word
            else:line=attempt
        laid.append((kind,a,b,max(height,count*18+30),text))
    h=145+sum(e[3] for e in laid)+40;d=Diagram(id,title,880,h)
    for x,n in zip(xs,names):d.rect(x-67,65,134,53);d.wrapped(x-60,83,n,120,12,True);d.line(x,120,x,h-40,True)
    y=145; boundaries=[0]
    for kind,a,b,height,text in laid:
        if kind=='note':
            x=min(xs[a],xs[b])-50;ww=abs(xs[a]-xs[b])+100
            d.rect(x,y+5,ww,height-14,colors.HexColor('#fff4d6'),colors.HexColor('#b3a05e'));d.wrapped(x+10,y+23,text,ww-20,14)
        else:
            d.wrapped(min(xs[a],xs[b])+8,y+18,text,abs(xs[a]-xs[b])-16,14)
            d.arrow([(xs[a],y+height-8),(xs[b],y+height-8)],kind='dep' if kind=='return' else 'ref')
        y+=height;boundaries.append(y)
    midpoint=min(boundaries[1:-1],key=lambda yy:abs(yy-h/2))
    (DG/(id+'_segments.json')).write_text(json.dumps([0,midpoint,h]))
    d.finish()

def sequences():
    sequence('D04','D04 · Confirmación y reserva - recorrido normal',[
      ('call',0,1,72,'confirmar(actor, pedido, pago, ubicacion)'),('note',1,1,60,'Comprobar rol Caja'),('call',1,2,52,'__enter__()'),('note',2,2,66,'Iniciar transacción'),('call',1,3,48,'obtener(pedido_id)'),('return',3,1,62,'Pedido bloqueado para actualizar'),('note',1,4,46,'Por cada SKU en orden uniforme:'),('call',1,4,50,'obtener_para_actualizar(SKU, ubicacion)'),('return',4,1,52,'Inventario y reservas actuales'),('note',1,4,86,'Invocar Pedido.confirmar(pago); después InventarioUbicacion.reservar(pedido, cantidad). Cambios aún provisionales.'),('call',1,4,50,'guardar(cada inventario)'),('call',1,3,50,'guardar(pedido confirmado)'),('call',1,2,70,'registrar(auditoría, PedidoConfirmado)'),('call',1,2,50,'commit()'),('return',2,1,50,'COMMIT exitoso'),('call',1,2,50,'__exit__()'),('return',1,0,62,'DTO: estado Confirmado')])
    sequence('D05','D05 · Rechazo - última unidad ya comprometida',[
      ('note',0,1,78,'Una consulta previa mostró stock; otro pedido ya lo reservó.'),('call',0,1,72,'confirmar(actor, pedido, pago, ubicacion)'),('call',1,2,50,'__enter__()'),('call',1,3,50,'obtener(pedido_id)'),('return',3,1,60,'Pedido Pendiente bloqueado'),('call',1,4,58,'obtener_para_actualizar(SKU, ubicacion)'),('note',3,4,78,'FOR UPDATE espera al otro pedido si es necesario.'),('return',4,1,54,'Disponible actual = 0'),('note',1,4,92,'Pedido.confirmar cambia solo el objeto provisional; InventarioUbicacion.reservar lanza DisponibilidadInsuficiente.'),('call',1,2,54,'__exit__(error)'),('note',2,3,72,'conn.rollback(); cerrar conexión'),('return',2,1,66,'Sin nuevos cambios persistidos'),('return',1,0,60,'Error de disponibilidad'),('note',0,4,68,'Pedido sigue Pendiente: sin reserva ni evento de confirmación. La política financiera de pago ya autorizado permanece pendiente (H05).')])

def main():
    data=json.loads((DOC/'current_sources.json').read_text())
    data['report']=data['report'].replace('Fuentes Mermaid propuestas; BPMN verificado con hallazgo H07. Exportaciones pendientes por desconexión del entorno.','Cinco fuentes Mermaid y vistas vectoriales SVG, PDF y PNG. BPMN de U2 verificado; hallazgo H07 documentado.').replace('PDF FIME, empaquetado y publicación pendientes porque el entorno de ejecución se desconectó.','Informe FIME y paquete preparados; publicación en GitHub pendiente de disponibilidad de la conexión.').replace('GitHub y PDF FIME','Paquete y GitHub')
    data['diagrams']=data['diagrams'].replace('El render y las exportaciones finales PDF/PNG están pendientes del restablecimiento de la conexión local. La revisión visual del BPMN de U2 también sigue pendiente.','Se adjuntan exportaciones PDF/PNG y vistas vectoriales SVG, además de las fuentes Mermaid. BPMN de U2 revisado visualmente; véase H07.')
    import platform
    data['defense']=data['defense'].replace('Contenido completo en el borrador privado de Notion; PDF FIME pendiente.','Informe FIME generado y revisado visualmente; copia editable en Markdown.').replace('Fuentes Mermaid propuestas D01–D03; exportación e inspección visual pendientes.','D01-D03: fuentes Mermaid y vistas SVG, PDF y PNG revisadas.').replace('D04 y D05 preparadas en fuente editable.','D04 y D05 con fuente Mermaid y exportaciones SVG, PDF y PNG.').replace('Seis iteraciones reales, errores y decisiones identificados.','Diez iteraciones documentadas; errores, correcciones y decisiones identificados.').replace('Núcleo escrito y 20 pruebas locales correctas; empaquetado y ensayo PG pendientes.','Código empaquetado y 20 pruebas locales correctas; ensayo PG pendiente.').replace('con Python 3.9','inicialmente con Python 3.9; la ejecución final usa Python '+platform.python_version()).replace('.drawio','.svg').replace('[README.md](http://README.md)','README.md')
    if 'IA10:' not in data['decisions']:
        data['decisions']+='\n## Cierre de generación y revisión\n**IA10:** Tras recuperar el entorno se ejecutaron 21 pruebas: 20 correctas y una PostgreSQL omitida por falta de TEST_DATABASE_URL. Se generaron el informe FIME, la guía y cinco diagramas con fuentes y exportaciones; se revisaron visualmente y se preparó el paquete. La creación del proyecto Supabase sigue bloqueada porque get_cost no está disponible. GitHub requiere una sesión de navegador para crear el repositorio; no se registra publicación ni defensa humana como realizadas.\n'
    data['defense']=re.sub(r'El código existente está en la carpeta ferremax-u3[^\n]*','El código existente está en la carpeta ferremax-u3. El núcleo y las pruebas Memory usan la biblioteca estándar; la ejecución final pasó con Python '+platform.python_version()+'. La conexión PostgreSQL se preparó para Python 3.10 o posterior y Psycopg 3.3.6; su ensayo conectado sigue pendiente.',data['defense'])
    # Sources remain auditable; generated documentation records only observed results.
    for k,name in [('report','Informe_Arquitectura.md'),('decisions','ADR_y_Trazabilidad.md'),('diagrams','Diagramas.md'),('defense','Guia_Defensa.md')]:
        (DOC/name).write_text(re.sub(r'<mention-date start="([^"]+)"[^>]*/>',r'\1',data[k]))
    (DOC/'current_sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    for section in re.split(r'(?=^## D\d\d )',data['diagrams'],flags=re.M):
        m=re.match(r'## (D\d\d) ',section)
        if m:
            code=re.search(r'```mermaid\n(.*?)\n```',section,re.S)
            if code:(DG/(m[1]+'.mmd')).write_text(code[1]+'\n')
    for m in re.finditer(r'^## (ADR\d{3}[^\n]*)\n(.*?)(?=^## |\Z)',data['decisions'],re.S|re.M):
        p=DOC/'adr';p.mkdir(exist_ok=True);(p/(m[1][:6]+'.md')).write_text('# '+m[1]+'\n'+m[2])
    for i,xml in enumerate(re.findall(r'<table\b.*?</table>',data['decisions'],re.S),1):
        rows=[[plain(x).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)] for row in re.findall(r'<tr[^>]*>(.*?)</tr>',xml,re.S)]
        with (DOC/f'trazabilidad_{i:02}.csv').open('w',newline='') as f:csv.writer(f).writerows(rows)
    diagrams();sequences()
    text=data['report'];a=text.index('## 4 ');b=text.index('## 5 ')
    comp=text[a:b]; c=comp.index('### Evaluación de Transaction Script')
    report=cover('Informe de arquitectura')+markdown(text[:a])+[PageBreak()]+markdown(comp[:c])+[PageBreak()]+markdown(comp[c:])+[PageBreak()]+markdown(text[b:])
    report+=[PageBreak(),Paragraph('Anexo A · Diagramas de arquitectura',S['H1X']),Paragraph('Los cinco diagramas conservan fuentes .mmd y vistas .svg editables. Los PDF y PNG individuales permiten ampliarlos durante la revisión. Estas vistas se generaron a partir de las relaciones y los mensajes de las fuentes; no representan validación de una base PostgreSQL conectada.',S['Text'])]
    # Landscape sequence exports are shown as two readable segments in the portrait report.
    for id in ['D01','D02','D03','D04','D05']:
        if id!='D01':report.append(PageBreak())
        report.append(Paragraph(id+' · Vista del diseño',S['H1X']))
        source=fitz.open(DG/(id+'.pdf'));page=source[0]
        if id in ['D04','D05']:
            boundaries=json.loads((DG/(id+'_segments.json')).read_text())
            for n,(top,bot) in enumerate(zip(boundaries,boundaries[1:])):
                if n:report.extend([PageBreak(),Paragraph(id+' · Continuación',S['H1X']),Paragraph('Participantes de izquierda a derecha: Caja, PedidoService, PostgresUnitOfWork, PgPedidos y PgInventarios.',S['SmallX'])])
                crop=fitz.Rect(0,top,page.rect.width,bot);path=QA/(id+f'_{n}.png');page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),clip=crop,alpha=False).save(path)
                report.append(Image(str(path),width=WIDTH,height=WIDTH*crop.height/crop.width))
        else:
            hh=WIDTH*page.rect.height/page.rect.width
            report.append(Image(str(DG/(id+'.png')),width=WIDTH,height=hh))
    report+=[PageBreak(),Paragraph('Anexo B · Decisiones, trazabilidad y uso de IA',S['H1X'])]+markdown(data['decisions'])
    report+=[PageBreak(),Paragraph('Anexo C · Evidencia de ejecución local',S['H1X']),Paragraph('Ejecución del núcleo y recorrido reproducible. El ensayo PostgreSQL se omite cuando no existe TEST_DATABASE_URL. No se declara validación de Supabase ni cumplimiento de tiempos de RNF01.',S['Text'])]
    p=DOC/'evidence'/'pruebas_locales.txt'
    if p.exists():
        log=p.read_text();report+=markdown('### Pruebas locales\nLos nombres y la salida completa están en docs/evidence/pruebas_locales.txt. Resumen literal del resultado:\n```text\n'+'\n'.join(log.splitlines()[-6:])+'\n```')
    p=DOC/'evidence'/'demo.txt'
    if p.exists():
        values=json.loads(p.read_text());lines=[json.dumps(v,ensure_ascii=False,separators=(',',':')) for v in values]
        report+=markdown('### Recorrido del demo\nSalida JSON de la consulta, revalidación, conversión, confirmación y cancelación, compactada para su lectura. Los UUID son datos sintéticos de esta ejecución.\n```json\n'+'\n'.join(lines)+'\n```')
    doc(OUT/'FerreMax_U3_Informe_FIME.pdf',report)
    defense=data['defense'].replace(' `.drawio`,','').replace(' `.drawio`','').replace('.drawio','.svg')
    doc(OUT/'FerreMax_U3_Guia_Defensa.pdf',cover('Guía de defensa y ejecución')+markdown(defense))
    shutil.copy2(OUT/'FerreMax_U3_Informe_FIME.pdf',DOC/'FerreMax_U3_Informe_FIME.pdf');shutil.copy2(OUT/'FerreMax_U3_Guia_Defensa.pdf',DOC/'Guia_Defensa.pdf')
    for path in OUT.glob('*.pdf'):
        pdf=fitz.open(path);pdir=QA/path.stem;pdir.mkdir(exist_ok=True)
        for i,page in enumerate(pdf):page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False).save(pdir/f'{i+1:02}.png')
        print(path.name,'pages',len(pdf),'bytes',path.stat().st_size)
if __name__=='__main__':main()

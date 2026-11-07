/* Presentación sobre Swagger real; App/DB de CI, sin escribir en producción. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.FERREMAX_PLAYWRIGHT || 'playwright');
(async()=>{
 fs.mkdirSync('reports/ci',{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8000/docs');
  await page.locator('.opblock').first().waitFor();
  assert.equal(await page.locator('.opblock').count(),6);
  assert(!await page.locator('.opblock-summary-path').first().isVisible());
  function op(title){return page.locator('.opblock').filter({has:page.locator('.opblock-summary-description').getByText(title,{exact:true})});}
  async function open(title){const block=op(title);await block.locator('.opblock-summary').click();return block;}
  const stock=await open('Consultar disponibilidad');
  // Los ejemplos de respuesta muestran mensaje, no rellenos de esquema string/0.
  const example=stock.locator('.responses-inner .highlight-code pre').first();
  await example.waitFor();
  assert.match(await example.innerText(),/mensaje/);
  assert(!(await example.innerText()).includes('ubicaciones'));
  await stock.getByRole('button',{name:'Try it out',exact:true}).click();
  await stock.locator('input[placeholder="sku"]').fill('FER-API-DEMO');
  await stock.getByRole('button',{name:'Execute',exact:true}).click();
  const body=stock.locator('.live-responses-table .highlight-code pre').first();
  await body.waitFor();
  let visible=JSON.parse(await body.innerText());
  assert.deepEqual(Object.keys(visible),['mensaje']);
  assert.match(visible.mensaje,/10 unidades disponibles/);
  const raw=await(await page.request.get('http://127.0.0.1:8000/inventario/FER-API-DEMO')).json();
  assert.equal(raw.ubicaciones[0].disponible,'10');
  await page.screenshot({path:'reports/ci/swagger-simple-inventario.png',fullPage:true});
  await page.getByLabel('Mostrar detalles técnicos',{exact:true}).check();
  await page.waitForFunction(()=>document.body.classList.contains('detalles-tecnicos'));
  assert(await page.locator('.opblock-summary-path').first().isVisible());
  await page.waitForFunction(()=>document.querySelector('.live-responses-table pre')?.textContent.includes('ubicaciones'));
  assert(JSON.parse(await body.innerText()).ubicaciones);
  await page.getByLabel('Mostrar detalles técnicos',{exact:true}).uncheck();
  await stock.locator('input[placeholder="sku"]').fill('PRODUCTO-QUE-NO-EXISTE');
  await stock.getByRole('button',{name:'Execute',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.live-responses-table pre')?.textContent.includes('Producto no encontrado'));
  assert.deepEqual(Object.keys(JSON.parse(await body.innerText())),['mensaje']);
  const create=await open('Crear pedido');
  await create.getByRole('button',{name:'Try it out',exact:true}).click();
  await create.locator('input[placeholder="cotizacion_id"]').fill('11111111-1111-4111-8111-111111111111');
  await create.locator('input[placeholder="version"]').fill('2');
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/versiones/2/convertir') && r.request().method()==='POST');
  await create.getByRole('button',{name:'Execute',exact:true}).click();
  const response=await responsePromise;assert.equal(response.status(),201);
  const actual=await response.json();assert(actual.pedido_id && actual.estado==='Pendiente');
  const createdBody=create.locator('.live-responses-table .highlight-code pre').first();await createdBody.waitFor();
  visible=JSON.parse(await createdBody.innerText());assert.deepEqual(Object.keys(visible),['mensaje']);
  assert.match(visible.mensaje,/240/);assert(!JSON.stringify(visible).includes(actual.pedido_id));
  await page.screenshot({path:'reports/ci/swagger-simple-pedido.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'reports/ci/swagger-simple-movil.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('Swagger: seis operaciones, ejemplos claros, respuestas reales 200/404/201 simplificadas, detalles técnicos recuperables y contrato HTTP completo verificados.');
 }catch(e){await page.screenshot({path:'reports/ci/swagger-fallo.png',fullPage:true});throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

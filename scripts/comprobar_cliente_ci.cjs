/* Prueba de navegador sobre App/DB desechables de CI; nunca sobre producción. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.FERREMAX_PLAYWRIGHT || 'playwright');
const base = 'http://127.0.0.1:8000';
(async () => {
  fs.mkdirSync('reports/ci', {recursive: true});
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1100}});
    const errors = [], posts = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('request', req => { if (req.method() === 'POST') posts.push(req.url()); });
    await page.goto(base + '/cliente');
    await page.locator('#quote option').filter({hasText: 'COT-RENOVAR-DEMO'}).waitFor({state:'attached'});
    // La renovación está bloqueada cuando el servidor informa vigencia actual.
    const qs = (await (await page.request.get(base + '/cliente/cotizaciones')).json()).cotizaciones;
    const current = qs.find(q => q.folio === 'COT-API-DEMO');
    const expired = qs.find(q => q.folio === 'COT-RENOVAR-DEMO');
    assert(current && expired && expired.renovable);
    await page.locator('#quote').selectOption(current.id);
    assert(await page.getByRole('button', {name:'Renovar cotización', exact:true}).isDisabled());
    assert.match(await page.locator('#blocked').innerText(), /todavía está vigente/);
    await page.locator('#quote').selectOption(expired.id);
    await page.getByLabel('Precio por unidad', {exact:true}).fill('120.00');
    await page.getByLabel('Motivo de la renovación').fill('El cliente solicita actualizar sus precios');
    await page.getByLabel('Condiciones acordadas con el cliente').fill('Precios revisados y pago de contado');
    assert.match(await page.locator('#total').innerText(), /240/);
    await page.screenshot({path:'reports/ci/cliente-formulario.png', fullPage:true});
    await page.getByRole('button', {name:'Renovar cotización', exact:true}).click();
    await page.getByRole('heading', {name:'Cotización renovada', exact:true}).waitFor();
    const receipt = await page.locator('#result').innerText();
    assert.match(receipt, /COT-RENOVAR-DEMO/);
    assert.match(receipt, /Puedes utilizarla hasta/);
    assert.match(receipt, /historial/);
    assert(!receipt.includes(expired.id) && !receipt.includes('version_anterior'));
    assert.equal(posts.length, 1);
    assert(await page.locator('#submit').isDisabled());
    const updated = (await (await page.request.get(base+'/cliente/cotizaciones')).json()).cotizaciones.find(q=>q.id===expired.id);
    assert.equal(updated.version, 2); assert.equal(updated.renovable, false);
    await page.screenshot({path:'reports/ci/cliente-renovada.png', fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'reports/ci/cliente-movil.png',fullPage:true});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    // Error de consulta: se bloquea el formulario y se ofrece recuperación.
    await page.route('**/cliente/cotizaciones', route=>route.fulfill({status:503,json:{mensaje:'No disponible'}}));
    await page.getByRole('button',{name:'Actualizar cotizaciones'}).click();
    await page.getByRole('heading',{name:'No pudimos consultar tus cotizaciones'}).waitFor();
    assert(await page.locator('#submit').isDisabled());
    await page.unroute('**/cliente/cotizaciones');
    await page.getByRole('button',{name:'Actualizar cotizaciones'}).click();
    await page.locator('#quote').waitFor({state:'visible'});
    await page.waitForFunction(()=>!document.getElementById('quote').disabled);
    // Cotización sin emitir: el usuario recibe una explicación, no una excepción.
    await page.route('**/cliente/cotizaciones', route=>route.fulfill({json:{cotizaciones:[{...expired,estado:'Por emitir',renovable:false}]}}));
    await page.getByRole('button',{name:'Actualizar cotizaciones'}).click();
    await page.waitForFunction(()=>document.querySelector('#quote option:last-child').textContent.includes('Por emitir'));
    await page.locator('#quote').selectOption(expired.id);
    assert.match(await page.locator('#blocked').innerText(), /aún no ha sido emitida/);
    // Pérdida de conexión durante POST: no afirmar ni éxito ni rollback.
    await page.unroute('**/cliente/cotizaciones');
    await page.route('**/cliente/cotizaciones', route=>route.fulfill({json:{cotizaciones:[expired]}}));
    await page.route('**/revalidar', route=>route.abort());
    await page.getByRole('button',{name:'Actualizar cotizaciones'}).click();
    await page.waitForFunction(()=>document.querySelector('#quote option:last-child').textContent.includes('Vencida'));
    await page.locator('#quote').selectOption(expired.id);
    await page.getByLabel('Motivo de la renovación').fill('Comprobar comunicación');
    await page.getByRole('button',{name:'Renovar cotización',exact:true}).click();
    await page.getByRole('heading',{name:'Necesitamos comprobar la renovación'}).waitFor();
    assert(await page.locator('#submit').isDisabled());
    assert.match(await page.locator('#result-text').innerText(), /no podemos confirmar si se guardó/);
    await page.unroute('**/revalidar'); await page.unroute('**/cliente/cotizaciones');
    // Datos sin documentos: estado vacío comprensible, sin botones engañosos.
    await page.route('**/cliente/cotizaciones', route=>route.fulfill({json:{cotizaciones:[]}}));
    await page.getByRole('button',{name:'Actualizar cotizaciones'}).click();
    await page.getByText('Todavía no hay cotizaciones registradas.').waitFor();
    assert(await page.locator('#quote').isDisabled());
    assert.deepEqual(errors, []);
    console.log('Cliente UI: renovación persistida, vigencia, error recuperable, conexión incierta, estado vacío y móvil comprobados.');
  } finally { await browser.close(); }
})().catch(error=>{ console.error(error); process.exitCode=1; });

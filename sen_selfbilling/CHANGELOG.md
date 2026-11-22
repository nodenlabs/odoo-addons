# Changelog — sen_selfbilling

## v19 → v20

Migración de Odoo **19.0** → **20.0**, en el mismo lugar (rama `20.0`). Reglas aplicadas del skill `odoo-module-migration`: reglas generales, salto v19→v20 y la parte v20 del barrido de `final-scan.md`. Todo se comprobó contra el código de 20.0 (community `odoo-20.0`, enterprise `odoo-20.0-e`), y los módulos MX se compararon con 19.0 enterprise.

### Paso 0 — reescritores de Odoo (ya aplicados, revisados a mano)
- `19.1-00-t-call` en `views/portal_templates.xml`: `breadcrumbs_searchbar` pasó de `<t t-set>` dentro del `t-call` a atributo de `portal.portal_layout`. Correcto.
- El mismo script reescribió la llamada a `portal.portal_docs_entry` de la tarjeta de `/my/home` (`icon.f`, `title.translate`, `url.f`, `text`, `config_card`). Sintaxis correcta, pero en v20 esa plantilla ya no recibe esos parámetros (ver abajo), así que se reemplazó.
- Font Awesome → Material Symbols: `<i class="fa fa-info-circle">` → `<i class="oi oi-filled" data-icon="info">`. Verificado: `oi-filled` existe en `web/static/src/webclient/icons.scss` y el core usa la misma combinación (`website_crm_partner_assign`, `account`).

### General
- `__manifest__.py`: `version` `19.0.1.5.0` → `20.0.1.5.0`. Se agregó `data/portal_entry_data.xml` a `data`.
- No hay `init_xml`/`update_xml`/`demo_xml`, ni carpeta `migrations/`, ni encabezados `coding`, ni `print()` activos. El único `super(Clase, self)` sigue en el controlador POS comentado.

### Portal `/my/home` — tarjeta «Facturación» (`views/portal_templates.xml`, `data/portal_entry_data.xml`)
- **Rompía la instalación.** En v20 `portal.portal_my_home` ya no tiene `div#portal_client_category` ni la variable `portal_client_category_enable`: las tarjetas son registros del modelo nuevo `portal.entry` (`portal/models/portal_entry.py`), y `portal.portal_docs_entry` pinta `entry.name`, `entry.description`, `entry.url` y `entry.image`. Con la herencia de v19 la instalación fallaba con `Element '<div id="portal_client_category">' cannot be located in parent view`.
- Se eliminó la plantilla `portal_my_home_billing`. Se agregó el registro `portal_entry_billing` (`portal.entry`, `noupdate="1"` igual que en el core): nombre «Facturación», descripción «Datos fiscales y facturación automática», URL `/my/billing`, imagen `account/static/src/img/bill.svg` (`type="bytes"`, el formato de v20), categoría `client_category`, `is_config_card=True` y secuencia 45. Mismo patrón que `payment.payment_methods_portal_entry` y `account.portal_invoice_client`. Al ser tarjeta de configuración sin `placeholder_count`, `_filter_visible_portal_cards()` la muestra siempre, igual que `config_card` en v19.
- El estado «Facturación automática: Activa/Inactiva» depende del usuario y no cabe en la descripción fija del registro. Por eso se agregó `portal_docs_entry_billing`, que hereda `portal.portal_docs_entry` y agrega una línea después de `//p[@t-field='entry.description']`, sólo si `entry` es `sen_selfbilling.portal_entry_billing`.
- La herencia de `portal.portal_breadcrumbs` (`ol.o_portal_submenu`) y el uso de `portal.portal_layout` (`breadcrumbs_searchbar`, cuerpo `t-out="0"`) se validaron en v20 sin cambios. `request.csrf_token()` sigue existiendo (`odoo/http/requestlib.py`).
- No se crearon `ir.access`: el módulo no define modelos nuevos (sólo campos en `res.partner` y `sale.order`), y `portal.entry` ya tiene lectura para `base.group_everyone` en `portal/security/ir.access.csv`. No había `ir.model.access.csv` que convertir.

### `/my/billing` (`controllers/portal.py`, `models/res_partner.py`)
- **`res.partner.can_edit_vat()` se eliminó en v20** (no existe en `portal`, `account` ni `sale`). La página daba `AttributeError` en cada carga. El portal del core ahora decide con `_has_confirmed_documents()` (facturas publicadas o ventas confirmadas en la empresa) y `_is_main_contact()`.
- Nuevo `res.partner._selfbilling_can_edit_vat()`: `not self.parent_id and not self._has_confirmed_documents()`. Es exactamente lo que devolvía `can_edit_vat()` en v19 (portal: `not parent_id`; account: sin facturas publicadas `child_of` la empresa; sale: sin ventas `sent`/`sale` `child_of` la empresa). El controlador lo llama sobre la empresa del usuario, como antes.

### `/billing` (`views/billing_tmpl.xml`, `controllers/main.py`)
- `t-esc` → `t-out` en las 3 apariciones: el mensaje de error del paso 1, los nombres de forma de pago del paso 2 y el mensaje de error del paso 3. En v20 `t-esc` en QWeb del servidor no pinta nada (sólo deja un WARNING), así que el comprador no habría visto ni el error ni las formas de pago. Los valores son texto plano, y `t-out` los sigue escapando.
- Rutas: `odoo.http` sólo se usa para `http.route` y `request` (siguen exportados en v20). No hay `request.website`, `get_current_website` ni `website.default_website`. No hay métodos `_auth_method_*` propios. `auth='public'`/`auth='user'` con `website=True` y `sitemap=False` se aceptan igual. `readonly` sigue siendo `False` por defecto salvo con `auth='none'` (`odoo/http/routing_map.py`), así que los POST siguen escribiendo. CSRF sigue activo por defecto en rutas `http`, y los formularios ya mandan `csrf_token`.
- `website.layout` existe en v20 (ahora hereda de `portal.frontend_layout`).

### Timbrado y envío (`models/account_move.py`)
- **`extra_edis` ahora es una lista.** En v20 `account.move.send._get_default_extra_edis()` devuelve `list` y `_get_default_sending_settings()` hace `vals['sending_methods'] + vals['extra_edis']`. Con el `{'mx_cfdi'}` de v19 daba `TypeError: can only concatenate list (not "set") to list`. El módulo lo atrapaba y no timbraba ninguna factura («No se pudo timbrar … intente más tarde»). Ahora se pasa `extra_edis=['mx_cfdi']`.
- `account.move.send._generate_and_send_invoices(moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings)` tiene la misma firma. `sending_methods` se sigue validando contra `res.partner.invoice_sending_method` (`manual`, `email`). En v20 se agregó `_generate_and_send_invoices_post_commit`; el módulo sigue usando la versión síncrona porque necesita el resultado del PAC en la misma petición.
- `l10n_mx_edi/models/account_move_send.py` es idéntico en 19 y 20 enterprise (la EDI sigue llamándose `mx_cfdi`). `l10n_mx_edi_cfdi_state='sent'`, `l10n_mx_edi_invoice_document_ids` y el estado `invoice_sent_failed` de `l10n_mx_edi.document` siguen existiendo.
- `account.move.preview_invoice()` sigue devolviendo `{'type': 'ir.actions.act_url', 'url': get_portal_url()}`.

### Módulos MX (comparación 19 → 20 enterprise)
- `l10n_mx_edi_sale`: `sale.order` conserva `l10n_mx_edi_cfdi_to_public`, `l10n_mx_edi_payment_method_id`, `l10n_mx_edi_usage` y `l10n_mx_edi_payment_policy` con los mismos cálculos, y `_prepare_invoice` los copia a la factura igual que antes. **Único cambio:** `_compute_l10n_mx_edi_cfdi_to_public` ahora depende también de `partner_id` y es `True` cuando `partner_id.country_code != 'MX'`, además de cuando la dirección está incompleta. La facturación automática ya omitía las ventas «a público en general» (`_selfbilling_auto_skip_reason`), así que ahora también omite las de clientes con país extranjero. Ver TODO_AI para `/billing`.
- `l10n_mx_edi`: `res.partner` conserva `l10n_mx_edi_fiscal_regime`, `l10n_mx_edi_usage`, `l10n_mx_edi_payment_method_id` y `l10n_mx_edi_payment_policy`. `pytz` cambió a `zoneinfo` internamente, sin efecto en el módulo. `get_partner_localisation_fields_required_to_invoice` ahora también pide `vat` (sólo lo usa el controlador POS comentado). `l10n_mx_edi.payment.method` sigue con el mismo modelo; `code` y `name` ahora son `readonly`. `/billing` sólo los lee.
- `l10n_mx_edi_website_sale` no es dependencia del módulo. Se revisó el diff 19→20 y no hay nada que el módulo use.

### Ventas, entregas y cron (`models/sale_order.py`, `models/stock_picking.py`, `data/ir_cron.xml`)
- `sale.order._create_invoices` cambió de `(grouped=False, final=False, date=None)` a `(final=False, grouped=False)`. El módulo sólo la llama sin argumentos o con `final=True` por nombre, así que no le afecta.
- `stock.picking._action_done(self)`: misma firma.
- `ir.cron._commit_progress(processed=0, *, remaining=None, deactivate=False)` es idéntico al de 19. Se mantiene la llamada de la migración 18→19 dentro de `if not _in_test()`. v20 agrega `ir.cron._rollback_progress()`, que sólo hace `cr.rollback()`. El módulo sigue llamando `cr.rollback()` directamente (mismo efecto, también fuera de pruebas). `ir.cron._trigger(at=...)` y `odoo.modules.module.current_test` no cambiaron.
- Correo: `message_post(body=Markup, subtype_xmlid=...)` y `activity_schedule('mail.mail_activity_data_todo', user_id=..., summary=..., note=...)` tienen la misma firma. No se usan `_message_post_after_hook`, `msg_vals`, `_track_*` ni `mail.tracking.value`.

### Vistas backend (`views/backend_views.xml`)
- Anclas validadas en v20 (la instalación las resuelve): `l10n_mx_edi_usage` y `fiscal_country_codes` en la ficha del contacto, `res.partner.open_commercial_entity`, `group[@name='sale_info']` en `sale.view_order_form` y el filtro `my_sale_orders_filter` en `sale.view_sales_order_filter`. No hay `toggle_active`, widgets eliminados ni atributos de fecha en `<filter>`.

### Patrones de v20 no encontrados
- No hay `get_param`/`set_param`, `read_group(`, `_table_query`, `ormcache`/`clear_cache`, `odoo.osv`, `_check_access`/`SELF_*_FIELDS`, `toggle_active`, `get_formview_action`, `b64encode`/`b64decode`, campos binarios propios, `datas`/`raw`, `bin_size`, `pytz`, imports movidos de `odoo.http`, `request.session.*`, `odoo.service`, `_auth_method_*`, hooks de correo, motores de reportes ni `t-raw`. No hay `static/src` (ni JS ni OWL). No hay campos `name` propios afectados por el nuevo sufijo « (copy)». No hay `i18n/`.

### Pruebas
- `tests/test_portal.py` (`test_rfc_locked_after_invoices`): el parche pasó de `res.partner.can_edit_vat` (ya no existe, `patch.object` fallaría) a `res.partner._has_confirmed_documents → True`, que es lo que el core usa en v20 para «el cliente ya tiene documentos emitidos». Así la prueba sigue ejercitando la lógica del módulo (`_selfbilling_can_edit_vat`). Aserciones sin cambios.
- `tests/test_auto_invoice.py` (`test_delivery_invoices_stamps_and_emails`): `assertEqual(…['extra_edis'], {'mx_cfdi'})` → `['mx_cfdi']`. Es el tipo que exige Odoo 20; la aserción sigue siendo de igualdad exacta.
- Nueva prueba `TestPublicBilling.test_invalid_folio_message_is_rendered`: `/billing?folio=…` precarga el folio y un folio inexistente muestra «Folio inválido #…» en la página. Cubre el cambio `t-esc` → `t-out` del paso 1, que antes no tenía prueba. Silencia el `_logger.error` esperado del controlador.

### Descripción (`static/description/index.html`)
- «Odoo 19 Enterprise» → «Odoo 20 Enterprise», «Odoo 19.0 Enterprise» → «Odoo 20.0 Enterprise» y «Version 19.0» → «Version 20.0». No se tocaron el copyright, los precios ni las URLs.

### Decisiones
- No se corrigió `<spa t-if="message_error" …>` (debería ser `<span>`) en el paso 1 de `/billing`. Ya estaba así en 18/19, el navegador lo pinta como elemento en línea y no tiene que ver con la migración.
- La imagen decorativa del paso 1 (`/es_MX/web_editor/image_shape/...pattern_points_1.svg`) sigue rota igual que en 18/19. Se deja como está.
- La línea de estado de la tarjeta usa `request.env.ref('sen_selfbilling.portal_entry_billing', raise_if_not_found=False)`, no la URL. Así sigue funcionando aunque alguien edite la URL de la tarjeta desde el editor del portal. Si se borra el registro, simplemente no se muestra.

### Verificación

```bash
cd /tmp/odoo20-port && docker compose exec -T odoo python3 /mnt/odoo-20.0/odoo-bin \
  --addons-path=/mnt/enterprise,/mnt/odoo-20.0/addons,/mnt/odoo-20.0/odoo/addons,/mnt/extra-addons \
  --db_host=db --db_user=odoo --db_password=odoo -d t20_selfbill_e \
  -i sen_selfbilling --test-tags /sen_selfbilling --stop-after-init \
  --http-port=18621 --gevent-port=18622 --without-demo=all
```

**Resultado (2026-11-19), instalación desde cero en la base `t20_selfbill_e` (Odoo 20.0 + Enterprise 20.0):**

```
odoo.modules.loading: Module sen_selfbilling loaded in 0.37s, 352 queries (+352 other)
odoo.tests.stats: sen_selfbilling: 34 tests 14.17s 18372 queries
odoo.tests.stats: web: 6 tests 0.01s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 26 tests when loading database 't20_selfbill_e'
```

- `ir_module_module`: `sen_selfbilling | installed | 20.0.1.5.0`.
- Se ejecutaron las 24 pruebas del módulo: las 23 de v19 más la nueva de `/billing`. Las otras 2 del total son las suites JS de `web` que arrastra el filtro de etiquetas; no hay navegador y no cuentan como fallo.
- No hay `ERROR`, `WARNING` de `sen_selfbilling`, `Unknown directives`, `DeprecationWarning` ni `UserWarning` en el log. Los únicos WARNING son del entorno: `markdown2` no instalado y `--without-demo=all`.
- Antes de las correcciones, la primera ejecución (`t20_selfbill_a`) no instalaba (`div#portal_client_category` no existe). La segunda (`t20_selfbill_b`) instalaba, pero fallaban las 2 pruebas MX con el `TypeError` de `extra_edis`.

**Nota sobre el entorno:** según el log (`addons paths`), la imagen trae su propio Odoo empaquetado (`20.0.post20260926`, en `/usr/lib/python3/dist-packages/odoo/addons`), y esa ruta va **antes** que `/mnt/odoo-20.0/addons`. Por eso los addons community (`account`, `sale`, `portal`, …) se cargaron de la imagen y no del checkout local (`632c2d6c`, 2026-10-24). El servidor (`odoo/`) y Enterprise sí vienen de las fuentes locales. En `account_move_send.py` la única diferencia entre ambos es `_generate_and_send_invoices_post_commit`, que es nuevo en el local y el módulo no usa. El resto de los addons community no se comparó archivo por archivo.

**Lo que no prueban los tests:** el timbrado contra un PAC real (se simula con `with_mocked_pac_sign_success/error` y, en `SelfBillingCommon`, simulando `_generate_and_send_invoices`); el flujo completo de `/billing` con un folio válido hasta la factura (sólo se prueba el folio inválido); la página `/billing` en un navegador real; los conectores de Mercado Libre, Amazon y Yuju, que no están instalados; y el cron real con `_commit_progress` dentro de un worker.

### TODO_AI (Human Review Required)

1. **`controllers/main.py` — `/billing` y `l10n_mx_edi_cfdi_to_public`.** `l10n_mx_edi_sale` calcula `sale.order.l10n_mx_edi_cfdi_to_public` a partir de `partner_id` (el comprador del marketplace), no de `partner_invoice_id`, y `_prepare_invoice` lo copia a la factura. `/billing` cambia `partner_invoice_id` al cliente con RFC, pero no regresa ese indicador a `False`. Si el comprador no tiene dirección fiscal completa o, desde v20, tiene país distinto de México, la factura podría timbrarse a «público en general» en lugar del RFC capturado. El comportamiento es el mismo que en v19; v20 sólo amplió la condición. No se cambió el código porque no hay prueba ni caso real de `/billing` completo con un conector instalado para confirmarlo. Si se confirma, lo esperado sería agregar `'l10n_mx_edi_cfdi_to_public': False` al `sale_order.write({...})` de ese paso (no se generó automáticamente).

---

Migración de Odoo **18.0** → **19.0**. Reglas aplicadas del skill `odoo-module-migration`: reglas generales y salto v18→v19, más el barrido de `final-scan.md` (partes general y v13–v19).

## General

- `__manifest__.py`: `version` actualizada de `18.0.1.5.0` a `19.0.1.5.0`.
- `__manifest__.py` y `__init__.py`: eliminado el encabezado `# -*- coding: utf-8 -*-` (innecesario desde v11).
- No hay `super(Clase, self)` activos (el único está en código comentado del controlador POS, que se dejó como estaba), ni `print()`, ni imports de `openerp`, ni `noupdate="0"`, ni carpeta `migrations/`.

## v18 → v19

### Datos (`data/ir_cron.xml`)
- `ir.actions.server` «Facturar, timbrar y enviar al cliente»: `<field name="groups_id">` → `<field name="group_ids">` (el campo se renombró en v19).

### Plantillas del portal (`views/portal_templates.xml`)
- Icono de la tarjeta «Facturación» en `/my/home`: `/account/static/src/img/Bill.svg` → `/account/static/src/img/bill.svg`. En v19 el archivo se renombró en minúsculas (así lo usa `account/views/account_portal_templates.xml`); con la ruta anterior el icono daba 404.
- Herencias validadas contra el código fuente de v19, sin cambios: `portal.portal_my_home` (`//div[hasclass('o_portal_docs')]` y `div#portal_client_category` siguen existiendo; `portal_client_category_enable` sigue controlando la visibilidad), `portal.portal_docs_entry` (mismos parámetros `icon`/`title`/`url`/`text`/`config_card`), `portal.portal_breadcrumbs` (`ol.o_portal_submenu` sin cambios) y `portal.portal_layout` (`breadcrumbs_searchbar` sigue soportado).

### Vistas backend (`views/backend_views.xml`)
- Anclas validadas en v19, sin cambios: `l10n_mx_edi_usage` sigue en `group[@name='fiscal_information']` de la ficha del contacto (vista `l10n_mx_edi.l10n_mx_edi_inh_res_partner_form`), `fiscal_country_codes` sigue en la vista, `res.partner.open_commercial_entity` existe, `group[@name='sale_info']` sigue en `sale.view_order_form` y el filtro `my_sale_orders_filter` sigue en `sale.view_sales_order_filter`.

### Controladores (`controllers/main.py`, `controllers/portal.py`)
- No hay rutas `type='json'`: las dos rutas (`/billing` y `/my/billing`) son `type='http'`, así que no aplica el cambio a `type='jsonrpc'`.
- `auth='public'`/`auth='user'` con `website=True`: en v19 el parámetro `readonly` de la ruta sigue siendo `False` por defecto salvo con `auth='none'`, así que las escrituras de los POST siguen funcionando. Los formularios ya mandan `csrf_token`.
- No se usa `request.website`. `CustomerPortal._prepare_portal_layout_values()`, `res.partner.can_edit_vat()` y `account.move.preview_invoice()` existen igual en v19.

### Modelos — métodos del core verificados en v19
- `account.move.send._generate_and_send_invoices(moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings)`: los argumentos que usa el módulo (`sending_methods`, `extra_edis`, `allow_raising`) se siguen aceptando; `sending_methods` sigue validándose contra `res.partner.invoice_sending_method` (`manual`, `email`). `l10n_mx_edi/models/account_move_send.py` es idéntico en 18 y 19 (la EDI sigue llamándose `mx_cfdi`).
- `l10n_mx_edi_cfdi_state` sigue teniendo el valor `sent`, y el estado `invoice_sent_failed` de `l10n_mx_edi.document` y `l10n_mx_edi_invoice_document_ids` siguen existiendo.
- `l10n_mx_edi_sale` en v19: `sale.order` mantiene `l10n_mx_edi_cfdi_to_public`, `l10n_mx_edi_payment_method_id` y `l10n_mx_edi_usage`. Agrega `l10n_mx_edi_payment_policy` (PUE/PPD, calculado desde el cliente y propagado a la factura); `/billing` no lo escribe, así que la factura toma el valor por defecto del cliente.
- `sale.order._create_invoices(grouped=False, final=False, date=None)`, `stock.picking._action_done()`, `ir.cron._trigger(at=...)` y `odoo.modules.module.current_test` sin cambios de firma.
- `models/sale_order.py` (`_cron_selfbilling_auto_invoice`): `ir.cron._notify_progress(done=, remaining=)` → `ir.cron._commit_progress(done, remaining=remaining)`. En v19 `_notify_progress` está marcado `@api.deprecated("Since 19.0, use _commit_progress")` y en las pruebas emitía un `DeprecationWarning`. `_commit_progress` suma `processed` al `done` de la ejecución actual (que empieza en 0), fija `remaining` y hace commit. Fuera de un cron sólo hace commit. Para respetar la regla del módulo de no hacer commit en pruebas, la llamada va dentro de `if not _in_test()`, igual que `_selfbilling_commit()`. Dentro de una prueba no hay progreso de cron, así que `_notify_progress` tampoco hacía nada ahí.

### Pruebas
- `tests/test_auto_invoice_mx.py`: `sale.order.line` `'tax_id'` → `'tax_ids'`. El campo se renombró en v19.
- `tests/common.py` (`SelfBillingCommon`) y `tests/test_auto_invoice_mx.py` (`TestAutoInvoiceMx`): se agregó `get_default_groups()` con `sales_team.group_sale_salesman`. **Por qué:** en v19 `BaseCommon.get_default_groups()` devuelve sólo `base.group_user`; en v18 devolvía `res.users._default_groups()`, que incluía Ventas. El usuario de prueba de `AccountTestInvoicingCommon` se quedó sin permiso para crear `sale.order`, y 10 de las 23 pruebas fallaban con `AccessError: You are not allowed to create 'Sales Order'`. Es un cambio del entorno de pruebas, no del comportamiento del módulo: las aserciones no se tocaron. `l10n_mx_edi_sale` hace lo mismo en sus pruebas de v19 (`cls.env.user.group_ids |= sales_team.group_sale_salesman`).

### Patrones de v19 no encontrados
- No hay `odoo.osv.expression`, `_sql_constraints`, `._cr`/`._uid`/`._context` (los aciertos del grep son `._create_invoices` y `._cron_…`), `auto_join=`, `res.groups`, `target='inline'`, vistas de ajustes, `web_icon`, `ormcache_context`, `pytz.timezone` ni `url_join`/`urljoin`.
- No se usa `res.partner.mobile` (eliminado en v19); los formularios sólo usan `phone`.

### Descripción (`static/description/index.html`)
- «Odoo 18 Enterprise» → «Odoo 19 Enterprise», «Odoo 18.0 Enterprise» → «Odoo 19.0 Enterprise» y «Version 18.0» → «Version 19.0». No se tocaron el copyright, los precios ni las URLs.

## Decisiones

- El grep de v13 encuentra `binding_view_types`, que es un falso positivo de `view_type`. El grep de v18 encuentra la palabra `street` dentro de comentarios, que también es un falso positivo de `tree`.
- `controllers/main.py` conserva el controlador POS comentado de 18, con su `super(SenSelfBillingPosController, self)` y su `print()`. Es código muerto y no se migró.
- `views/billing_tmpl.xml` sigue usando `t-esc` en QWeb del servidor. Es válido en v19 (sólo deja de funcionar en v20), así que se dejó igual.
- La imagen decorativa del paso 1 de `/billing` apunta a `/es_MX/web_editor/image_shape/website.s_text_image_default_image/web_editor/pattern/pattern_points_1.svg`. En v19 `html_editor` conserva la ruta `/web_editor/image_shape/...` por compatibilidad, pero la forma `pattern/pattern_points_1.svg` no existe ni en 18 (`web_editor`) ni en 19 (`html_builder`): ya estaba rota en 18 y no es un tema de esta migración. Se deja igual.

## Verificación

```bash
cd /tmp/odoo19-port && docker compose exec -T odoo odoo \
  --addons-path=/mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons \
  --db_host=db --db_user=odoo --db_password=odoo -d t_selfbill2 \
  -i sen_selfbilling --test-tags /sen_selfbilling --stop-after-init \
  --http-port=18473 --gevent-port=18474 --without-demo=all
```

**Resultado (2026-11-18), instalación desde cero en la base `t_selfbill2` (Odoo `19.0-20260421` + Enterprise):**

```
odoo.modules.loading: Module sen_selfbilling loaded in 0.32s, 362 queries (+362 other)
odoo.modules.loading: Modules loaded.
odoo.tests.stats: sen_selfbilling: 31 tests 12.62s 16587 queries
odoo.tests.result: 0 failed, 0 error(s) of 23 tests when loading database 't_selfbill2'
```

`ir_module_module`: `sen_selfbilling | installed | 19.0.1.5.0`. No hay `WARNING` ni `ERROR` de `sen_selfbilling` en el log. El aviso de docutils `<string>:38: (ERROR/3) Unexpected indentation` sale al cargar el módulo `mail` del core, no de este módulo.

Nota: en este contenedor `--no-http` no basta (el arranque de pruebas intenta abrir el 8069, que ya está ocupado), así que se usan `--http-port`/`--gevent-port` propios.

**Lo que no prueban los tests:** el timbrado contra un PAC real (las pruebas simulan el PAC con `with_mocked_pac_sign_success/error` de `l10n_mx_edi` y, en `SelfBillingCommon`, simulan `_generate_and_send_invoices`); el flujo completo de `/billing` (folio → datos fiscales → factura); los conectores de Mercado Libre, Amazon y Yuju, que no están instalados (`_folio_domain` sólo usa sus campos si existen); y la ejecución real del cron con `_commit_progress` dentro de un worker.

## TODO_AI (Human Review Required)

En la migración 18→19 no hubo elementos `# TODO_AI:`. Los de v19→v20 están en su propia sección, arriba.

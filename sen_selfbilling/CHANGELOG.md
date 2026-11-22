# Changelog — sen_selfbilling

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

No hay elementos `# TODO_AI:`: `grep -rn TODO_AI .` no devuelve nada.

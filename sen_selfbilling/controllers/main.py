from odoo import http, _
# from odoo.addons.point_of_sale.controllers.main import PosController
from odoo.tools import format_amount
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

import re

import logging
_logger = logging.getLogger(__name__)

class SenSelfBillingController(CustomerPortal):
    
    def generate_folio(self, folio: str):
        _folio = folio
        if len(str(folio).split('-')) == 3:
            # Amazon Order Id: 701-4901486-0632218
            pass
        elif len(folio) == 17:
            # Amazon Order Id: 70149014860632218 to  701-4901486-0632218
            _folio = f"{folio[0:3]}-{folio[3:10]}-{folio[10:]}"
        return _folio

    def _folio_domain(self, folio):
        """Ventas que responden a un folio de cliente.

        Cada conector guarda la referencia del marketplace en su propio campo y
        no todos están instalados (Yuju ya no lo está): sólo se buscan los
        campos que existen, para que el dominio nunca sea inválido.
        """
        fields = request.env['sale.order']._fields
        domain = [('name', '=', folio)]
        for field in ('meli_reference', 'amazon_order_ref', 'channel_order_id'):
            if field in fields:
                domain = ['|', (field, '=', folio)] + domain
        if 'meli_order_ids' in fields and folio.isdigit() and len(folio) >= 10:
            # Un carrito de Mercado Libre agrupa varias órdenes en una venta.
            domain = ['|', ('meli_order_ids', 'ilike', folio)] + domain
        return domain

    def _invoice_is_stamped(self, invoice):
        return invoice._selfbilling_is_stamped()

    def _stamp_invoices(self, invoices):
        """Genera el CFDI y el PDF de las facturas publicadas sin timbrar
        (flujo "Enviar e imprimir" sin correo). Devuelve los errores del PAC."""
        return invoices._selfbilling_stamp()

    @http.route(['/billing'], type='http', auth="public", website=True, sitemap=False)
    def billing(self, **kwargs):
        message_error = None
        step = kwargs.get('step','get-started')
        sale_order = None
        partner = None
        payment_methods = []
        rfc = None
        _logger.info(kwargs)
        try:
            if step == 'validate-folio' and kwargs and request.httprequest.method == 'POST':                        
                folio = kwargs.get("folio", "")
                folio = self.generate_folio(folio)
                sale_order = request.env['sale.order'].sudo().search(self._folio_domain(folio), limit=1)
                if not sale_order: 
                    _logger.info(f"Folio inválido #{folio}")
                    raise Exception(f"Folio inválido #{folio}")
                
                posted_invoices = sale_order.invoice_ids.filtered(lambda m: m.state == 'posted')
                if posted_invoices and all(self._invoice_is_stamped(m) for m in posted_invoices):
                    for invoice in posted_invoices:
                        res = invoice.preview_invoice()
                        return request.redirect(res.get("url", '/my'))
                if sale_order.state == 'draft':
                    _logger.info('La orden de venta existe, pero no ha sido confirmada para poder facturarla')
                    raise Exception('La orden de venta existe, pero no ha sido confirmada para poder facturarla')                   

                if len(sale_order.picking_ids.filtered(
                        lambda p: p.state != 'done'
                    )):
                    _logger.info('La orden de venta existe, pero no ha sido despachada para poder facturarla.')
                    raise Exception('La orden de venta existe, pero no ha sido despachada para poder facturarla.')     
                
                rfc = str(kwargs.get("rfc", "")).strip().upper()
                if not re.match(r"^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))([A-Z\d]{3})?$", rfc):
                    raise Exception(f"RFC inválido {rfc}")                
                partner = request.env['res.partner'].sudo().search([('vat', '=', rfc)], limit=1)
                payment_methods = request.env['l10n_mx_edi.payment.method'].sudo().search([])
                step = 'partner-address'
            elif step == 'self-billing' and kwargs and request.httprequest.method == 'POST':                        
                sale_id = int(kwargs.get('sale_id', '0'))
                
                sale_order = request.env['sale.order'].sudo().search([('id', '=', sale_id)], limit=1)
                if not sale_order:
                    raise Exception(f"Ocurrio un error al obtener los detalles de la venta, intente más tarde.")
                partner_id = int(kwargs.get("partner_id", '0') or '0') # 232
                rfc = kwargs.get("rfc", '')
                partner_name = str(kwargs.get("partner_name", '')).strip().upper() # 
                partner_zip_code= kwargs.get("partner_zip_code", '') # 41071
                partner_fiscal_regime = kwargs.get("partner_fiscal_regime", '601') # '621'
                partner_payment_method = int(kwargs.get("partner_payment_method", '1')) # '3'
                partner_use_cfdi = kwargs.get("partner_use_cfdi", 'G03') # '04'
                partner_phone = kwargs.get("partner_phone", None) or None
                partner_email = kwargs.get("partner_email", None) or None
                
                
                partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)], limit=1)
                
                if not len(partner):
                    partner = request.env['res.partner'].sudo().create({
                        "name": partner_name,
                        "zip": partner_zip_code,
                        "vat": rfc,
                        "l10n_mx_edi_fiscal_regime": partner_fiscal_regime
                    })
                else:
                    _update = {}
                    if partner.name != partner_name: 
                        _update.update({"name":partner_name })
                    if partner.zip != partner_zip_code: 
                        _update.update({"zip":partner_zip_code })
                    if partner.l10n_mx_edi_fiscal_regime != partner_fiscal_regime:
                        _update.update({"l10n_mx_edi_fiscal_regime":partner_fiscal_regime })
                    if partner_phone and partner.phone != partner_phone:
                        _update.update({"phone":partner_phone })
                    if partner_email and partner.email != partner_email:
                        _update.update({"email":partner_email })
                    if partner.l10n_mx_edi_usage != partner_use_cfdi:
                        _update.update({"l10n_mx_edi_usage":partner_use_cfdi })
                    if len(_update.keys()):
                        partner.write(_update)
                
                if sale_order.partner_invoice_id.id != partner.id \
                    or sale_order.l10n_mx_edi_usage != partner_use_cfdi \
                    or sale_order.l10n_mx_edi_payment_method_id.id != partner_payment_method:
                    sale_order.write({
                        'l10n_mx_edi_payment_method_id': partner_payment_method,
                        'partner_invoice_id': partner.id,
                        'l10n_mx_edi_usage': partner_use_cfdi,
                    })
                    
                if not sale_order.invoice_ids:
                    # Si falla la publicación no debe quedar un borrador que bloquee el reintento.
                    with request.env.cr.savepoint():
                        invoice = sale_order._create_invoices()
                        _logger.info("created invoices invoice_ids:" + str(sale_order.invoice_ids))
                        invoice.sudo()._post()

                posted_invoices = sale_order.invoice_ids.filtered(lambda m: m.state == 'posted')
                if not posted_invoices:
                    raise Exception("La factura no pudo generarse, intente más tarde")

                errors = self._stamp_invoices(posted_invoices)
                if errors:
                    raise Exception(" ".join(errors))

                for invoice in posted_invoices:
                    res = invoice.preview_invoice()
                    return request.redirect(res.get("url", '/my'))
        except Exception as e:
            _logger.error(e)            
            message_error = str(e)
        
        data = {
            "step": step,
            "rfc": rfc,
            "partner": partner,
            "sale_order": sale_order,           
            "message_error": message_error,
            "payment_methods": payment_methods,
            # /billing?folio=… precarga el folio (link que se manda al comprador).
            "folio": str(kwargs.get("folio") or "").strip()[:40],
        }
        return request.render("sen_selfbilling.portal_selfbilling", data)

    
    
#class SenSelfBillingPosController(PosController):
#
#    @http.route(['/pos/ticket/validate'], type='http', auth="public", website=True, sitemap=False)
#    def show_ticket_validation_screen(self, access_token='', step='1', **kwargs):
#        self.MANDATORY_BILLING_FIELDS = ["name", "zipcode", "email",  "vat"] + ['regimen_fiscal_id','forma_pago_id','methodo_pago','uso_cfdi_id']
#        self.OPTIONAL_BILLING_FIELDS = [ "state_id", "street", "phone",  "city",  "company_name", "country_id", 'tipo_comprobante']
#        def _parse_additional_values(fields, prefix, kwargs):
#            """ Parse the values in the kwargs by extracting the ones matching the given fields name.
#            :return a dict with the parsed value and the field name as key, and another on with the prefix to
#            re-render the form with previous values if needed.
#            """
#            res, res_prefixed = {}, {}
#            for field in fields:
#                key = prefix + field.name
#                if key in kwargs:
#                    val = kwargs.pop(key)
#                    res[field.name] = val
#                    res_prefixed[key] = val
#            return res, res_prefixed
#
#        # If the route is called directly, return a 404
#        if not access_token:
#            return request.not_found()
#        # Get the order using the access token. We can't use the id in the route because we may not have it yet when the QR code is generated.
#        pos_order = request.env['pos.order'].sudo().search([('access_token', '=', access_token)])
#        if not pos_order:
#            return request.not_found()
#
#        # If the order was already invoiced, return the invoice directly by forcing the access token so that the non-connected user can see it.
#        if pos_order.account_move and pos_order.account_move.is_sale_document():
#            return request.redirect('/my/invoices/%s?access_token=%s' % (pos_order.account_move.id, pos_order.account_move._portal_ensure_token()))
#
#        # Get the optional extra fields that could be required for a localisation.
#        pos_order_country = pos_order.company_id.account_fiscal_country_id
#        additional_partner_fields = request.env['res.partner'].get_partner_localisation_fields_required_to_invoice(pos_order_country)
#        additional_invoice_fields = request.env['account.move'].get_invoice_localisation_fields_required_to_invoice(pos_order_country)
#
#        user_is_connected = not request.env.user._is_public()
#
#        metodo_pagos = [{"id": "PUE", "name": "Pago en una sola exhibición"}, {"id": "PPD", "name": "Pago en parcialidades y diferidos"}]
#
#        forma_pagos = request.env['catalogo.forma.pago'].sudo().search([])
#        uso_cfdis = request.env['catalogo.uso.cfdi'].sudo().search([])
#        regimenes_fiscal = request.env['catalogo.regimen.fiscal'].sudo().search([])
#
#
#
#        partner = request.env['res.partner']
#
#        # Validate the form by ensuring required fields are filled and the VAT is correct.
#        form_values = {'error': {}, 'error_message': {}, 'extra_field_values': {}}
#        
#        if step == '3' and kwargs and request.httprequest.method == 'POST':                        
#            form_values.update(kwargs)
#            # Extract the additional fields values from the kwargs now as they can't be there when validating the 'regular' partner form.
#            partner_values, prefixed_partner_values = _parse_additional_values(additional_partner_fields, 'partner_', kwargs)
#            form_values['extra_field_values'].update(prefixed_partner_values)
#            # Do the same for invoice values, separately as they are only needed for the invoice creation.
#            invoice_values, prefixed_invoice_values = _parse_additional_values(additional_invoice_fields, 'invoice_', kwargs)
#            form_values['extra_field_values'].update(prefixed_invoice_values)
#            # Check the basic form fields if the user is not connected as we will need these information to create the new user.
#            print('user_is_connected', user_is_connected)
#            if not user_is_connected:
#                error, error_message = self.details_form_validate(kwargs, partner_creation=True)
#            else:
#                # Check that the billing information of the user are filled.
#                error, error_message = {}, []
#                partner = request.env.user.partner_id
#                for field in self.MANDATORY_BILLING_FIELDS:
#                    if not partner[field]:
#                        error[field] = 'error'
#                        error_message.append(_('The %s must be filled in your details.', request.env['ir.model.fields']._get('res.partner', field).field_description))
#            # Check that the "optional" additional fields are filled.
#            error, error_message = self.extra_details_form_validate(partner_values, additional_partner_fields, error, error_message)
#            error, error_message = self.extra_details_form_validate(invoice_values, additional_invoice_fields, error, error_message)            
#            
#            if not error:
#                partner_values.update({ 
#                    'regimen_fiscal_id': int( form_values.get('regimen_fiscal_id')) ,
#                    'uso_cfdi_id': int( form_values.get('uso_cfdi_id'))
#                })
#                invoice_values.update({
#                    'forma_pago_id': int(form_values.get('forma_pago_id')),
#                    'uso_cfdi_id': int(form_values.get('uso_cfdi_id')),
#                    'methodo_pago': form_values.get('methodo_pago'),                    
#                    'tipo_comprobante': 'I'
#                }) 
#                
#                class F:
#                    name: str
#                    def __init__(self, name: str):
#                        self.name = name
#                del self.MANDATORY_BILLING_FIELDS[self.MANDATORY_BILLING_FIELDS.index('forma_pago_id')]
#                del self.MANDATORY_BILLING_FIELDS[self.MANDATORY_BILLING_FIELDS.index('methodo_pago')]
#
#                additional_invoice_fields.append(F('forma_pago_id'))
#                additional_invoice_fields.append(F('uso_cfdi_id'))
#                additional_invoice_fields.append(F('methodo_pago'))
#                additional_invoice_fields.append(F('tipo_comprobante'))
#                return self._get_invoice(partner_values, invoice_values, pos_order, additional_invoice_fields, kwargs)
#            else:
#                form_values.update({'error': error, 'error_message': error_message})
#                step = '2'
#        elif step == '2' and request.httprequest.method == 'POST':            
#            if not kwargs.get('rfc', None):            
#                form_values.update({ 'error':  { 'rfc': 'error'}})
#                step = '1'
#            else:
#                rfc = str(kwargs.get('rfc')).strip()
#                pos_order.partner_id = partner.sudo().search([('vat','=', rfc)], limit=1)
#
#        #elif user_is_connected:
#        #    return self._get_invoice({}, {}, pos_order, additional_invoice_fields, kwargs)
#
#        # Most of the time, the country of the customer will be the same as the order. We can prefill it by default with the country of the company.
#        if 'country_id' not in form_values:
#            form_values['country_id'] = pos_order_country.id
#
#        
#        # Prefill the customer extra values if there is any and an user is connected
#        partner = (user_is_connected and request.env.user.partner_id) or pos_order.partner_id
#        if partner:
#            if additional_partner_fields:
#                form_values['extra_field_values'] = {'partner_' + field.name: partner[field.name] for field in additional_partner_fields if field.name not in form_values['extra_field_values']}
#
#            # This is just to ensure that the user went and filled its information at least once.
#            # Another more thorough check is done upon posting the form.
#            if not partner.country_id or not partner.street:
#                form_values['partner_address'] = False
#            else:
#                form_values['partner_address'] = partner._display_address()
#        
#        return request.render("sen_selfbilling.ticket_validation_screen", {
#            'partner': partner,
#            'address_url': f'/my/account?redirect=/pos/ticket/validate?access_token={access_token}',
#            'user_is_connected': user_is_connected,
#            'format_amount': format_amount,
#            'env': request.env,
#            'countries': request.env['res.country'].sudo().search([]),
#            'states': request.env['res.country.state'].sudo().search([]),
#            'partner_can_edit_vat':  True,
#            'pos_order': pos_order,
#            'invoice_required_fields': additional_invoice_fields,
#            'partner_required_fields': additional_partner_fields,
#            'access_token': access_token,
#            'step': step,
#            'metodo_pagos':metodo_pagos,
#            'forma_pagos':forma_pagos,
#            'uso_cfdis':uso_cfdis,
#            'regimenes_fiscal': regimenes_fiscal,
#            **form_values,
#        })
#        #return super(SenSelfBillingPosController, self).show_ticket_validation_screen(access_token, **kwargs)
from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.sen_selfbilling.models.res_partner import CFDI_USAGES, FISCAL_REGIMES

from .main import SenSelfBillingController

FISCAL_FIELDS = ('vat', 'name', 'zip', 'l10n_mx_edi_fiscal_regime', 'l10n_mx_edi_usage')


class SelfBillingPortal(SenSelfBillingController):

    def _selfbilling_partner(self):
        """Los datos fiscales son de la empresa (contacto comercial) del usuario."""
        return request.env.user.partner_id.commercial_partner_id.sudo()

    @http.route(['/my/billing'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_my_billing(self, **post):
        partner = self._selfbilling_partner()
        can_edit_vat = partner._selfbilling_can_edit_vat()
        errors = {}
        data = {field: partner[field] or '' for field in FISCAL_FIELDS}
        auto = partner.selfbilling_auto
        if request.httprequest.method == 'POST':
            data = {
                'vat': (post.get('vat') or '').strip().upper() if can_edit_vat else (partner.vat or ''),
                'name': ' '.join((post.get('name') or '').split()).upper(),
                'zip': (post.get('zip') or '').strip(),
                'l10n_mx_edi_fiscal_regime': post.get('l10n_mx_edi_fiscal_regime') or '',
                'l10n_mx_edi_usage': post.get('l10n_mx_edi_usage') or '',
            }
            auto = bool(post.get('selfbilling_auto'))
            errors = partner._selfbilling_check_fiscal_data(data)
            if not errors:
                vals = dict(data, selfbilling_auto=auto)
                if not can_edit_vat:
                    vals.pop('vat')
                if not partner.country_id:
                    vals['country_id'] = request.env.ref('base.mx').id
                try:
                    with request.env.cr.savepoint():
                        partner.write(vals)
                except (UserError, ValidationError) as exc:
                    errors['vat'] = exc.args[0] if exc.args else str(exc)
            if not errors:
                return request.redirect('/my/billing?saved=1')
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'billing',
            'partner': partner,
            'data': data,
            'auto': auto,
            'errors': errors,
            'can_edit_vat': can_edit_vat,
            'saved': bool(post.get('saved')) and request.httprequest.method == 'GET',
            'invoice_email': request.env.user.partner_id.email,
            'fiscal_regimes': [(code, name) for code, name, _f, _m in FISCAL_REGIMES],
            'cfdi_usages': CFDI_USAGES,
        })
        return request.render('sen_selfbilling.portal_my_billing', values)

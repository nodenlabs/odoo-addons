import re

from odoo import _, api, fields, models

RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[A-Z\d]{3}$")
GENERIC_RFCS = ('XAXX010101000', 'XEXX010101000')
ZIP_RE = re.compile(r"^\d{5}$")
# Régimen societario al final de la razón social: el SAT lo pide sin él.
COMPANY_TYPE_RE = re.compile(
    r"[\s,]+(S\.?\s*A\.?\s*P\.?\s*I\.?|S\.?\s*A\.?\s*B\.?|S\.?\s*A\.?|S\.?\s*DE\s*R\.?\s*L\.?|S\.?\s*C\.?|A\.?\s*C\.?|S\.?\s*A\.?\s*S\.?)"
    r"(\s*DE\s*C\.?\s*V\.?)?\.?\s*$"
)

# Catálogo c_RegimenFiscal del SAT: (clave, nombre, física, moral).
FISCAL_REGIMES = [
    ('601', 'General de Ley Personas Morales', False, True),
    ('603', 'Personas Morales con Fines no Lucrativos', False, True),
    ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios', True, False),
    ('606', 'Arrendamiento', True, False),
    ('607', 'Régimen de Enajenación o Adquisición de Bienes', True, False),
    ('608', 'Demás ingresos', True, False),
    ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México', True, True),
    ('611', 'Ingresos por Dividendos (socios y accionistas)', True, False),
    ('612', 'Personas Físicas con Actividades Empresariales y Profesionales', True, False),
    ('614', 'Ingresos por intereses', True, False),
    ('615', 'Régimen de los ingresos por obtención de premios', True, False),
    ('616', 'Sin obligaciones fiscales', True, False),
    ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos', False, True),
    ('621', 'Incorporación Fiscal', True, False),
    ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras', True, True),
    ('623', 'Opcional para Grupos de Sociedades', False, True),
    ('624', 'Coordinados', False, True),
    ('625', 'Actividades Empresariales con ingresos a través de Plataformas Tecnológicas', True, False),
    ('626', 'Régimen Simplificado de Confianza (RESICO)', True, True),
]

# Catálogo c_UsoCFDI (los D sólo aplican a personas físicas).
CFDI_USAGES = [
    ('G01', 'Adquisición de mercancías'),
    ('G02', 'Devoluciones, descuentos o bonificaciones'),
    ('G03', 'Gastos en general'),
    ('I01', 'Construcciones'),
    ('I02', 'Mobiliario y equipo de oficina por inversiones'),
    ('I03', 'Equipo de transporte'),
    ('I04', 'Equipo de cómputo y accesorios'),
    ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
    ('I06', 'Comunicaciones telefónicas'),
    ('I07', 'Comunicaciones satelitales'),
    ('I08', 'Otra maquinaria y equipo'),
    ('D01', 'Honorarios médicos, dentales y gastos hospitalarios'),
    ('D02', 'Gastos médicos por incapacidad o discapacidad'),
    ('D03', 'Gastos funerales'),
    ('D04', 'Donativos'),
    ('D05', 'Intereses reales pagados por créditos hipotecarios (casa habitación)'),
    ('D06', 'Aportaciones voluntarias al SAR'),
    ('D07', 'Primas por seguros de gastos médicos'),
    ('D08', 'Gastos de transportación escolar obligatoria'),
    ('D09', 'Depósitos en cuentas para el ahorro, primas de planes de pensiones'),
    ('D10', 'Pagos por servicios educativos (colegiaturas)'),
    ('S01', 'Sin efectos fiscales'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    selfbilling_auto = fields.Boolean(
        string='Facturación automática',
        copy=False,
        tracking=True,
        help='Al validar la entrega de una venta se factura, se timbra y se envía por '
        'correo con los datos fiscales del cliente, sin que tenga que solicitarla.',
    )
    selfbilling_fiscal_warning = fields.Text(
        string='Datos fiscales incompletos',
        compute='_compute_selfbilling_fiscal_warning',
    )

    @api.depends('selfbilling_auto', 'vat', 'name', 'zip', 'l10n_mx_edi_fiscal_regime', 'l10n_mx_edi_usage')
    def _compute_selfbilling_fiscal_warning(self):
        """Lo que haría fallar la facturación automática, para corregirlo antes de la venta."""
        for partner in self:
            errors = partner._selfbilling_fiscal_errors() if partner.selfbilling_auto else {}
            partner.selfbilling_fiscal_warning = '\n'.join(errors.values()) or False

    @api.model
    def _selfbilling_check_fiscal_data(self, vals):
        """Validar datos fiscales CFDI 4.0. Devuelve {campo: mensaje}."""
        errors = {}
        rfc = (vals.get('vat') or '').strip().upper()
        name = (vals.get('name') or '').strip()
        regime = vals.get('l10n_mx_edi_fiscal_regime') or ''
        usage = vals.get('l10n_mx_edi_usage') or ''
        is_company = len(rfc) == 12
        if not RFC_RE.match(rfc):
            errors['vat'] = _('RFC inválido: 12 caracteres para personas morales y 13 para personas físicas, con homoclave.')
        elif rfc in GENERIC_RFCS:
            errors['vat'] = _('El RFC genérico no se puede usar para facturar a su nombre.')
        if not name:
            errors['name'] = _('Capture su nombre o razón social.')
        elif name != name.upper():
            errors['name'] = _('El nombre debe ir en MAYÚSCULAS, igual que en su Constancia de Situación Fiscal.')
        elif is_company and COMPANY_TYPE_RE.search(name):
            errors['name'] = _('Capture la razón social sin el régimen societario (sin «S.A. DE C.V.», «S. DE R.L.», etc.).')
        if not ZIP_RE.match((vals.get('zip') or '').strip()):
            errors['zip'] = _('El código postal debe tener 5 dígitos, el de su Constancia de Situación Fiscal.')
        regimes = {code: (fisica, moral) for code, _name, fisica, moral in FISCAL_REGIMES}
        if regime not in regimes:
            errors['l10n_mx_edi_fiscal_regime'] = _('Seleccione su régimen fiscal.')
        elif 'vat' not in errors and not regimes[regime][1 if is_company else 0]:
            errors['l10n_mx_edi_fiscal_regime'] = (
                _('Ese régimen no aplica a personas morales.') if is_company
                else _('Ese régimen no aplica a personas físicas.')
            )
        if usage not in dict(CFDI_USAGES):
            errors['l10n_mx_edi_usage'] = _('Seleccione el uso del CFDI.')
        elif is_company and usage.startswith('D'):
            errors['l10n_mx_edi_usage'] = _('Los usos «D» (deducciones personales) sólo aplican a personas físicas.')
        return errors

    def _selfbilling_fiscal_errors(self):
        self.ensure_one()
        partner = self.commercial_partner_id
        return partner._selfbilling_check_fiscal_data({
            'vat': partner.vat,
            'name': partner.name,
            'zip': partner.zip,
            'l10n_mx_edi_fiscal_regime': partner.l10n_mx_edi_fiscal_regime,
            'l10n_mx_edi_usage': partner.l10n_mx_edi_usage,
        })

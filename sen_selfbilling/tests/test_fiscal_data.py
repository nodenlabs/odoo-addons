from odoo.tests import tagged

from .common import VALID, SelfBillingCommon


@tagged('post_install', '-at_install')
class TestFiscalData(SelfBillingCommon):

    def check(self, **changes):
        return self.env['res.partner']._selfbilling_check_fiscal_data(dict(VALID, **changes))

    def test_valid_person(self):
        self.assertEqual(self.check(), {})

    def test_valid_company(self):
        self.assertEqual(self.check(vat='GAC0610269Q5', name='GALACOM', l10n_mx_edi_fiscal_regime='601'), {})

    def test_rfc(self):
        self.assertIn('vat', self.check(vat='GODE561231'), 'Sin homoclave')
        self.assertIn('vat', self.check(vat='XAXX010101000'), 'RFC genérico')
        self.assertIn('vat', self.check(vat='GODE561331GR8'), 'Mes inválido')

    def test_name_uppercase_without_company_type(self):
        self.assertIn('name', self.check(name='Diego Gomez'))
        self.assertIn('name', self.check(vat='GAC0610269Q5', name='GALACOM SA DE CV', l10n_mx_edi_fiscal_regime='601'))
        self.assertIn('name', self.check(vat='GAC0610269Q5', name='GALACOM, S.A. DE C.V.', l10n_mx_edi_fiscal_regime='601'))
        self.assertEqual(self.check(vat='GAC0610269Q5', name='CASA', l10n_mx_edi_fiscal_regime='601'), {},
                         'Una razón social que termina en «SA» como palabra no es régimen societario')

    def test_zip(self):
        self.assertIn('zip', self.check(zip='6400'))

    def test_regime_matches_person_type(self):
        self.assertIn('l10n_mx_edi_fiscal_regime', self.check(l10n_mx_edi_fiscal_regime='601'))
        self.assertIn('l10n_mx_edi_fiscal_regime',
                      self.check(vat='GAC0610269Q5', name='GALACOM', l10n_mx_edi_fiscal_regime='612'))
        self.assertEqual(self.check(l10n_mx_edi_fiscal_regime='626'), {}, 'RESICO aplica a ambas')

    def test_personal_deductions_only_for_persons(self):
        self.assertEqual(self.check(l10n_mx_edi_usage='D01'), {})
        self.assertIn('l10n_mx_edi_usage', self.check(
            vat='GAC0610269Q5', name='GALACOM', l10n_mx_edi_fiscal_regime='601', l10n_mx_edi_usage='D01'))

    def test_backend_warning_only_when_auto_is_on(self):
        partner = self.customer.copy({'name': 'Diego Gomez', 'vat': 'GODE561231GR8'})
        self.assertFalse(partner.selfbilling_fiscal_warning, 'Sin facturación automática no se avisa')

        partner.selfbilling_auto = True
        self.assertIn('MAYÚSCULAS', partner.selfbilling_fiscal_warning)

        partner.name = 'DIEGO GOMEZ'
        self.assertFalse(partner.selfbilling_fiscal_warning)

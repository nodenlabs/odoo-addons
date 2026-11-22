from unittest.mock import patch

from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestPortalBilling(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='portal_sb', groups='base.group_portal',
                                 name='Diego', email='diego@example.com')
        cls.partner = cls.user.partner_id

    def post(self, **data):
        self.authenticate('portal_sb', 'portal_sb')
        page = self.url_open('/my/billing')
        token = page.text.split('name="csrf_token" value="')[1].split('"')[0]
        return self.url_open('/my/billing', data=dict(data, csrf_token=token))

    def test_home_card(self):
        self.authenticate('portal_sb', 'portal_sb')
        page = self.url_open('/my/home')
        self.assertIn('/my/billing', page.text)
        self.assertIn('Inactiva', page.text)

    def test_page_shows_sat_requirements(self):
        self.authenticate('portal_sb', 'portal_sb')
        page = self.url_open('/my/billing')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Constancia de Situación Fiscal', page.text)
        self.assertIn('Facturación automática', page.text)

    def test_save_fiscal_data_and_enable(self):
        res = self.post(vat='gode561231gr8', name='diego  gomez', zip='64000',
                        l10n_mx_edi_fiscal_regime='612', l10n_mx_edi_usage='G03', selfbilling_auto='1')
        self.assertIn('se guardaron', res.text)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.vat, 'GODE561231GR8')
        self.assertEqual(self.partner.name, 'DIEGO GOMEZ', 'Se pasa a mayúsculas')
        self.assertEqual(self.partner.l10n_mx_edi_fiscal_regime, '612')
        self.assertTrue(self.partner.selfbilling_auto)

    def test_invalid_data_is_not_saved(self):
        res = self.post(vat='GODE561231GR8', name='DIEGO', zip='640',
                        l10n_mx_edi_fiscal_regime='601', l10n_mx_edi_usage='G03', selfbilling_auto='1')
        self.assertIn('is-invalid', res.text)
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.selfbilling_auto)
        self.assertNotEqual(self.partner.zip, '640')

    def test_rfc_locked_after_invoices(self):
        self.partner.write({'vat': 'GODE561231GR8'})
        # v20: can_edit_vat() ya no existe; el core usa _has_confirmed_documents(),
        # que es True cuando el cliente ya tiene facturas emitidas.
        with patch.object(type(self.env['res.partner']), '_has_confirmed_documents', lambda self: True):
            res = self.post(vat='OTRA561231GR8', name='DIEGO GOMEZ', zip='64000',
                            l10n_mx_edi_fiscal_regime='612', l10n_mx_edi_usage='G03')
        self.assertIn('se guardaron', res.text)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.vat, 'GODE561231GR8', 'El RFC no cambia si ya hay facturas')
        self.assertEqual(self.partner.zip, '64000')


@tagged('post_install', '-at_install')
class TestPublicBilling(HttpCase):

    def test_invalid_folio_message_is_rendered(self):
        # v20: t-esc ya no se renderiza en QWeb del servidor; el error debe verse en /billing.
        page = self.url_open('/billing?folio=NOEXISTE-123')
        self.assertEqual(page.status_code, 200)
        self.assertIn('value="NOEXISTE-123"', page.text, 'El folio del link se precarga')
        token = page.text.split('name="csrf_token" value="')[1].split('"')[0]
        with mute_logger('odoo.addons.sen_selfbilling.controllers.main'):
            res = self.url_open('/billing', data={
                'csrf_token': token, 'step': 'validate-folio', 'folio': 'NOEXISTE-123', 'rfc': 'GODE561231GR8',
            })
        self.assertEqual(res.status_code, 200)
        self.assertIn('Folio inválido #NOEXISTE-123', res.text)

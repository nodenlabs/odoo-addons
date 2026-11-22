
from odoo.tests import tagged

from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAutoInvoiceMx(TestMxEdiCommon):
    """Flujo completo con l10n_mx_edi real: se genera el CFDI y sólo se simula el PAC."""

    @classmethod
    def get_default_groups(cls):
        # v19: el usuario de prueba ya no recibe los grupos por defecto de
        # res.users (sólo base.group_user); las ventas necesitan este grupo.
        return super().get_default_groups() | cls.env.ref('sales_team.group_sale_salesman')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'name': 'INMOBILIARIA CVA',
            'vat': 'ICV060329BY0',
            'zip': '33826',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_chih').id,
            'l10n_mx_edi_fiscal_regime': '601',
            'l10n_mx_edi_usage': 'G01',
            'email': 'facturas@cva.example.com',
            'selfbilling_auto': True,
        })
        cls.product.write({'is_storable': True, 'invoice_policy': 'delivery'})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.env['stock.quant']._update_available_quantity(cls.product, cls.warehouse.lot_stock_id, 10)

    def sell_and_deliver(self):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 2, 'price_unit': 1000.0,
                                   'tax_ids': [(6, 0, self.tax_16.ids)]})],
        })
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        return order

    def test_delivery_creates_signed_cfdi_and_emails_it(self):
        with self.mx_external_setup(self.frozen_today), self.with_mocked_pac_sign_success():
            order = self.sell_and_deliver()
            self.assertEqual(order.selfbilling_auto_state, 'pending')
            self.env['sale.order']._cron_selfbilling_auto_invoice()
        invoice = order.invoice_ids
        self.assertEqual(order.selfbilling_auto_state, 'done', order.selfbilling_auto_info)
        self.assertEqual(invoice.l10n_mx_edi_cfdi_state, 'sent')
        self.assertTrue(invoice.l10n_mx_edi_cfdi_uuid)
        self.assertTrue(invoice.l10n_mx_edi_cfdi_attachment_id)
        self.assertEqual(invoice.l10n_mx_edi_usage, 'G01', 'Uso del CFDI elegido por el cliente')
        self.assertEqual(invoice.amount_total, 2320.0)
        mail = self.env['mail.message'].search([
            ('model', '=', 'account.move'), ('res_id', '=', invoice.id),
            ('partner_ids', 'in', self.customer.ids),
        ])
        self.assertTrue(mail, 'La factura se envía por correo al cliente')
        self.assertIn(invoice.l10n_mx_edi_cfdi_attachment_id.name, mail.attachment_ids.mapped('name'))

    def test_pac_error_keeps_posted_invoice_and_retries(self):
        with self.mx_external_setup(self.frozen_today), self.with_mocked_pac_sign_error():
            order = self.sell_and_deliver()
            self.env['sale.order']._cron_selfbilling_auto_invoice()
        self.assertEqual(order.selfbilling_auto_state, 'pending')
        self.assertEqual(order.selfbilling_auto_attempts, 1)
        self.assertIn('turlututu', order.selfbilling_auto_info, 'El motivo del PAC queda en la venta')
        self.assertEqual(order.invoice_ids.state, 'posted')
        self.assertFalse(order.invoice_ids.l10n_mx_edi_cfdi_state)
        with self.mx_external_setup(self.frozen_today), self.with_mocked_pac_sign_success():
            order.action_selfbilling_auto_invoice()
        self.assertEqual(order.selfbilling_auto_state, 'done')
        self.assertEqual(len(order.invoice_ids), 1, 'Se timbra la misma factura, no otra')
        self.assertEqual(order.invoice_ids.l10n_mx_edi_cfdi_state, 'sent')

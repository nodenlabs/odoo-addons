from odoo.tests import tagged

from .common import VALID, SelfBillingCommon


@tagged('post_install', '-at_install')
class TestAutoInvoice(SelfBillingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer.selfbilling_auto = True

    def run_cron(self):
        self.env['sale.order']._cron_selfbilling_auto_invoice()

    def test_delivery_invoices_stamps_and_emails(self):
        order = self.make_sale()
        self.assertFalse(order.selfbilling_auto_state)
        self.deliver(order)
        self.assertEqual(order.selfbilling_auto_state, 'pending')
        self.run_cron()
        invoice = order.invoice_ids
        self.assertEqual(order.selfbilling_auto_state, 'done', order.selfbilling_auto_info)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_mx_edi_cfdi_state, 'sent')
        self.assertEqual(self.sent[0][1]['sending_methods'], ['email'])
        self.assertEqual(self.sent[0][1]['extra_edis'], ['mx_cfdi'])
        self.assertEqual(order.l10n_mx_edi_usage, 'G03', 'El uso del CFDI viene del cliente')

    def test_partial_deliveries_invoice_each_part(self):
        order = self.make_sale(qty=3)
        self.deliver(order, qty=1)
        self.run_cron()
        self.assertEqual(order.invoice_ids.invoice_line_ids.quantity, 1)
        self.deliver(order)
        self.run_cron()
        self.assertEqual(len(order.invoice_ids), 2)
        self.assertEqual(sum(order.invoice_ids.invoice_line_ids.mapped('quantity')), 3)
        self.assertTrue(all(m.l10n_mx_edi_cfdi_state == 'sent' for m in order.invoice_ids))

    def test_customer_without_flag_is_not_invoiced(self):
        other = self.env['res.partner'].create(dict(VALID, email='otro@example.com'))
        order = self.make_sale(other)
        self.deliver(order)
        self.assertFalse(order.selfbilling_auto_state)
        self.assertFalse(order.invoice_ids)

    def test_incomplete_fiscal_data_is_an_error_without_invoice(self):
        self.customer.zip = False
        order = self.make_sale()
        self.deliver(order)
        self.run_cron()
        self.assertEqual(order.selfbilling_auto_state, 'error')
        self.assertIn('código postal', order.selfbilling_auto_info)
        self.assertFalse(order.invoice_ids, 'Sin datos fiscales no se crea la factura')

    def test_pac_rejection_retries_then_fails(self):
        self.stamp_fails = True
        order = self.make_sale()
        self.deliver(order)
        self.run_cron()
        self.assertEqual(order.selfbilling_auto_state, 'pending')
        self.assertEqual(order.selfbilling_auto_attempts, 1)
        self.assertTrue(order.selfbilling_auto_retry_at)
        self.assertEqual(order.invoice_ids.state, 'posted', 'La factura publicada se conserva')
        for _attempt in range(2):
            order.selfbilling_auto_retry_at = False
            self.run_cron()
        self.assertEqual(order.selfbilling_auto_state, 'error')
        self.assertEqual(len(order.invoice_ids), 1, 'Los reintentos timbran la misma factura')
        # Corregido el problema, se reintenta a mano.
        self.stamp_fails = False
        order.action_selfbilling_auto_invoice()
        self.assertEqual(order.selfbilling_auto_state, 'done')

    def test_cfdi_to_public_is_skipped(self):
        order = self.make_sale()
        order.l10n_mx_edi_cfdi_to_public = True
        self.deliver(order)
        self.run_cron()
        self.assertEqual(order.selfbilling_auto_state, 'skipped')
        self.assertFalse(order.invoice_ids)

    def test_draft_invoice_blocks(self):
        order = self.make_sale()
        self.deliver(order)
        order._create_invoices()
        self.run_cron()
        self.assertEqual(order.selfbilling_auto_state, 'error')

    def test_manual_action_works_without_flag(self):
        other = self.env['res.partner'].create(dict(VALID, email='otro@example.com'))
        order = self.make_sale(other)
        self.deliver(order)
        order.action_selfbilling_auto_invoice()
        self.assertEqual(order.selfbilling_auto_state, 'done')

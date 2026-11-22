from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

SEND_TARGET = 'odoo.addons.account.models.account_move_send.AccountMoveSend._generate_and_send_invoices'

VALID = {
    'vat': 'GODE561231GR8',
    'name': 'DIEGO GOMEZ',
    'zip': '64000',
    'l10n_mx_edi_fiscal_regime': '612',
    'l10n_mx_edi_usage': 'G03',
}


class SelfBillingCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.customer = cls.env['res.partner'].create(dict(
            VALID, email='diego@example.com', country_id=cls.env.ref('base.mx').id,
        ))
        cls.storable = cls.env['product.product'].create({
            'name': 'Molino', 'is_storable': True, 'invoice_policy': 'delivery',
            'list_price': 100.0, 'taxes_id': [(6, 0, [])],
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.env['stock.quant']._update_available_quantity(cls.storable, cls.warehouse.lot_stock_id, 50)

    def setUp(self):
        super().setUp()
        self.sent = []
        self.stamp_fails = False

        def fake_send(send, moves, **kwargs):
            self.sent.append((moves, kwargs))
            if self.stamp_fails:
                return self.env['ir.attachment']
            moves.l10n_mx_edi_cfdi_state = 'sent'
            return self.env['ir.attachment']

        patcher = patch(SEND_TARGET, autospec=True, side_effect=fake_send)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_sale(self, partner=None, qty=2):
        order = self.env['sale.order'].create({
            'partner_id': (partner or self.customer).id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {'product_id': self.storable.id, 'product_uom_qty': qty})],
        })
        order.action_confirm()
        return order

    def deliver(self, order, qty=None):
        picking = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = qty if qty is not None else move.product_uom_qty
        picking.move_ids.picked = True
        res = picking.button_validate()
        if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            self.env['stock.backorder.confirmation'].with_context(res['context']).create({}).process()
        return picking

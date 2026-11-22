from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        # Sólo la salida al cliente: en entregas de varios pasos el picking y el
        # empaque no cuentan, y las devoluciones son de entrada.
        self.filtered(
            lambda p: p.state == 'done' and p.picking_type_code == 'outgoing' and p.sale_id
        ).sale_id._selfbilling_queue_auto_invoice()
        return res

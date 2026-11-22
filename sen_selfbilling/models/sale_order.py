"""Facturación automática.

Si el cliente activó «Facturación automática» en el portal, al validar la
entrega de su venta se factura lo entregado, se timbra y se le manda por
correo. No se hace dentro de la validación: la venta queda pendiente y un cron
la procesa después del commit, así un fallo del PAC no deshace la entrega.
"""
import logging
import time
from datetime import timedelta

import odoo
from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

CRON_AUTO_INVOICE = 'sen_selfbilling.ir_cron_selfbilling_auto_invoice'
AUTO_BATCH = 10
AUTO_TIME_BUDGET = 120
AUTO_MAX_ATTEMPTS = 3
AUTO_RETRY_DELAY = timedelta(minutes=30)
AUTO_DEBOUNCE = timedelta(seconds=30)

AUTO_STATES = [
    ('pending', 'Pendiente'),
    ('done', 'Facturada'),
    ('skipped', 'Omitida'),
    ('error', 'Error'),
]


def _in_test():
    return bool(odoo.modules.module.current_test)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    selfbilling_auto_state = fields.Selection(
        AUTO_STATES, string='Facturación automática', copy=False, readonly=True, index=True,
    )
    selfbilling_auto_info = fields.Text(string='Detalle de facturación automática', copy=False, readonly=True)
    selfbilling_auto_attempts = fields.Integer(copy=False, readonly=True)
    selfbilling_auto_retry_at = fields.Datetime(copy=False, readonly=True)

    # ── Cola ───────────────────────────────────────────────────────────

    def _selfbilling_auto_partner(self):
        self.ensure_one()
        return self.partner_invoice_id.commercial_partner_id

    def _selfbilling_queue_auto_invoice(self):
        """Dejar pendientes las ventas de clientes con facturación automática."""
        orders = self.sudo().filtered(
            lambda o: o.state == 'sale' and o._selfbilling_auto_partner().selfbilling_auto
        )
        if orders:
            # Una entrega parcial posterior vuelve a facturar lo nuevo entregado.
            orders.write({
                'selfbilling_auto_state': 'pending',
                'selfbilling_auto_attempts': 0,
                'selfbilling_auto_retry_at': False,
            })
            cron = self.env.ref(CRON_AUTO_INVOICE, raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger(at=fields.Datetime.now() + AUTO_DEBOUNCE)

    @api.model
    def _selfbilling_auto_domain(self):
        return [
            ('selfbilling_auto_state', '=', 'pending'),
            '|', ('selfbilling_auto_retry_at', '=', False),
            ('selfbilling_auto_retry_at', '<=', fields.Datetime.now()),
        ]

    @api.model
    def _cron_selfbilling_auto_invoice(self, limit=AUTO_BATCH, budget=AUTO_TIME_BUDGET):
        deadline = time.monotonic() + budget
        done = 0
        while time.monotonic() < deadline:
            orders = self.search(self._selfbilling_auto_domain(), limit=limit, order='id')
            if not orders:
                break
            for order in orders:
                if time.monotonic() > deadline:
                    break
                order.with_company(order.company_id)._selfbilling_auto_invoice()
                done += 1
        remaining = self.search_count(self._selfbilling_auto_domain())
        self.env['ir.cron']._notify_progress(done=done, remaining=remaining)

    def _selfbilling_commit(self):
        if not _in_test():
            self.env.cr.commit()

    # ── Facturar y timbrar ─────────────────────────────────────────────

    def _selfbilling_auto_skip_reason(self):
        self.ensure_one()
        partner = self._selfbilling_auto_partner()
        if self.state != 'sale':
            return _('La venta no está confirmada.')
        if not partner.selfbilling_auto and not self.env.context.get('selfbilling_force'):
            return _('El cliente desactivó la facturación automática.')
        if 'l10n_mx_edi_cfdi_to_public' in self._fields and self.l10n_mx_edi_cfdi_to_public:
            return _('La venta está marcada como CFDI a público en general.')
        return False

    def _selfbilling_auto_invoice(self):
        """Facturar lo entregado, timbrar y enviar. Nunca lanza."""
        self.ensure_one()
        reason = self._selfbilling_auto_skip_reason()
        if reason:
            self.write({'selfbilling_auto_state': 'skipped', 'selfbilling_auto_info': reason})
            self._selfbilling_commit()
            return
        partner = self._selfbilling_auto_partner()
        fiscal_errors = partner._selfbilling_fiscal_errors()
        if fiscal_errors:
            self._selfbilling_auto_fail(
                _('Datos fiscales incompletos del cliente: %s', ' '.join(fiscal_errors.values())), final=True,
            )
            return
        if self.invoice_ids.filtered(lambda m: m.state == 'draft' and m.move_type == 'out_invoice'):
            self._selfbilling_auto_fail(
                _('La venta tiene una factura en borrador: publíquela o elimínela y reintente.'), final=True,
            )
            return

        # 1. Factura publicada: se confirma antes de llamar al PAC.
        try:
            with self.env.cr.savepoint():
                if self.invoice_status == 'to invoice':
                    if 'l10n_mx_edi_usage' in self._fields and partner.l10n_mx_edi_usage:
                        self.l10n_mx_edi_usage = partner.l10n_mx_edi_usage
                    invoices = self._create_invoices(final=True)
                    invoices.action_post()
        except Exception as exc:  # noqa: BLE001 - queda en la venta
            _logger.exception('Facturación automática: no se pudo crear la factura de %s', self.name)
            self._selfbilling_auto_fail(_('No se pudo crear la factura: %s', exc))
            return
        self._selfbilling_commit()

        # 2. Timbrar y enviar lo que falte. Lo que el PAC firma se guarda de inmediato.
        invoices = self.invoice_ids.filtered(
            lambda m: m.state == 'posted' and m.move_type == 'out_invoice' and not m._selfbilling_is_stamped()
        )
        try:
            errors = invoices._selfbilling_stamp(send_email=True)
        except Exception as exc:  # noqa: BLE001
            _logger.exception('Facturación automática: error al timbrar %s', self.name)
            if not _in_test():
                self.env.cr.rollback()
            errors = [str(exc)]
        if errors:
            self._selfbilling_auto_fail(' '.join(errors))
            return
        if not invoices:
            self.write({
                'selfbilling_auto_state': 'skipped',
                'selfbilling_auto_info': _('No hay nada nuevo entregado por facturar.'),
            })
            self._selfbilling_commit()
            return
        self.write({
            'selfbilling_auto_state': 'done',
            'selfbilling_auto_info': False,
            'selfbilling_auto_retry_at': False,
        })
        self.message_post(
            body=Markup('%s %s') % (
                _('Facturación automática: timbrada y enviada al cliente.'),
                ', '.join(invoices.mapped('name')),
            ),
            subtype_xmlid='mail.mt_note',
        )
        self._selfbilling_commit()

    def _selfbilling_auto_fail(self, message, final=False):
        attempts = self.selfbilling_auto_attempts + 1
        retry = not final and attempts < AUTO_MAX_ATTEMPTS
        self.write({
            'selfbilling_auto_state': 'pending' if retry else 'error',
            'selfbilling_auto_info': message,
            'selfbilling_auto_attempts': attempts,
            'selfbilling_auto_retry_at': fields.Datetime.now() + AUTO_RETRY_DELAY if retry else False,
        })
        if not retry:
            user = self.user_id if self.user_id and self.user_id.active and not self.user_id._is_superuser() else False
            if user:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('Facturación automática fallida'),
                    note=message,
                )
            self.message_post(body=_('Facturación automática fallida: %s', message), subtype_xmlid='mail.mt_note')
        self._selfbilling_commit()

    def action_selfbilling_auto_invoice(self):
        """Facturar, timbrar y enviar ya (o reintentar)."""
        for order in self.sudo():
            order.write({'selfbilling_auto_state': 'pending', 'selfbilling_auto_attempts': 0,
                         'selfbilling_auto_retry_at': False})
            order.with_company(order.company_id).with_context(selfbilling_force=True)._selfbilling_auto_invoice()
        return True

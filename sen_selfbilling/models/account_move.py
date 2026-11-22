import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _selfbilling_is_stamped(self):
        self.ensure_one()
        return self.state == 'posted' and self.l10n_mx_edi_cfdi_state == 'sent'

    def _selfbilling_stamp(self, send_email=False):
        """Timbrar (CFDI + PDF) las facturas publicadas que aún no lo están.

        Con `send_email` además se mandan por correo a quien tenga correo.
        Devuelve la lista de errores legibles; nunca lanza por un rechazo del PAC.
        """
        to_stamp = self.filtered(lambda m: m.state == 'posted' and not m._selfbilling_is_stamped())
        errors = []
        failed = self.browse()
        for invoice in to_stamp:
            methods = ['email'] if send_email and invoice.partner_id.email else ['manual']
            try:
                self.env['account.move.send'].sudo()._generate_and_send_invoices(
                    invoice, sending_methods=methods, extra_edis={'mx_cfdi'}, allow_raising=False,
                )
            except Exception:
                # Fallos ajenos al PAC (certificado, red...): detalle al log, mensaje legible.
                _logger.exception("Error timbrando la factura %s", invoice.name)
                errors.append(f"No se pudo timbrar {invoice.name} en este momento, intente más tarde.")
                failed |= invoice
        for invoice in (to_stamp - failed).filtered(lambda m: not m._selfbilling_is_stamped()):
            document = invoice.l10n_mx_edi_invoice_document_ids.filtered(
                lambda d: d.state == 'invoice_sent_failed')[:1]
            errors.append(f"No se pudo timbrar {invoice.name}: {document.message or 'el PAC rechazó el CFDI.'}")
        return errors

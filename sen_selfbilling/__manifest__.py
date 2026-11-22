# Copyright © 2026 Noden Labs (https://sentilis.me/noden)
# All rights reserved. Licensed under OPL-1.
# See: https://www.odoo.com/documentation/user/legal/licenses/licenses.html
{
    'name': 'AutoInvoice MX: CFDI 4.0 Self-Billing for Marketplaces — Noden',
    'summary': 'Your Mercado Libre, native Amazon and web-store customers invoice themselves: '
               'order number + RFC and a stamped CFDI 4.0 arrives instantly. No data entry.',
    'version': '19.0.1.5.0',
    'category': 'Accounting/Localizations',
    'author': 'Noden Labs',
    'website': 'https://sentilis.me/noden',
    'support': 'noden@sentilis.me',
    'depends': [
        'account',
        'sale',
        'sale_stock',
        'portal',
        'website',
        'l10n_mx_edi',
        # Uso del CFDI y forma de pago en la venta (/billing los escribe).
        'l10n_mx_edi_sale',
        #'point_of_sale'
    ],
    'data': [
        'data/ir_cron.xml',
        'views/billing_tmpl.xml',
        'views/portal_templates.xml',
        'views/backend_views.xml',
    ],
    'images': ['static/description/cover.png'],
    'application': True,
    'installable': True,
    'price': 0.00,
    'currency': 'USD',
    'license': 'OPL-1',
}

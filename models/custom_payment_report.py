# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CustomPaymentReport(models.Model):
    _name = 'account.payment.custom_payment_report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    
    name = fields.Char(string='',readonly=True)
    
    date = fields.Date(
        string='Date', 
        default=fields.Date.context_today,  # Asigna el día actual por defecto
    )
    
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Hecho'), 
        ('sent', 'Enviado'),
    ], string='Estado', default='draft',tracking=True)
    
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Contacto",
        readonly=False,
        tracking=True)
    
    partner_type = fields.Selection(string='Tipo',selection=[
        ('customer', 'Cliente'),
        ('supplier', 'Proveedor'),
    ], default='supplier', required=True,readonly=True)
    
    paid_payment_ids = fields.Many2many(
        'account.payment',
        'account_payment_custom_payment_report_rel',
        'custom_payment_id',
        'paid_payment_id',
        string='Pagos realizados',
        #readonly=False,
        domain="[('partner_id', '=', partner_id), ('partner_type', 'in', ['customer', 'supplier'])]"
    )
    matched_move_line_ids = fields.Many2many(
        'account.move.line',
        compute='_compute_matched_move_line_ids',
        help='Facturas que fueron imputadas en los pagos',
    )

    withholding_line_ids = fields.Many2many(
    'l10n_ar.payment.withholding',
    'account_custom_report_withholding_rel',
    'custom_report_id',
    'wihholding_id',
    compute='_compute_l10n_ar_withholding_line_ids',
    string='Withholding Lines',
    readonly=True,
    store=True)
    
    @api.onchange('partner_id')
    def _compute_paid_payment_ids(self):
        self.add_all()
                
    @api.depends('paid_payment_ids')
    def _compute_matched_move_line_ids(self):
        for record in self:
            # Inicializar un conjunto vacío para almacenar las líneas de facturas imputadas
            matched_lines = self.env['account.move.line']
            
            # Iterar sobre los pagos en la lista paid_payment_ids
            for payment in record.paid_payment_ids:
                # Buscar todas las líneas de movimientos que están conciliadas (matched) con los pagos
                for line in payment.matched_move_line_ids:
                    # Si la línea tiene movimientos conciliados, agregar las líneas de factura relacionadas
                    matched_lines |= line.matched_credit_ids.mapped('debit_move_id')
                    matched_lines |= line.matched_debit_ids.mapped('credit_move_id')

            # Asignar las líneas de facturas imputadas al campo Many2many
            record.matched_move_line_ids = matched_lines

    @api.depends('paid_payment_ids')
    def _compute_l10n_ar_withholding_line_ids(self):
        for record in self:
            # Inicializar un conjunto vacío para almacenar las líneas de retenciones
            withholding_lines = self.env['l10n_ar.payment.withholding']
    
            # Iterar sobre los pagos realizados en paid_payment_ids
            for payment in record.paid_payment_ids:
                # Buscar todas las líneas de retenciones relacionadas con los pagos
                withholding_lines |= self.env['l10n_ar.payment.withholding'].search([('payment_id', '=', payment.id)])
    
            # Asignar las líneas de retenciones encontradas al campo withholding_line_ids
            record.withholding_line_ids = withholding_lines

    def add_all(self):
        for record in self:
            if record.partner_id:
                domain = [('partner_id', '=', record.partner_id.id), ('state', '=', 'posted')]
                # Añadir condición según el partner_type
                if record.partner_type == 'supplier':
                    # Buscar pagos de proveedor (normalmente outbound)
                    domain.append(('payment_type', '=', 'outbound'))
                elif record.partner_type == 'customer':
                    # Buscar pagos de cliente (normalmente inbound)
                    domain.append(('payment_type', '=', 'inbound'))
                
                # Buscar los pagos según las condiciones
                pagos = self.env['account.payment'].search(domain)
                record.paid_payment_ids = pagos
            else:
                record.paid_payment_ids = False
    def remove_all(self):
        self.paid_payment_ids= False
            
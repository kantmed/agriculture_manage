from odoo import fields, models


class AgricultureCompanyGroup(models.Model):
    _name = "agriculture.company.group"
    _description = "Groupe de sociétés agricoles"

    name = fields.Char(required=True)
    company_ids = fields.Many2many("res.company", string="Sociétés", required=True)
    active = fields.Boolean(default=True)
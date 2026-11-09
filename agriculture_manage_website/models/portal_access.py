from odoo import fields, models


class AgriculturePortalAccess(models.Model):
    _name = "agriculture.portal.access"
    _description = "Accès portail agricole"

    name = fields.Char(required=True)
    user_id = fields.Many2one("res.users", required=True)
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    farm_ids = fields.Many2many(
        comodel_name="agriculture.farm",
        relation="farm_user_rel",
        column1="user_id",
        column2="farm_id",
        string="Exploitations autorisées",
        help="Exploitations auxquelles cet utilisateur peut accéder.",
    )
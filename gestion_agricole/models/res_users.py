# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    gest_agri_farm_ids = fields.Many2many(
        "gest_agri.farm",
        string="Exploitations accessibles",
        compute="_compute_gest_agri_farms",
        compute_sudo=True,
        help="Exploitations dont l'utilisateur est responsable ou sur lesquelles "
        "il dispose d'un droit d'accès actif.",
    )
    gest_agri_managed_farm_ids = fields.Many2many(
        "gest_agri.farm",
        string="Exploitations administrées",
        compute="_compute_gest_agri_farms",
        compute_sudo=True,
        help="Exploitations sur lesquelles l'utilisateur peut modifier les "
        "données : responsable ou rôle Responsable/Administrateur.",
    )

    def _compute_gest_agri_farms(self):
        Farm = self.env["gest_agri.farm"].sudo()
        Access = self.env["gest_agri.farm.access"].sudo()
        for user in self:
            managed_farm_ids = set(
                Farm.search([("manager_id", "=", user.id)]).ids
            )
            access_farm_ids = set(
                Access.search(
                    [("user_id", "=", user.id), ("active", "=", True)]
                ).mapped("farm_id").ids
            )
            elevated_farm_ids = set(
                Access.search(
                    [
                        ("user_id", "=", user.id),
                        ("active", "=", True),
                        ("role", "in", ("manager", "admin")),
                    ]
                ).mapped("farm_id").ids
            )
            managed_farm_ids |= elevated_farm_ids
            user.gest_agri_farm_ids = [
                (6, 0, sorted(managed_farm_ids | access_farm_ids))
            ]
            user.gest_agri_managed_farm_ids = [(6, 0, sorted(managed_farm_ids))]

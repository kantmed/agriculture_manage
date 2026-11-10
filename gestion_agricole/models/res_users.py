# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    gest_agri_farm_ids = fields.Many2many(
        "gest_agri.farm",
        string="Exploitations accessibles",
        compute="_compute_gest_agri_farms",
        compute_sudo=True,
        bypass_search_access=True,
        help="Exploitations dont l'utilisateur est responsable ou sur lesquelles "
        "il dispose d'un droit d'accès actif.",
    )
    gest_agri_managed_farm_ids = fields.Many2many(
        "gest_agri.farm",
        string="Exploitations administrées",
        compute="_compute_gest_agri_farms",
        compute_sudo=True,
        bypass_search_access=True,
        help="Exploitations sur lesquelles l'utilisateur peut modifier les "
        "données : responsable ou rôle Responsable/Administrateur.",
    )

    def _compute_gest_agri_farms(self):
        # Les recherches sont effectuées en sudo (l'utilisateur ne peut pas
        # lire les droits d'accès des autres), mais le périmètre multi-sociétés
        # DOIT être appliqué : sans ce filtre, un responsable d'une société
        # voyait et pouvait modifier le patrimoine d'une exploitation d'une
        # autre société (fuite inter-sociétés).
        #
        # Le périmètre utilisé est celui de l'utilisateur concerné
        # (user._get_company_ids()) et non celui de l'environnement ambiant :
        # le résultat est ainsi une fonction pure de l'utilisateur, ce qui
        # évite une valeur dépendante du contexte de lecture.
        #
        # bypass_search_access=True est indispensable sur ces deux champs :
        # sans lui, la conversion du Many2many filtre les exploitations selon
        # le droit de lecture de gest_agri.farm, dont le domaine d'accès
        # repose précisément sur gest_agri_farm_ids. La conversion réentrait
        # donc dans l'évaluation du domaine d'accès (dépendance circulaire) et
        # pouvait renvoyer une liste vide, rendant l'accès aux exploitations
        # imprévisible.
        Farm = self.env["gest_agri.farm"].sudo()
        Access = self.env["gest_agri.farm.access"].sudo()
        for user in self:
            company_ids = user._get_company_ids()
            managed_farm_ids = set(
                Farm.search(
                    [("manager_id", "=", user.id), ("company_id", "in", company_ids)]
                ).ids
            )
            # Une seule recherche pour tous les droits d'accès de l'utilisateur.
            accesses = Access.search(
                [
                    ("user_id", "=", user.id),
                    ("active", "=", True),
                    ("company_id", "in", company_ids),
                ]
            )
            access_farm_ids = set(accesses.mapped("farm_id").ids)
            elevated_farm_ids = set(
                accesses.filtered(
                    lambda access: access.role in ("manager", "admin")
                ).mapped("farm_id").ids
            )
            managed_farm_ids |= elevated_farm_ids
            user.gest_agri_farm_ids = [
                (6, 0, sorted(managed_farm_ids | access_farm_ids))
            ]
            user.gest_agri_managed_farm_ids = [(6, 0, sorted(managed_farm_ids))]

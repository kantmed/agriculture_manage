# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError


class GestAgriFarmAccess(models.Model):
    _name = "gest_agri.farm.access"
    _description = "Droit d'accès à une exploitation"
    _order = "farm_id, role, user_id"
    _check_company_auto = True

    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Utilisateur",
        required=True,
        ondelete="cascade",
        domain=[("share", "=", False)],
        index=True,
    )
    role = fields.Selection(
        selection=[
            ("user", "Utilisateur"),
            ("manager", "Responsable"),
            ("admin", "Administrateur"),
        ],
        string="Rôle",
        required=True,
        default="user",
        help="Rôle accordé à l'utilisateur sur cette exploitation.",
    )
    company_id = fields.Many2one(
        related="farm_id.company_id",
        string="Société",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)

    _unique_active_user_farm = models.UniqueIndex(
        "(farm_id, user_id) WHERE active IS TRUE",
        "Un utilisateur ne peut avoir qu'un seul droit d'accès actif par exploitation.",
    )

    def _invalidate_farm_access_cache(self):
        """Invalide les caches de sécurité dépendant des droits d'accès."""
        self.env.invalidate_all()
        self.env.transaction.invalidate_access_cache()
        self.env.transaction.invalidate_ormcache("default")
        self.env.transaction.invalidate_ormcache("stable")

    def _check_self_management(self):
        """Interdit à un non-administrateur de modifier ses propres droits."""
        if self.env.su or self.env.user.has_group(
            "gestion_agricole.group_gest_agri_admin"
        ):
            return
        if any(access.user_id == self.env.user for access in self):
            # NOUVEAU : bloquer si ce n'est pas admin ET hors société
            user_company = self.env.company.id
            access_companies = self.mapped("farm_id.company_id").ids
            if user_company not in access_companies:
                raise AccessError(
                    self.env._(
                        "Vous ne pouvez pas modifier vos propres droits d'accès "
                        "sur une exploitation d'une autre société. "
                        "Contactez un administrateur agricole."
                    )
                )
            raise AccessError(
                self.env._(
                    "Vous ne pouvez pas modifier ou supprimer vos propres droits "
                    "d'accès à une exploitation. Contactez un administrateur agricole."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        accesses = super().create(vals_list)
        accesses._check_self_management()
        accesses._invalidate_farm_access_cache()
        return accesses

    def write(self, vals):
        if "farm_id" in vals:
            for record in self.filtered(
                lambda r: not r.env.user.has_group(
                    "gestion_agricole.group_gest_agri_admin"
                )
            ):
                target_farm_id = vals["farm_id"]
                target_farm = record.env["gest_agri.farm"].browse(target_farm_id)
                # Vérifier que la cible appartient à la même société
                if target_farm.company_id != record.company_id:
                    raise AccessError(
                        "Vous ne pouvez pas modifier le droit d'accès vers une "
                        "exploitation d'une autre société."
                    )
                # Vérifier que le responsable a le droit sur la cible
                user = record.env.user
                if not user.has_group(
                    "gestion_agricole.group_gest_agri_manager"
                ) and user.id != target_farm.manager_id.id:
                    raise AccessError(
                        "Vous ne pouvez pas modifier le droit d'accès vers une "
                        "exploitation que vous ne gérez pas."
                    )
        result = super().write(vals)
        if {"farm_id", "user_id", "role", "active"} & set(vals):
            self._check_self_management()
            self._invalidate_farm_access_cache()
        return result

    def unlink(self):
        self._check_self_management()
        result = super().unlink()
        self.env.invalidate_all()
        self.env.transaction.invalidate_access_cache()
        self.env.transaction.invalidate_ormcache("default")
        self.env.transaction.invalidate_ormcache("stable")
        return result

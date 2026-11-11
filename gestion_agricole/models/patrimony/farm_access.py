# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


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
    notes = fields.Text(
        string="Notes internes",
        help="Motif, observations et précisions complémentaires concernant cette habilitation.",
    )
    date_start = fields.Date(
        string="Date de début",
        help="Début prévu de validité de l'habilitation.",
    )
    date_end = fields.Date(
        string="Date de fin",
        help="Fin prévue de validité de l'habilitation.",
    )
    is_expired = fields.Boolean(
        string="Habilitation expirée",
        compute="_compute_is_expired",
        search="_search_is_expired",
        help="Indique si la date de fin de validité est dépassée. "
        "Information purement indicative : elle ne modifie pas les droits accordés.",
    )
    active = fields.Boolean(string="Actif", default=True)

    _unique_active_user_farm = models.UniqueIndex(
        "(farm_id, user_id) WHERE active IS TRUE",
        "Un utilisateur ne peut avoir qu'un seul droit d'accès actif par exploitation.",
    )

    def _invalidate_farm_access_cache(self):
        """Invalide les caches de sécurité dépendant des droits d'accès.

        Trois caches sont concernés :

        * le cache de valeurs des deux champs calculés de ``res.users``
          (``gest_agri_farm_ids`` / ``gest_agri_managed_farm_ids``), qui
          portent les périmètres d'accès ;
        * le cache ormcache « default », qui contient le domaine d'accès
          ``BaseModel._access_domain``. Ce domaine est évalué à partir de
          ``user.gest_agri_farm_ids`` : sans invalidation, un droit d'accès
          créé ou modifié ne serait pris en compte qu'à la fin de la
          transaction, et l'utilisateur ne verrait pas ses exploitations ;
        * le cache d'accès Odoo (décisions de lecture par enregistrement).

        L'ancien ``env.invalidate_all()`` vidait l'intégralité du cache ORM
        (donc celui de tous les modules) : il est remplacé par une invalidation
        ciblée, tout en conservant l'invalidation ormcache indispensable.
        """
        self.env["res.users"].invalidate_model(
            ["gest_agri_farm_ids", "gest_agri_managed_farm_ids"]
        )
        self.env.transaction.invalidate_ormcache("default")
        self.env.transaction.invalidate_access_cache()

    @api.depends("date_end")
    def _compute_is_expired(self):
        """Une habilitation est expirée si sa date de fin est passée.

        Le champ n'est pas stocké : le résultat est recalculé à chaque lecture
        et suit donc naturellement le changement de date, sans cron.
        """
        today = fields.Date.context_today(self)
        for access in self:
            access.is_expired = bool(access.date_end and access.date_end < today)

    def _search_is_expired(self, operator, value):
        """Traduit la recherche sur ``is_expired`` en domaine sur ``date_end``."""
        today = fields.Date.context_today(self)
        expired_domain = [("date_end", "<", today)]
        not_expired_domain = [
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", today),
        ]

        if operator in ("in", "not in"):
            # L'optimiseur de domaines d'Odoo 20 peut convertir un test
            # booléen en opérateur « in » : on le prend en charge.
            values = value if isinstance(value, (list, tuple, set)) else [value]
            states = {bool(item) for item in values}
            if operator == "not in":
                states = {not state for state in states}
            if states == {True}:
                return expired_domain
            if states == {False}:
                return not_expired_domain
            return []

        if operator not in ("=", "!="):
            raise ValueError(
                self.env._(
                    "Opérateur non pris en charge pour « Habilitation expirée »."
                )
            )
        expired = bool(value)
        if operator == "!=":
            expired = not expired
        return expired_domain if expired else not_expired_domain

    @api.constrains("date_start", "date_end")
    def _check_date_period(self):
        """La date de fin ne peut pas précéder la date de début."""
        for access in self:
            if (
                access.date_start
                and access.date_end
                and access.date_end < access.date_start
            ):
                raise ValidationError(
                    self.env._(
                        "La date de fin de validité ne peut pas être antérieure "
                        "à la date de début."
                    )
                )

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

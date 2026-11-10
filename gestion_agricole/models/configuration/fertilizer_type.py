# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_reference


class GestAgriFertilizerType(models.Model):
    _name = "gest_agri.fertilizer.type"
    _description = "Type d'engrais"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        index=True,
        default=lambda self: self.env.company,
        help="Laisser vide pour un référentiel global, réservé aux administrateurs.",
    )
    sequence = fields.Integer(string="Séquence", default=10)

    # Unicité garantie au niveau PostgreSQL.
    # Les index uniques sont la seule garantie d'unicité réellement fiable
    # sous REPEATABLE READ (niveau d'isolation par défaut d'Odoo 20) : le
    # verrou consultatif de check_unique_reference() sérialise les
    # transactions mais ne rafraîchit pas l'instantané de lecture.
    # La normalisation SQL (LOWER(BTRIM(...))) est volontairement plus
    # permissive que la normalisation Python (.strip().casefold()) : la
    # contrainte Python reste le message utilisateur, la base est le garde-fou.
    _code_company_unique = models.UniqueIndex(
        "(company_id, LOWER(BTRIM(code))) "
        "WHERE active IS TRUE AND company_id IS NOT NULL",
        "Le code doit être unique au sein de la société.",
    )
    _code_global_unique = models.UniqueIndex(
        "(LOWER(BTRIM(code))) WHERE active IS TRUE AND company_id IS NULL",
        "Un code global doit être unique parmi les codes globaux.",
    )
    _name_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(name))) WHERE active IS TRUE",
        "Le nom doit être unique au sein de la société.",
    )

    @api.constrains("code", "company_id", "active")
    def _check_code_unique(self):
        # Une référence globale (sans société) est réservée à l'administrateur
        # agricole.
        # Attention : company_id est un Many2one ; sous Odoo 20 l'expression
        # « record.company_id == False » vaut TOUJOURS False (BaseModel.__eq__
        # renvoie NotImplemented pour un comparateur qui n'est pas un
        # BaseModel, et la comparaison retombe alors sur l'identité). Il faut
        # donc tester la vacuité du Many2one.
        # Le superutilisateur (et les opérations en sudo) sont autorisés :
        # ils sont utilisés par les chargements de données et les tests.
        if not self.env.su and not self.env.user.has_group(
            "gestion_agricole.group_gest_agri_admin"
        ):
            for record in self:
                if not record.company_id:
                    raise ValidationError(
                        self.env._(
                            "Seul un administrateur agricole peut gérer une "
                            "référence globale (sans société)."
                        )
                    )
        check_unique_reference(self, "code", "Code", global_scope=True)

    @api.constrains("name", "company_id", "active")
    def _check_name_unique(self):
        # Une référence globale (sans société) est réservée à l'administrateur
        # agricole.
        # Attention : company_id est un Many2one ; sous Odoo 20 l'expression
        # « record.company_id == False » vaut TOUJOURS False (BaseModel.__eq__
        # renvoie NotImplemented pour un comparateur qui n'est pas un
        # BaseModel, et la comparaison retombe alors sur l'identité). Il faut
        # donc tester la vacuité du Many2one.
        # Le superutilisateur (et les opérations en sudo) sont autorisés :
        # ils sont utilisés par les chargements de données et les tests.
        if not self.env.su and not self.env.user.has_group(
            "gestion_agricole.group_gest_agri_admin"
        ):
            for record in self:
                if not record.company_id:
                    raise ValidationError(
                        self.env._(
                            "Seul un administrateur agricole peut gérer une "
                            "référence globale (sans société)."
                        )
                    )
        check_unique_reference(self, "name", "Nom", global_scope=False)

# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriEggCategory(models.Model):
    """Catégorie d'œufs configurable.

    Les catégories (très gros, gros, moyen, petit, déclassé, cassé, autre…)
    sont un référentiel configurable : aucun seuil commercial ou réglementaire
    n'est codé en dur. Le drapeau ``is_loss`` permet de distinguer les
    catégories de perte / déclassement des catégories commercialisables sans
    dépendre du libellé.
    """

    _name = "gest_agri.egg.category"
    _description = "Catégorie d'œufs"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    sequence = fields.Integer(string="Séquence", default=10)
    is_loss = fields.Boolean(
        string="Catégorie de perte / déclassement",
        help="Cochez pour les catégories qui ne sont pas commercialisables "
             "(cassé, déclassé, sale…). Utilisé par les statistiques de pertes.",
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        index=True,
        default=lambda self: self.env.company,
    )

    _code_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(code))) WHERE active IS TRUE",
        "Le code de catégorie d'œufs doit être unique au sein de la société.",
    )
    _name_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(name))) WHERE active IS TRUE",
        "Le nom de catégorie d'œufs doit être unique au sein de la société.",
    )

    @api.constrains("code", "company_id", "active")
    def _check_code_unique(self):
        for rec in self:
            if not rec.code or not rec.active:
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("company_id", "=", rec.company_id.id),
                ("code", "=ilike", rec.code.strip()),
            ])
            if duplicates:
                raise ValidationError(self.env._("Le code de catégorie « %s » existe déjà.", rec.code))

    @api.constrains("name", "company_id", "active")
    def _check_name_unique(self):
        for rec in self:
            if not rec.name or not rec.active:
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("company_id", "=", rec.company_id.id),
                ("name", "=ilike", rec.name.strip()),
            ])
            if duplicates:
                raise ValidationError(self.env._("Le nom de catégorie « %s » existe déjà.", rec.name))

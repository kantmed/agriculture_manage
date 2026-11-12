# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalMortality(models.Model):
    _name = "gest_agri.animal.mortality"
    _description = "Mortalité animale"
    _inherit = ["mail.thread"]
    _order = "death_datetime desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="restrict", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="restrict", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", compute="_compute_farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)

    death_datetime = fields.Datetime(string="Date et heure du décès", required=True, default=fields.Datetime.now, index=True)
    mortality_type = fields.Selection(
        selection=[
            ("disease", "Maladie"),
            ("accident", "Accident"),
            ("birth", "Mise bas"),
            ("health_issue", "Problème sanitaire"),
            ("slaughter", "Abattage / sortie"),
            ("unknown", "Cause inconnue"),
        ],
        string="Type de mortalité", required=True, default="unknown",
    )
    cause = fields.Char(string="Cause du décès")
    diagnosis = fields.Text(string="Diagnostic vétérinaire")
    health_record_id = fields.Many2one("gest_agri.animal.health", string="Dossier sanitaire associé", ondelete="set null")
    consultation_id = fields.Many2one("gest_agri.veterinary.consultation", string="Consultation associée", ondelete="set null")
    animal_count = fields.Integer(string="Nombre d'animaux concernés (lot)", default=0)
    responsible_id = fields.Many2one("res.users", string="Responsable de la déclaration", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )
    previous_animal_state = fields.Selection(
        selection=[
            ("draft", "Brouillon"), ("active", "Actif"), ("sold", "Vendu"),
            ("dead", "Mort"), ("retired", "Retiré"),
        ],
        string="État de l'animal avant décès", readonly=True, copy=False,
        help="État exact de l'animal juste avant la validation de la mortalité. "
             "Il permet une annulation sûre et traçable de la mortalité.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.mortality")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.mortality » est introuvable."))
                vals["name"] = ref
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une mortalité doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une mortalité ne peut concerner à la fois un animal et un lot."))
            if vals.get("animal_count", 0) < 0:
                raise ValidationError(self.env._("Le nombre d'animaux ne peut pas être négatif."))
        return super().create(vals_list)

    @api.depends("animal_id", "lot_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.animal_id.farm_id or rec.lot_id.farm_id

    @api.constrains("animal_id", "state")
    def _check_animal_unique(self):
        for rec in self:
            if not rec.animal_id or rec.state == "cancelled":
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("animal_id", "=", rec.animal_id.id),
                ("state", "!=", "cancelled"),
            ])
            if duplicates:
                raise ValidationError(self.env._("Une mortalité est déjà enregistrée pour cet animal."))

    def _lot_declared_deaths(self):
        """Total des décès déjà déclarés pour le lot, hors enregistrements annulés.

        Le lot lui-même n'est jamais modifié : on ne fait que comptabiliser les
        mortalités qui le concernent afin de déterminer l'effectif encore disponible.
        """
        self.ensure_one()
        domain = [
            ("lot_id", "=", self.lot_id.id),
            ("state", "!=", "cancelled"),
            ("animal_count", ">", 0),
        ]
        if self.id:
            domain.append(("id", "!=", self.id))
        return sum(self.search(domain).mapped("animal_count"))

    def _lot_available_capacity(self):
        """Effectif du lot encore disponible pour de nouvelles mortalités."""
        self.ensure_one()
        return self.lot_id.member_count - self._lot_declared_deaths()

    def _lock_lot_row(self):
        """Verrou transactionnel de la ligne de lot (SELECT ... FOR UPDATE).

        Sérialise les validations concurrentes de mortalités de lot sans modifier
        la configuration PostgreSQL ni installer d'extension : deux transactions
        ne peuvent pas valider simultanément des décès dont le cumul dépasse
        l'effectif disponible.
        """
        self.ensure_one()
        if self.lot_id:
            self.env.cr.execute(
                "SELECT id FROM gest_agri_animal_lot WHERE id = %s FOR UPDATE",
                (self.lot_id.id,),
            )

    @api.constrains("animal_count", "lot_id", "state")
    def _check_lot_count(self):
        for rec in self:
            if not rec.lot_id or rec.state == "cancelled":
                continue
            if rec.animal_count <= 0:
                raise ValidationError(self.env._("Le nombre d'animaux décédés du lot doit être strictement positif."))
            available = rec._lot_available_capacity()
            if rec.animal_count > available:
                raise ValidationError(self.env._(
                    "Le nombre déclaré (%(c)s) dépasse l'effectif disponible du lot (%(a)s).",
                    c=rec.animal_count, a=available,
                ))

    @api.constrains("lot_id", "death_datetime", "state")
    def _check_lot_unique(self):
        for rec in self:
            if not rec.lot_id or not rec.death_datetime or rec.state == "cancelled":
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("lot_id", "=", rec.lot_id.id),
                ("death_datetime", "=", rec.death_datetime),
                ("state", "!=", "cancelled"),
            ])
            if duplicates:
                raise ValidationError(self.env._("Une mortalité est déjà enregistrée pour ce lot à cette date."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_mortality_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_mortality_state_transition=True).write({"state": target})

    def action_validate(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("Seule une mortalité en brouillon peut être validée."))
        # Verrou transactionnel par lot : sérialise les validations concurrentes.
        for rec in self:
            rec._lock_lot_row()
        # Contrôle d'effectif autoritatif (sous verrou) pour les mortalités de lot.
        for rec in self:
            if rec.lot_id:
                available = rec._lot_available_capacity()
                if rec.animal_count > available:
                    raise ValidationError(self.env._(
                        "Le nombre déclaré (%(c)s) dépasse l'effectif disponible du lot (%(a)s).",
                        c=rec.animal_count, a=available,
                    ))
        # Mémoriser l'état antérieur exact des animaux avant de les marquer décédés.
        for rec in self:
            if rec.animal_id and not rec.previous_animal_state:
                rec.previous_animal_state = rec.animal_id.state
        self._apply_state("validated")
        for rec in self:
            if rec.animal_id:
                rec.animal_id.with_context(gest_agri_animal_state_transition=True).write({"state": "dead"})

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(self.env._("La mortalité est déjà annulée."))
            if rec.state == "validated" and rec.animal_id:
                # Une annulation n'est autorisée que si la restauration est fiable :
                # l'état antérieur doit être connu et l'animal ne doit pas avoir
                # changé d'état depuis (pour ne pas écraser une modification légitime).
                if not rec.previous_animal_state:
                    raise UserError(self.env._(
                        "L'état antérieur de l'animal n'est pas connu : l'annulation de la "
                        "mortalité « %s » est interdite. Utilisez une procédure corrective traçable.",
                        rec.display_name,
                    ))
                if rec.animal_id.state != "dead":
                    raise UserError(self.env._(
                        "L'animal « %(a)s » a changé d'état depuis la validation de la mortalité "
                        "« %(m)s » : l'annulation automatique est interdite pour ne pas écraser une "
                        "modification légitime. Utilisez une procédure corrective traçable.",
                        a=rec.animal_id.display_name, m=rec.display_name,
                    ))
        restorations = [
            (rec.animal_id, rec.previous_animal_state)
            for rec in self
            if rec.state == "validated" and rec.animal_id and rec.previous_animal_state
        ]
        self._apply_state("cancelled")
        for animal, target_state in restorations:
            animal.with_context(gest_agri_animal_state_transition=True).write({"state": target_state})

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La mortalité « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()

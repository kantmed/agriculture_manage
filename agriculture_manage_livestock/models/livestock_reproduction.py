from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AgricultureLivestockReproduction(models.Model):
    _name = "agriculture.livestock.reproduction"
    _description = "Cycle de reproduction"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "service_date desc, id desc"

    name = fields.Char(string="Référence", readonly=True, copy=False, default="Nouveau", tracking=True)
    female_id = fields.Many2one(
        "agriculture.livestock.animal", string="Femelle", required=True,
        domain="[('sex', '=', 'female'), ('state', '=', 'active')]", ondelete="restrict", tracking=True,
    )
    male_id = fields.Many2one(
        "agriculture.livestock.animal", string="Mâle / père", ondelete="restrict",
        domain="[('sex', '=', 'male'), ('state', '=', 'active')]",
    )
    farm_id = fields.Many2one(related="female_id.farm_id", store=True, readonly=True)
    company_id = fields.Many2one(related="female_id.company_id", store=True, readonly=True)
    species_id = fields.Many2one(related="female_id.species_id", store=True, readonly=True)
    service_method = fields.Selection([
        ("natural", "Saillie naturelle"),
        ("insemination", "Insémination artificielle"),
        ("unknown", "Méthode non précisée"),
    ], string="Mode de reproduction", required=True, default="natural", tracking=True)
    service_date = fields.Date(string="Date de saillie / insémination", required=True, default=fields.Date.context_today, tracking=True)
    expected_birth_date = fields.Date(string="Date prévisionnelle de mise bas", tracking=True)
    pregnancy_state = fields.Selection([
        ("planned", "Prévu"),
        ("mated", "Saillie / insémination réalisée"),
        ("pregnant", "Gestation confirmée"),
        ("delivered", "Mise bas enregistrée"),
        ("failed", "Échec / avortement"),
    ], string="État", required=True, default="planned", tracking=True)
    pregnancy_check_date = fields.Date(string="Date de confirmation")
    actual_birth_date = fields.Date(string="Date réelle de mise bas")
    offspring_count = fields.Integer(string="Nombre de petits nés", default=1)
    offspring_ids = fields.One2many("agriculture.livestock.animal", "reproduction_id", string="Petits enregistrés")
    offspring_total = fields.Integer(string="Petits créés", compute="_compute_offspring_total")
    notes = fields.Text(string="Observations")

    @api.depends("offspring_ids")
    def _compute_offspring_total(self):
        for rec in self:
            rec.offspring_total = len(rec.offspring_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.reproduction") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("female_id", "male_id", "service_date", "expected_birth_date", "pregnancy_check_date", "actual_birth_date", "offspring_count", "pregnancy_state")
    def _check_reproduction(self):
        today = fields.Date.context_today(self)
        for rec in self:
            female = rec.female_id
            if female and female.sex != "female":
                raise ValidationError(_("L'animal sélectionné comme femelle doit être de sexe féminin."))
            if female and female.state != "active":
                raise ValidationError(_("La femelle doit être active."))
            if female and not female.species_id.individual_tracking:
                raise ValidationError(_("Le suivi de reproduction individuel nécessite une espèce configurée en suivi individuel."))
            if rec.male_id:
                if rec.male_id.sex != "male" or rec.male_id.state != "active":
                    raise ValidationError(_("Le père doit être un animal mâle actif."))
                if rec.male_id.farm_id != female.farm_id or rec.male_id.species_id != female.species_id:
                    raise ValidationError(_("Le père et la femelle doivent appartenir à la même exploitation et à la même espèce."))
            if rec.service_date and rec.service_date > today:
                raise ValidationError(_("La date de saillie ou d'insémination ne peut pas être dans le futur."))
            if rec.expected_birth_date and rec.service_date and rec.expected_birth_date < rec.service_date:
                raise ValidationError(_("La date prévisionnelle doit être postérieure à la saillie ou à l'insémination."))
            if rec.pregnancy_check_date and rec.pregnancy_check_date > today:
                raise ValidationError(_("La date de confirmation ne peut pas être dans le futur."))
            if rec.pregnancy_check_date and rec.service_date and rec.pregnancy_check_date < rec.service_date:
                raise ValidationError(_("La date de confirmation ne peut pas précéder la saillie ou l'insémination."))
            if rec.actual_birth_date and rec.actual_birth_date > today:
                raise ValidationError(_("La date réelle de mise bas ne peut pas être dans le futur."))
            if rec.actual_birth_date and rec.service_date and rec.actual_birth_date < rec.service_date:
                raise ValidationError(_("La mise bas ne peut pas précéder la saillie ou l'insémination."))
            if rec.offspring_count < 1:
                raise ValidationError(_("Le nombre de petits doit être supérieur ou égal à un."))

    def action_mark_mated(self):
        for rec in self:
            if rec.pregnancy_state != "planned":
                raise UserError(_("Seul un cycle prévu peut être marqué comme saillie ou insémination réalisée."))
            rec.pregnancy_state = "mated"
        return True

    def action_confirm_pregnancy(self):
        for rec in self:
            if rec.pregnancy_state != "mated":
                raise UserError(_("La confirmation nécessite une saillie ou une insémination déjà réalisée."))
            rec.pregnancy_state = "pregnant"
            rec.pregnancy_check_date = fields.Date.context_today(rec)
        return True

    def action_register_birth(self):
        Animal = self.env["agriculture.livestock.animal"]
        for rec in self:
            if rec.pregnancy_state != "pregnant":
                raise UserError(_("Seule une gestation confirmée peut être enregistrée comme mise bas."))
            birth_date = rec.actual_birth_date or fields.Date.context_today(rec)
            if birth_date > fields.Date.context_today(rec):
                raise UserError(_("La date réelle de mise bas ne peut pas être dans le futur."))
            female = rec.female_id
            if rec.offspring_ids:
                raise UserError(_("Des petits sont déjà rattachés à ce cycle de reproduction."))
            vals_list = []
            for index in range(1, rec.offspring_count + 1):
                vals_list.append({
                    "name": _("Petit de %(mother)s - %(number)s", mother=female.name, number=index),
                    "farm_id": female.farm_id.id,
                    "site_id": female.site_id.id if female.site_id else False,
                    "species_id": female.species_id.id,
                    "breed_id": female.breed_id.id if female.breed_id else False,
                    "herd_id": female.herd_id.id if female.herd_id else False,
                    "sex": "unknown",
                    "birth_date": birth_date,
                    "entry_date": birth_date,
                    "origin": "birth",
                    "mother_id": female.id,
                    "father_id": rec.male_id.id if rec.male_id else False,
                    "reproduction_id": rec.id,
                })
            Animal.create(vals_list)
            rec.actual_birth_date = birth_date
            rec.pregnancy_state = "delivered"
        return True

    def action_mark_failed(self):
        for rec in self:
            if rec.pregnancy_state not in ("mated", "pregnant"):
                raise UserError(_("Seul un cycle sailli ou en gestation peut être marqué en échec."))
            rec.pregnancy_state = "failed"
        return True

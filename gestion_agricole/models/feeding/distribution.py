# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriFeedDistribution(models.Model):
    _name = "gest_agri.feed.distribution"
    _description = "Distribution alimentaire"
    _inherit = ["mail.thread"]
    _order = "distribution_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="set null", check_company=True, index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="set null", check_company=True, index=True)
    ration_id = fields.Many2one("gest_agri.feed.ration", string="Ration", ondelete="set null", check_company=True, index=True)

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------
    distribution_date = fields.Date(string="Date de distribution", required=True, index=True)
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # Lignes
    # ------------------------------------------------------------------
    line_ids = fields.One2many("gest_agri.feed.distribution.line", "distribution_id", string="Aliments distribués")

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Terminée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------
    total_quantity = fields.Float(string="Quantité totale", compute="_compute_total_quantity", digits=(16, 3))

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Resolve the same state default the ORM would use, including a
        # caller-provided default_state, then validate every item before
        # allocating sequences or creating any record.
        defaults = self.default_get(["state"])
        for vals in vals_list:
            requested_state = vals.get("state", defaults.get("state", "draft"))
            if requested_state != "draft":
                raise ValidationError(self.env._("Une distribution doit être créée à l'état brouillon."))
            # Make the invariant explicit so a context default cannot be
            # re-applied later by the ORM create pipeline.
            vals["state"] = "draft"
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.feed.distribution")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.feed.distribution » est introuvable."))
                vals["name"] = ref
            # animal ou lot
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une distribution doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une distribution ne peut concerner à la fois un animal et un lot."))
            self._check_coherence(vals)
            self._check_reference_access(vals)
        return super().create(vals_list)

    def _check_reference_access(self, vals):
        farm = self.env["gest_agri.farm"].browse(vals.get("farm_id"))
        farm.check_access("write")
        for field, model in (
            ("site_id", "gest_agri.site"),
            ("animal_id", "gest_agri.animal"),
            ("lot_id", "gest_agri.animal.lot"),
            ("ration_id", "gest_agri.feed.ration"),
        ):
            record = self.env[model].browse(vals.get(field))
            if record:
                record.check_access("read")

    @api.model
    def _check_coherence(self, vals):
        farm_id = vals.get("farm_id")
        if bool(vals.get("animal_id")) == bool(vals.get("lot_id")):
            raise ValidationError(self.env._("Une distribution doit concerner soit un animal, soit un lot."))
        if vals.get("animal_id") and farm_id:
            animal = self.env["gest_agri.animal"].browse(vals["animal_id"])
            if animal.farm_id.id != farm_id:
                raise ValidationError(self.env._("L'animal n'appartient pas à l'exploitation."))
            if vals.get("ration_id"):
                ration = self.env["gest_agri.feed.ration"].browse(vals["ration_id"])
                if ration.farm_id.id != farm_id:
                    raise ValidationError(self.env._("La ration n'appartient pas à l'exploitation."))
                if ration.species_id and animal.species_id and ration.species_id != animal.species_id:
                    raise ValidationError(self.env._("La ration n'est pas compatible avec l'espèce de l'animal."))
        if vals.get("lot_id") and farm_id:
            lot = self.env["gest_agri.animal.lot"].browse(vals["lot_id"])
            if lot.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))
            if vals.get("ration_id"):
                ration = self.env["gest_agri.feed.ration"].browse(vals["ration_id"])
                if ration.farm_id.id != farm_id:
                    raise ValidationError(self.env._("La ration n'appartient pas à l'exploitation."))
                if ration.species_id and lot.species_id and ration.species_id != lot.species_id:
                    raise ValidationError(self.env._("La ration n'est pas compatible avec l'espèce du lot."))
        if vals.get("site_id") and farm_id:
            site = self.env["gest_agri.site"].browse(vals["site_id"])
            if site.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("line_ids", "line_ids.quantity")
    def _compute_total_quantity(self):
        for dist in self:
            dist.total_quantity = sum(l.quantity for l in dist.line_ids)

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if not self:
            return super().write(vals)
        if "line_ids" in vals:
            # Check every child command before the ORM starts applying the
            # One2many command list. The savepoint below also guarantees that
            # any later ORM constraint failure rolls the entire command list
            # back when the caller catches the exception.
            self.check_access("write")
            # Validate commands for each distribution individually to ensure
            # correct prevalidation even for multi-record writes.
            for dist in self:
                dist._check_line_commands(vals["line_ids"])
        protected = {"farm_id", "animal_id", "lot_id", "ration_id"}
        for dist in self:
            if dist.state in ("done", "cancelled") and (protected & set(vals)):
                raise UserError(self.env._("La distribution « %s » est terminée ou annulée.", dist.display_name))
            if dist.state in ("done", "cancelled") and (set(vals) - {"notes", "active"}):
                raise UserError(self.env._("La distribution « %s » est terminée ou annulée.", dist.display_name))
        if "state" in vals:
            for dist in self:
                if dist.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        coherence_fields = {"farm_id", "site_id", "animal_id", "lot_id", "ration_id"}
        if coherence_fields & set(vals):
            for dist in self:
                effective_vals = {
                    field: vals.get(field, dist[field].id)
                    for field in coherence_fields
                }
                self._check_coherence(effective_vals)
                self._check_reference_access(effective_vals)
        if "line_ids" in vals:
            with self.env.cr.savepoint():
                return super().write(vals)
        return super().write(vals)

    def _check_line_commands(self, commands):
        Line = self.env["gest_agri.feed.distribution.line"]

        # This prevalidation is designed for single-record writes. Multi-record
        # writes with One2many commands are not fully supported by the
        # prevalidation; the ORM will still enforce ACL at execution time.
        if len(self) != 1:
            # For multi-record writes, skip prevalidation and rely on the
            # ORM's built-in ACL checks at execution time.
            return

        # Track the logical set of line IDs currently in the parent, updated
        # after each command, so that subsequent prevalidation covers all
        # lines that will actually be affected (fail-fast).
        # Start with the lines initially linked to the parent.
        current_line_ids = set(self.mapped("line_ids").ids)

        # Track the number of lines created by CREATE commands that are not
        # yet materialized. These lines cannot be tracked by ID but their
        # presence is noted so that subsequent CLEAR/SET prevalidation is
        # aware that additional lines will be affected. The ORM enforces ACL
        # at execution time for these lines.
        created_count = 0

        def check_parents(distributions):
            distributions = distributions.exists()
            if not distributions:
                raise ValidationError(self.env._("La distribution source ou cible n'existe pas."))
            distributions.check_access("read")
            distributions.check_access("write")
            Line._check_distribution_draft(distributions)

        def check_lines(lines, operation):
            lines = lines.exists()
            if not lines:
                return lines
            lines.check_access(operation)
            sources = lines.mapped("distribution_id")
            check_parents(sources)
            return lines

        for command in commands or ():
            operation, record_id, payload = command
            if operation == Command.CREATE:
                for distribution in self:
                    check_parents(distribution)
                    feed = self.env["gest_agri.feed"].browse(payload.get("feed_id"))
                    if feed:
                        feed.check_access("read")
                    if "quantity" in payload and payload["quantity"] <= 0:
                        raise ValidationError(self.env._("La quantité doit être strictement positive."))
                # Created lines (NewId) are not yet materialized in the database.
                # They cannot be tracked by ID in current_line_ids. The ORM will
                # enforce ACL at execution time when the line is created and then
                # potentially unlinked by a subsequent CLEAR/SET/DELETE. We track
                # the count so that subsequent commands know additional lines
                # exist, but their ACL is checked by the framework.
                created_count += 1
            elif operation == Command.UPDATE:
                line = check_lines(Line.browse(record_id), "write")
                if line and "distribution_id" in payload:
                    target = self.env["gest_agri.feed.distribution"].browse(payload["distribution_id"]).exists()
                    check_parents(target)
                    if any(source.company_id != target.company_id for source in line.mapped("distribution_id")):
                        raise ValidationError(self.env._("La ligne ne peut pas changer de société."))
                if line and "feed_id" in payload:
                    self.env["gest_agri.feed"].browse(payload["feed_id"]).check_access("read")
                if "quantity" in payload and payload["quantity"] <= 0:
                    raise ValidationError(self.env._("La quantité doit être strictement positive."))
            elif operation in (Command.DELETE, Command.UNLINK):
                check_lines(Line.browse(record_id), "unlink")
                # Update tracked state: line removed from parent.
                current_line_ids.discard(record_id)
            elif operation == Command.LINK:
                line = check_lines(Line.browse(record_id), "write")
                target = self[-1:]
                check_parents(target)
                if line and any(source.company_id != target.company_id for source in line.mapped("distribution_id")):
                    raise ValidationError(self.env._("La ligne ne peut pas changer de société."))
                # Update tracked state: line added to parent.
                if record_id:
                    current_line_ids.add(record_id)
            elif operation == Command.CLEAR:
                # Pre-validate unlink on all lines currently in the parent,
                # including those introduced by preceding LINK/SET commands.
                lines_to_check = Line.browse(list(current_line_ids))
                check_lines(lines_to_check, "unlink")
                # Note: lines created by CREATE (NewId) are not tracked by ID
                # and cannot be pre-validated. The ORM will enforce ACL at
                # execution time when they are created and then unlinked.
                # Update tracked state: parent cleared.
                current_line_ids.clear()
                created_count = 0
            elif operation == Command.SET:
                target_ids = set(payload or [])
                # Lines that will be removed: currently in parent but not in target.
                removed_ids = current_line_ids - target_ids
                removed = Line.browse(list(removed_ids))
                linked = check_lines(Line.browse(list(target_ids)), "write")
                if removed:
                    check_lines(removed, "unlink")
                target = self[-1:]
                check_parents(target)
                if linked and any(source.company_id != target.company_id for source in linked.mapped("distribution_id")):
                    raise ValidationError(self.env._("La ligne ne peut pas changer de société."))
                # Update tracked state: parent now contains exactly target_ids.
                current_line_ids = set(target_ids)
            else:
                raise ValueError(self.env._("Commande One2many inconnue : %s", operation))

    @api.constrains("farm_id", "site_id", "animal_id", "lot_id", "ration_id")
    def _check_relations_coherence(self):
        for dist in self:
            self._check_coherence({
                "farm_id": dist.farm_id.id,
                "site_id": dist.site_id.id,
                "animal_id": dist.animal_id.id,
                "lot_id": dist.lot_id.id,
                "ration_id": dist.ration_id.id,
            })

    def _apply_state(self, target, allowed):
        """Apply one checked transition without trusting a caller-controlled context."""
        self._check_allowed(allowed)
        return super(GestAgriFeedDistribution, self).write({"state": target})

    def action_done(self):
        self._apply_state("done", {"draft"})

    def action_cancel(self):
        # Existing write() lock makes completed distributions immutable. Keep
        # that effective rule until the business owner decides whether a done
        # distribution may be cancelled.
        self._apply_state("cancelled", {"draft"})

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Terminée", "cancelled": "Annulée"}
        for dist in self:
            if dist.state not in allowed:
                raise UserError(self.env._("Transition impossible : la distribution « %(d)s » est à l'état « %(s)s ».", d=dist.display_name, s=labels.get(dist.state, dist.state)))

    def unlink(self):
        for dist in self:
            if dist.state != "draft":
                raise UserError(self.env._("La distribution « %s » ne peut être supprimée qu'en brouillon.", dist.display_name))
        return super().unlink()


class GestAgriFeedDistributionLine(models.Model):
    _name = "gest_agri.feed.distribution.line"
    _description = "Ligne de distribution alimentaire"
    _order = "sequence, id"
    _check_company_auto = True

    distribution_id = fields.Many2one(
        "gest_agri.feed.distribution", string="Distribution", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    farm_id = fields.Many2one(
        related="distribution_id.farm_id", string="Exploitation", store=True,
        readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="distribution_id.company_id", string="Société", store=True,
        readonly=True, precompute=True, index=True,
    )
    feed_id = fields.Many2one(
        "gest_agri.feed", string="Aliment", required=True, ondelete="restrict",
        check_company=True, index=True,
    )
    quantity = fields.Float(string="Quantité", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", required=True, ondelete="restrict")
    sequence = fields.Integer(string="Séquence", default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            distribution = self.env["gest_agri.feed.distribution"].browse(vals.get("distribution_id"))
            distribution.check_access("write")
            self._check_distribution_draft(distribution)
            feed = self.env["gest_agri.feed"].browse(vals.get("feed_id"))
            feed.check_access("read")
        return super().create(vals_list)

    def write(self, vals):
        if not self:
            return super().write(vals)
        self.check_access("write")
        sources = self.mapped("distribution_id").exists()
        if any(not line.distribution_id for line in self):
            raise ValidationError(self.env._("Chaque ligne doit rester rattachée à une distribution."))
        self._check_distribution_access_and_draft(sources)
        if "distribution_id" in vals:
            targets = self.env["gest_agri.feed.distribution"].browse(vals["distribution_id"]).exists()
            if len(targets) != 1:
                raise ValidationError(self.env._("La distribution cible doit exister."))
            self._check_distribution_access_and_draft(targets)
            if any(source.company_id != targets.company_id for source in sources):
                raise ValidationError(self.env._("La ligne ne peut pas changer de société."))
        feeds = (
            self.env["gest_agri.feed"].browse(vals["feed_id"])
            if vals.get("feed_id") else self.mapped("feed_id")
        )
        feeds.check_access("read")
        return super().write(vals)

    @api.model
    def _check_distribution_draft(self, distributions):
        if any(distribution.state != "draft" for distribution in distributions):
            raise UserError(self.env._("Les lignes ne peuvent être modifiées que sur une distribution en brouillon."))

    @api.model
    def _check_distribution_access_and_draft(self, distributions):
        distributions.check_access("read")
        distributions.check_access("write")
        self._check_distribution_draft(distributions)

    def unlink(self):
        self.mapped("distribution_id").check_access("write")
        self._check_distribution_draft(self.mapped("distribution_id"))
        return super().unlink()

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité doit être strictement positive."))

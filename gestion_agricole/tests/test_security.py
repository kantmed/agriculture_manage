# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_a = cls._create_user("agri_user_a", [cls.base_user, cls.group_user])
        cls.user_b = cls._create_user("agri_user_b", [cls.base_user, cls.group_user])
        cls.manager = cls._create_user(
            "agri_manager", [cls.base_user, cls.group_manager]
        )
        cls.admin = cls._create_user("agri_admin", [cls.base_user, cls.group_admin])

        # Un responsable système distinct pour éviter que le responsable
        # agricole testé soit automatiquement gestionnaire des exploitations.
        cls.farm_owner = cls.env["res.users"].create(
            {
                "name": "Propriétaire technique",
                "login": "agri_farm_owner",
                "email": "agri_farm_owner@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine A",
                "code": "DOM-A",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine B",
                "code": "DOM-B",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle A",
                "code": "PA",
                "farm_id": cls.farm_a.id,
                "area": 10.0,
            }
        )
        cls.plot_b = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle B",
                "code": "PB",
                "farm_id": cls.farm_b.id,
                "area": 10.0,
            }
        )

        cls.access_a_user = cls.env["gest_agri.farm.access"].create(
            {
                "farm_id": cls.farm_a.id,
                "user_id": cls.user_a.id,
                "role": "user",
            }
        )
        cls.access_b_user = cls.env["gest_agri.farm.access"].create(
            {
                "farm_id": cls.farm_b.id,
                "user_id": cls.user_b.id,
                "role": "user",
            }
        )
        cls.access_a_manager = cls.env["gest_agri.farm.access"].create(
            {
                "farm_id": cls.farm_a.id,
                "user_id": cls.manager.id,
                "role": "manager",
            }
        )

    @classmethod
    def _create_user(cls, login, groups):
        # Les groupes peuvent être fournis sous forme d'enregistrements ou
        # d'identifiants : on accepte les deux formes.
        group_ids = [
            group.id if hasattr(group, "id") else int(group) for group in groups
        ]
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": cls.company.id,
                    "company_ids": [(6, 0, [cls.company.id])],
                    "group_ids": [(6, 0, group_ids)],
                }
            )
        )

    def test_farm_isolation(self):
        visible_a = self.env["gest_agri.farm"].with_user(self.user_a).search([])
        visible_b = self.env["gest_agri.farm"].with_user(self.user_b).search([])
        self.assertIn(self.farm_a, visible_a)
        self.assertNotIn(self.farm_b, visible_a)
        self.assertIn(self.farm_b, visible_b)
        self.assertNotIn(self.farm_a, visible_b)
        with self.assertRaises(AccessError):
            self.farm_b.with_user(self.user_a).read(["name"])

    def test_child_isolation(self):
        plots_a = self.env["gest_agri.plot"].with_user(self.user_a).search([])
        self.assertIn(self.plot_a, plots_a)
        self.assertNotIn(self.plot_b, plots_a)
        with self.assertRaises(AccessError):
            self.plot_b.with_user(self.user_a).read(["name"])

    def test_user_cannot_write_farm(self):
        with self.assertRaises(AccessError):
            self.farm_a.with_user(self.user_a).write({"name": "Modification interdite"})

    def test_user_cannot_create_child(self):
        with self.assertRaises(AccessError):
            self.env["gest_agri.plot"].with_user(self.user_a).create(
                {
                    "name": "Parcelle interdite",
                    "code": "INTERDIT",
                    "farm_id": self.farm_a.id,
                    "area": 1.0,
                }
            )

    def test_manager_can_write_managed_farm(self):
        self.farm_a.with_user(self.manager).write({"name": "Domaine A modifié"})
        self.assertEqual(self.farm_a.name, "Domaine A modifié")
        with self.assertRaises(AccessError):
            self.farm_b.with_user(self.manager).write({"name": "Interdit"})

    def test_manager_can_create_child(self):
        site = (
            self.env["gest_agri.site"]
            .with_user(self.manager)
            .create(
                {
                    "name": "Site géré",
                    "code": "GERE",
                    "farm_id": self.farm_a.id,
                }
            )
        )
        self.assertEqual(site.farm_id, self.farm_a)
        with self.assertRaises(AccessError):
            self.env["gest_agri.site"].with_user(self.manager).create(
                {
                    "name": "Site interdit",
                    "code": "INTERDIT",
                    "farm_id": self.farm_b.id,
                }
            )

    def test_manager_cannot_edit_own_access(self):
        with self.assertRaises(AccessError):
            self.access_a_manager.with_user(self.manager).write({"role": "admin"})

    def test_admin_can_manage_access(self):
        self.access_a_manager.with_user(self.admin).write({"role": "admin"})
        self.assertEqual(self.access_a_manager.role, "admin")

    def test_plot_write_permissions(self):
        with self.assertRaises(AccessError):
            self.plot_a.with_user(self.user_a).write({"name": "Interdit"})
        self.plot_a.with_user(self.manager).write({"name": "Parcelle A modifiée"})
        self.assertEqual(self.plot_a.name, "Parcelle A modifiée")
        self.plot_b.with_user(self.admin).unlink()
        self.assertFalse(self.plot_b.exists())

    def test_farm_access_unique_active(self):
        """Un second droit d'accès actif pour le même couple est refusé."""
        import psycopg2

        with self.assertRaises((psycopg2.errors.UniqueViolation, ValidationError)):
            self.env["gest_agri.farm.access"].create(
                {
                    "farm_id": self.farm_a.id,
                    "user_id": self.user_a.id,
                    "role": "manager",
                }
            )
            self.env.flush_all()

    def test_farm_access_notes_default_and_modification(self):
        """Les notes d'une habilitation sont vides par défaut, puis modifiables."""
        self.assertFalse(self.access_a_user.notes)
        self.access_a_user.write(
            {"notes": "Habilitation accordée pour la saison 2026."}
        )
        self.assertEqual(
            self.access_a_user.notes, "Habilitation accordée pour la saison 2026."
        )
        reloaded = self.env["gest_agri.farm.access"].browse(self.access_a_user.id)
        self.assertEqual(
            reloaded.notes, "Habilitation accordée pour la saison 2026."
        )
        self.access_a_user.write({"notes": False})
        self.assertFalse(self.access_a_user.notes)

    def test_farm_access_notes_creation_and_security_preserved(self):
        """La création avec notes fonctionne et l'isolation des habilitations reste intacte."""
        access = self.env["gest_agri.farm.access"].create(
            {
                "farm_id": self.farm_a.id,
                "user_id": self.user_b.id,
                "role": "user",
                "notes": "Accès temporaire pour la récolte.",
            }
        )
        self.assertEqual(access.notes, "Accès temporaire pour la récolte.")

        # L'utilisateur concerné peut lire ses propres notes.
        own_notes = self.access_a_user.with_user(self.user_a).read(["notes"])
        self.assertEqual(own_notes[0]["notes"], False)

        # Un autre utilisateur ne peut pas lire une habilitation qui ne le concerne pas.
        with self.assertRaises(AccessError):
            self.access_a_user.with_user(self.user_b).read(["notes"])

    def test_farm_access_dates_optional_and_coherent(self):
        """Les dates de validité sont facultatives et acceptent une période cohérente."""
        Access = self.env["gest_agri.farm.access"]

        no_dates = Access.create(
            {"farm_id": self.farm_b.id, "user_id": self.user_a.id, "role": "user"}
        )
        self.assertFalse(no_dates.date_start)
        self.assertFalse(no_dates.date_end)

        start_only = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.manager.id,
                "role": "user",
                "date_start": "2026-01-01",
            }
        )
        self.assertEqual(str(start_only.date_start), "2026-01-01")
        self.assertFalse(start_only.date_end)

        end_only = Access.create(
            {
                "farm_id": self.farm_a.id,
                "user_id": self.user_b.id,
                "role": "user",
                "date_end": "2026-12-31",
            }
        )
        self.assertFalse(end_only.date_start)
        self.assertEqual(str(end_only.date_end), "2026-12-31")

        coherent = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.farm_owner.id,
                "role": "user",
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
            }
        )
        self.assertEqual(str(coherent.date_start), "2026-01-01")
        self.assertEqual(str(coherent.date_end), "2026-12-31")

        same_day = Access.create(
            {
                "farm_id": self.farm_a.id,
                "user_id": self.admin.id,
                "role": "user",
                "date_start": "2026-06-15",
                "date_end": "2026-06-15",
            }
        )
        self.assertEqual(str(same_day.date_start), "2026-06-15")
        self.assertEqual(str(same_day.date_end), "2026-06-15")

    def test_farm_access_dates_incoherent_rejected_and_correction(self):
        """Une période incohérente est refusée à la création comme à la modification."""
        Access = self.env["gest_agri.farm.access"]

        with self.assertRaises(ValidationError):
            Access.create(
                {
                    "farm_id": self.farm_b.id,
                    "user_id": self.user_a.id,
                    "role": "user",
                    "date_start": "2026-12-31",
                    "date_end": "2026-01-01",
                }
            )

        with self.assertRaises(ValidationError):
            self.access_a_user.write(
                {"date_start": "2026-12-31", "date_end": "2026-01-01"}
            )

        # Une correction cohérente est acceptée après l'erreur.
        self.access_a_user.write(
            {"date_start": "2026-01-01", "date_end": "2026-12-31"}
        )
        reloaded = Access.browse(self.access_a_user.id)
        self.assertEqual(str(reloaded.date_start), "2026-01-01")
        self.assertEqual(str(reloaded.date_end), "2026-12-31")

    def test_farm_access_is_expired_compute_and_update(self):
        """Le statut d'expiration suit la date du jour et les modifications de date_end."""
        Access = self.env["gest_agri.farm.access"]
        today = fields.Date.context_today(Access)
        past = today - timedelta(days=1)
        future = today + timedelta(days=1)

        no_end = Access.create(
            {"farm_id": self.farm_b.id, "user_id": self.user_a.id, "role": "user"}
        )
        expired = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.manager.id,
                "role": "user",
                "date_end": past,
            }
        )
        ends_today = Access.create(
            {
                "farm_id": self.farm_a.id,
                "user_id": self.user_b.id,
                "role": "user",
                "date_end": today,
            }
        )
        not_yet = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.farm_owner.id,
                "role": "user",
                "date_end": future,
            }
        )

        self.assertFalse(no_end.is_expired)
        self.assertTrue(expired.is_expired)
        self.assertFalse(ends_today.is_expired)
        self.assertFalse(not_yet.is_expired)

        # La modification de date_end actualise immédiatement le calcul.
        not_yet.write({"date_end": past})
        self.assertTrue(not_yet.is_expired)
        not_yet.write({"date_end": today})
        self.assertFalse(not_yet.is_expired)
        not_yet.write({"date_end": False})
        self.assertFalse(not_yet.is_expired)

    def test_farm_access_is_expired_search(self):
        """Les filtres =/!= True/False traduisent correctement l'expiration."""
        Access = self.env["gest_agri.farm.access"]
        today = fields.Date.context_today(Access)
        past = today - timedelta(days=1)
        future = today + timedelta(days=1)

        expired = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.user_a.id,
                "role": "user",
                "date_end": past,
            }
        )
        ends_today = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.manager.id,
                "role": "user",
                "date_end": today,
            }
        )
        no_end = Access.create(
            {
                "farm_id": self.farm_a.id,
                "user_id": self.user_b.id,
                "role": "user",
            }
        )
        not_yet = Access.create(
            {
                "farm_id": self.farm_b.id,
                "user_id": self.farm_owner.id,
                "role": "user",
                "date_end": future,
            }
        )
        ids = (expired | ends_today | no_end | not_yet).ids

        expired_found = Access.search([("id", "in", ids), ("is_expired", "=", True)])
        self.assertEqual(expired_found, expired)

        not_expired_found = Access.search(
            [("id", "in", ids), ("is_expired", "=", False)]
        )
        self.assertEqual(
            set(not_expired_found.ids), {ends_today.id, no_end.id, not_yet.id}
        )

        expired_ne = Access.search([("id", "in", ids), ("is_expired", "!=", True)])
        self.assertEqual(expired_ne, ends_today | no_end | not_yet)

        not_expired_ne = Access.search(
            [("id", "in", ids), ("is_expired", "!=", False)]
        )
        self.assertEqual(not_expired_ne, expired)

    def test_expired_access_keeps_effective_rights(self):
        """Une habilitation expirée reste active et continue d'accorder les mêmes droits."""
        Access = self.env["gest_agri.farm.access"]
        today = fields.Date.context_today(Access)
        self.access_a_user.write({"date_end": today - timedelta(days=1)})

        self.assertTrue(self.access_a_user.is_expired)
        self.assertTrue(self.access_a_user.active)

        visible = self.env["gest_agri.farm"].with_user(self.user_a).search([])
        self.assertIn(self.farm_a, visible)
        self.assertEqual(self.farm_a.with_user(self.user_a).read(["name"])[0]["name"],
                         self.farm_a.name)

    def test_multi_company_isolation(self):
        """Teste l'isolation entre deux sociétés distinctes."""
        other_company = self.env["res.company"].create({"name": "Société B"})

        # Ferme dans la Société B
        farm_b = self.env["gest_agri.farm"].create({
            "name": "Ferme Société B",
            "code": "FARM-B",
            "company_id": other_company.id,
            "total_area": 50.0,
        })

        # L'utilisateur de la Société A ne doit pas voir la ferme de la Société B
        visible_a = self.env["gest_agri.farm"].with_user(self.user_a).search([])
        self.assertNotIn(farm_b, visible_a)

        # Test de modification non autorisée : utilisateur A tente de modifier farm_b
        with self.assertRaises(AccessError):
            farm_b.with_user(self.user_a).write({"name": "Modification interdite"})

        # Test de modification autorisée : l'administrateur agricole peut
        # modifier une exploitation de sa société (la Société B n'est pas dans
        # ses sociétés actives : l'accès doit être refusé).
        with self.assertRaises(AccessError):
            farm_b.with_user(self.admin).write({"name": "Modification admin"})

    def test_user_belongs_to_two_companies(self):
        """Un utilisateur multi-sociétés ne voit que les exploitations
        auxquelles il a explicitement accès."""
        other_company = self.env["res.company"].create({"name": "Société B"})

        user_multi = self.env["res.users"].create({
            "name": "Utilisateur multi",
            "login": "multi_user",
            "email": "multi@example.com",
            "company_id": self.company.id,
            "company_ids": [(6, 0, [self.company.id, other_company.id])],
            "group_ids": [(6, 0, [self.base_user.id, self.group_user.id])],
        })

        farm_a = self.env["gest_agri.farm"].create({
            "name": "Ferme A",
            "code": "FARM-A",
            "company_id": self.company.id,
        })
        farm_b = self.env["gest_agri.farm"].create({
            "name": "Ferme B",
            "code": "FARM-B",
            "company_id": other_company.id,
        })

        # Sans droit d'accès explicite, aucune exploitation n'est visible :
        # le domaine d'accès du groupe « Utilisateur agricole » repose sur
        # les droits d'accès, pas sur la seule appartenance à une société.
        visible = self.env["gest_agri.farm"].with_user(user_multi).search([])
        self.assertNotIn(farm_a, visible)
        self.assertNotIn(farm_b, visible)

        # Avec un droit d'accès explicite sur la ferme A, celle-ci devient
        # visible, mais pas la ferme B.
        self.env["gest_agri.farm.access"].create({
            "farm_id": farm_a.id,
            "user_id": user_multi.id,
            "role": "user",
        })
        visible = self.env["gest_agri.farm"].with_user(user_multi).search([])
        self.assertIn(farm_a, visible)
        self.assertNotIn(farm_b, visible)

    def test_manager_cannot_modify_other_company_farm(self):
        """Un responsable ne doit pas voir ni modifier une exploitation
        d'une société à laquelle il n'appartient pas."""
        other_company = self.env["res.company"].create({"name": "Société B"})

        farm_b = self.env["gest_agri.farm"].create({
            "name": "Ferme Société B",
            "code": "FARM-B",
            "company_id": other_company.id,
            "total_area": 50.0,
            "manager_id": self.env.user.id,
        })

        manager_a = self._create_user(
            "agri_manager_a", [self.base_user.id, self.group_manager.id]
        )

        # L'exploitation d'une autre société n'est pas visible
        visible = self.env["gest_agri.farm"].with_user(manager_a).search([])
        self.assertNotIn(farm_b, visible)

        # ... et ne peut pas être modifiée
        with self.assertRaises(AccessError):
            farm_b.with_user(manager_a).write({"name": "Modification interdite"})

    def test_manager_can_modify_own_company_farm(self):
        """Un responsable peut modifier une exploitation de sa société dont
        il a le rôle Responsable."""
        self.farm_a.with_user(self.manager).write(
            {"name": "Domaine A renommé par le responsable"}
        )
        self.assertEqual(self.farm_a.name, "Domaine A renommé par le responsable")
        self.assertIn(self.farm_a, self.manager.gest_agri_managed_farm_ids)

    def test_access_deactivation(self):
        """Teste la désactivation d'un accès."""
        access = self.access_a_user
        self.assertTrue(access.active)

        # Archivage de l'accès
        access.write({"active": False})
        self.assertFalse(access.active)

        # L'utilisateur ne doit plus pouvoir accéder à la ferme via les
        # droits d'accès. L'invalidation du cache de sécurité est réalisée
        # par le module lui-même (pas d'invalidation manuelle ici, afin que
        # le test valide réellement le comportement du module).
        visible = self.env["gest_agri.farm"].with_user(self.user_a).search([])
        self.assertNotIn(self.farm_a, visible)

    def test_bulk_operations(self):
        """Teste les opérations sur plusieurs enregistrements."""
        farm_c = self.env["gest_agri.farm"].create({
            "name": "Ferme B",
            "code": "FARM-C",
            "company_id": self.company.id,
            "total_area": 50.0,
        })

        # Modification en lot de plusieurs exploitations gérées
        farms = self.env["gest_agri.farm"].browse([self.farm_a.id, farm_c.id])
        farms.write({"name": "Fermes modifiées"})
        self.assertEqual(self.farm_a.name, "Fermes modifiées")
        self.assertEqual(farm_c.name, "Fermes modifiées")

    def _create_feed_security_fixture(self):
        species = self.env["gest_agri.livestock.species"].create(
            {"name": "Espèce sécurité", "code": "SEC-SP", "company_id": False}
        )
        feed = self.env["gest_agri.feed"].create({
            "name": "Aliment sécurité A", "code": "SEC-FEED-A",
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
            "company_id": self.company.id,
        })
        animal_a = self.env["gest_agri.animal"].create({
            "name": "Animal sécurité A", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_a.id,
        })
        animal_b = self.env["gest_agri.animal"].create({
            "name": "Animal sécurité B", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_b.id,
        })
        ration = self.env["gest_agri.feed.ration"].create({
            "name": "Ration sécurité A", "species_id": species.id,
            "company_id": self.company.id, "farm_id": self.farm_a.id,
        })
        ration_line = self.env["gest_agri.feed.ration.line"].create({
            "ration_id": ration.id, "feed_id": feed.id, "quantity": 2,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        distribution_a = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal_a.id,
            "distribution_date": "2026-01-01",
        })
        distribution_b = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_b.id, "animal_id": animal_b.id,
            "distribution_date": "2026-01-01",
        })
        line_a = self.env["gest_agri.feed.distribution.line"].create({
            "distribution_id": distribution_a.id, "feed_id": feed.id,
            "quantity": 1, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        line_b = self.env["gest_agri.feed.distribution.line"].create({
            "distribution_id": distribution_b.id, "feed_id": feed.id,
            "quantity": 1, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        return species, feed, ration, ration_line, distribution_a, distribution_b, line_a, line_b

    def _create_managed_destination_farm(self, code):
        farm = self.env["gest_agri.farm"].create({
            "name": f"Destination {code}", "code": code,
            "company_id": self.company.id, "manager_id": self.farm_owner.id,
        })
        self.env["gest_agri.farm.access"].create({
            "farm_id": farm.id, "user_id": self.manager.id, "role": "manager",
        })
        return farm

    def _create_lot_with_fixture_animal(self, animal, name):
        lot = self.env["gest_agri.animal.lot"].create({
            "name": name, "species_id": animal.species_id.id,
            "farm_id": animal.farm_id.id,
        })
        animal.write({"lot_id": lot.id})
        return lot

    def test_lot_move_refuses_to_separate_active_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_with_fixture_animal(animal, "Lot avec animal actif")
        target = self._create_managed_destination_farm("SEC-LOT-ACTIVE")

        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"farm_id": target.id})

        self.assertEqual(lot.farm_id, self.farm_a)
        self.assertEqual(animal.farm_id, self.farm_a)
        self.assertEqual(animal.lot_id, lot)

    def test_lot_move_checks_archived_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_with_fixture_animal(animal, "Lot avec membre archivé")
        animal.write({"active": False})
        target = self._create_managed_destination_farm("SEC-LOT-ARCH")

        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"farm_id": target.id})

        self.assertFalse(animal.active)
        self.assertEqual(lot.farm_id, self.farm_a)
        self.assertEqual(animal.farm_id, self.farm_a)
        self.assertEqual(animal.lot_id, lot)

    def test_lot_move_checks_archived_only_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_with_fixture_animal(animal, "Lot avec seul membre archivé")
        animal.write({"active": False})
        target = self._create_managed_destination_farm("SEC-LOT-ONLY-ARCH")

        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"farm_id": target.id})

        self.assertEqual(lot.farm_id, self.farm_a)
        self.assertEqual(animal.farm_id, self.farm_a)

    def test_lot_move_checks_every_member_when_one_is_archived(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        active_animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        archived_animal = self.env["gest_agri.animal"].create({
            "name": "Animal archivé du lot", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_a.id,
        })
        lot = self._create_lot_with_fixture_animal(active_animal, "Lot mixte actif/archivé")
        archived_animal.write({"lot_id": lot.id, "active": False})
        target = self._create_managed_destination_farm("SEC-LOT-MIXED")

        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"farm_id": target.id})

        self.assertEqual(lot.farm_id, self.farm_a)
        self.assertEqual(active_animal.farm_id, self.farm_a)
        self.assertEqual(archived_animal.farm_id, self.farm_a)
        self.assertEqual(archived_animal.lot_id, lot)

    def test_bulk_lot_move_checks_archived_members_per_lot(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        populated_lot = self._create_lot_with_fixture_animal(animal, "Lot plein pour lot multiple")
        animal.write({"active": False})
        empty_lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot vide pour lot multiple", "species_id": animal.species_id.id,
            "farm_id": self.farm_a.id,
        })
        target = self._create_managed_destination_farm("SEC-LOT-BULK")
        lots = (empty_lot | populated_lot).with_user(self.manager)

        with self.assertRaises(ValidationError):
            lots.write({"farm_id": target.id})

        self.assertEqual(empty_lot.farm_id, self.farm_a)
        self.assertEqual(populated_lot.farm_id, self.farm_a)
        self.assertEqual(animal.farm_id, self.farm_a)

    def test_bulk_lot_move_failure_does_not_partially_move_records(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        incompatible_lot = self._create_lot_with_fixture_animal(animal, "Lot incompatible en tête")
        empty_lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot vide en second", "species_id": species.id,
            "farm_id": self.farm_a.id,
        })
        target = self._create_managed_destination_farm("SEC-LOT-ATOMIC")
        lots = (incompatible_lot | empty_lot).with_user(self.manager)

        with self.assertRaises(ValidationError):
            lots.write({"farm_id": target.id})

        self.assertEqual(incompatible_lot.farm_id, self.farm_a)
        self.assertEqual(empty_lot.farm_id, self.farm_a)
        self.assertEqual(animal.farm_id, self.farm_a)

    def test_lot_move_rejects_member_site_mismatch(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        lot_site = self.env["gest_agri.site"].create({
            "name": "Site du lot", "code": "SEC-LOT-SITE-A", "farm_id": self.farm_a.id,
        })
        animal_site = self.env["gest_agri.site"].create({
            "name": "Site de l'animal", "code": "SEC-LOT-SITE-B", "farm_id": self.farm_a.id,
        })
        animal = self.env["gest_agri.animal"].create({
            "name": "Animal site différent", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_a.id, "site_id": animal_site.id,
        })
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot site différent", "species_id": species.id,
            "farm_id": self.farm_a.id,
        })
        animal.write({"lot_id": lot.id})

        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"site_id": lot_site.id})

        self.assertFalse(lot.site_id)
        self.assertEqual(animal.site_id, animal_site)

    def test_feed_ration_line_permissions_by_role_and_company(self):
        species, feed, ration, line, *_ = self._create_feed_security_fixture()

        self.assertEqual(
            self.env["gest_agri.feed.ration.line"].with_user(self.user_a).search(
                [("id", "=", line.id)]
            ),
            line,
        )
        with self.assertRaises(AccessError):
            line.with_user(self.user_a).write({"quantity": 3})
        with self.assertRaises(AccessError):
            self.env["gest_agri.feed.ration.line"].with_user(self.user_a).create({
                "ration_id": ration.id, "feed_id": feed.id, "quantity": 3,
                "uom_id": self.env.ref("uom.product_uom_kgm").id,
            })

        manager_line = self.env["gest_agri.feed.ration.line"].with_user(self.manager).create({
            "ration_id": ration.id, "feed_id": feed.id, "quantity": 4,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        manager_line.write({"quantity": 5})
        self.assertEqual(manager_line.quantity, 5)
        admin_line = self.env["gest_agri.feed.ration.line"].with_user(self.admin).create({
            "ration_id": ration.id, "feed_id": feed.id, "quantity": 6,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        admin_line.unlink()

        other_company = self.env["res.company"].create({"name": "Société ration sécurité"})
        other_species = self.env["gest_agri.livestock.species"].create({
            "name": "Espèce société B", "code": "SEC-SP-B", "company_id": other_company.id,
        })
        other_feed = self.env["gest_agri.feed"].create({
            "name": "Aliment société B", "code": "SEC-FEED-B",
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
            "company_id": other_company.id,
        })
        other_ration = self.env["gest_agri.feed.ration"].create({
            "name": "Ration société B", "species_id": other_species.id,
            "company_id": other_company.id, "farm_id": self.env["gest_agri.farm"].create({"name": "Ferme ration B", "code": "RAT-B", "company_id": other_company.id}).id,
        })
        other_line = self.env["gest_agri.feed.ration.line"].create({
            "ration_id": other_ration.id, "feed_id": other_feed.id, "quantity": 2,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        with self.assertRaises(AccessError):
            other_line.with_user(self.user_a).read(["quantity"])
        with self.assertRaises(AccessError):
            other_line.with_user(self.manager).read(["quantity"])

        ration_b = self.env["gest_agri.feed.ration"].create({
            "name": "Ration ferme B", "species_id": species.id,
            "company_id": self.company.id, "farm_id": self.farm_b.id,
        })
        line_b = self.env["gest_agri.feed.ration.line"].create({
            "ration_id": ration_b.id, "feed_id": feed.id, "quantity": 2,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        with self.assertRaises(AccessError):
            ration_b.with_user(self.user_a).read(["name"])
        with self.assertRaises(AccessError):
            line_b.with_user(self.user_a).read(["quantity"])
        with self.assertRaises(AccessError):
            ration_b.with_user(self.manager).write({"name": "Tentative hors ferme"})

    def test_manager_cannot_create_ration_with_unmanaged_context_farm(self):
        species = self.env["gest_agri.livestock.species"].create({
            "name": "Espèce défaut ferme", "code": "SEC-DEFAULT-SP", "company_id": False,
        })
        with self.assertRaises(AccessError):
            self.env["gest_agri.feed.ration"].with_user(self.manager).with_context(
                default_farm_id=self.farm_b.id
            ).create({"name": "Ration ferme non gérée", "species_id": species.id})

    def test_feed_distribution_line_permissions_and_farm_isolation(self):
        _, feed, _, _, distribution_a, distribution_b, line_a, line_b = self._create_feed_security_fixture()

        self.assertEqual(
            self.env["gest_agri.feed.distribution.line"].with_user(self.user_a).search(
                [("id", "=", line_a.id)]
            ),
            line_a,
        )
        self.assertFalse(
            self.env["gest_agri.feed.distribution.line"].with_user(self.user_a).search(
                [("id", "=", line_b.id)]
            )
        )
        with self.assertRaises(AccessError):
            line_b.with_user(self.user_a).read(["quantity"])
        with self.assertRaises(AccessError):
            self.env["gest_agri.feed.distribution.line"].with_user(self.user_a).create({
                "distribution_id": distribution_a.id, "feed_id": feed.id,
                "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
            })

        manager_line = self.env["gest_agri.feed.distribution.line"].with_user(self.manager).create({
            "distribution_id": distribution_a.id, "feed_id": feed.id,
            "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        manager_line.write({"quantity": 3})
        with self.assertRaises(AccessError):
            manager_line.write({"distribution_id": distribution_b.id})
        with self.assertRaises(AccessError):
            self.env["gest_agri.feed.distribution.line"].with_user(self.manager).create({
                "distribution_id": distribution_b.id, "feed_id": feed.id,
                "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
            })

        admin_line = self.env["gest_agri.feed.distribution.line"].with_user(self.admin).create({
            "distribution_id": distribution_b.id, "feed_id": feed.id,
            "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        admin_line.unlink()

    def test_distribution_parent_cannot_be_moved_outside_managed_farms(self):
        _, _, _, _, distribution_a, _, _, _ = self._create_feed_security_fixture()
        with self.assertRaises(AccessError):
            distribution_a.with_user(self.manager).write({
                "farm_id": self.farm_b.id,
                "animal_id": self.env["gest_agri.animal"].search(
                    [("farm_id", "=", self.farm_b.id)], limit=1
                ).id,
            })

    def test_distribution_lines_are_locked_with_parent(self):
        _, _, _, _, distribution_a, _, line_a, _ = self._create_feed_security_fixture()
        distribution_a.action_done()
        line_id = line_a.id
        distribution_id = line_a.distribution_id.id
        initial_quantity = line_a.quantity
        initial_total = distribution_a.total_quantity
        with self.assertRaises(UserError):
            line_a.with_user(self.manager).write({"quantity": 7})
        self.assertTrue(line_a.exists())
        self.assertEqual(line_a.id, line_id)
        self.assertEqual(line_a.distribution_id.id, distribution_id)
        self.assertEqual(line_a.quantity, initial_quantity)
        self.assertEqual(distribution_a.total_quantity, initial_total)
        with self.assertRaises(UserError):
            line_a.with_user(self.admin).unlink()
        self.assertTrue(line_a.exists())
        self.assertEqual(line_a.distribution_id.id, distribution_id)
        self.assertEqual(line_a.quantity, initial_quantity)
        self.assertEqual(distribution_a.total_quantity, initial_total)

    def test_distribution_done_line_cannot_be_transferred_to_draft(self):
        species, feed, _, _, source, _, line, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        target = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal.id,
            "distribution_date": "2026-02-01",
        })
        target_line = self.env["gest_agri.feed.distribution.line"].create({
            "distribution_id": target.id, "feed_id": feed.id,
            "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        source.with_user(self.manager).action_done()
        source_ids = source.line_ids.ids
        target_ids = target.line_ids.ids
        source_total = source.total_quantity
        target_total = target.total_quantity
        line_id = line.id
        line_quantity = line.quantity

        with self.assertRaises(UserError):
            line.with_user(self.manager).write({"distribution_id": target.id})

        self.assertTrue(line.exists())
        self.assertEqual(line.id, line_id)
        self.assertEqual(line.distribution_id, source)
        self.assertEqual(line.quantity, line_quantity)
        self.assertEqual(source.line_ids.ids, source_ids)
        self.assertEqual(target.line_ids.ids, target_ids)
        self.assertEqual(source.total_quantity, source_total)
        self.assertEqual(target.total_quantity, target_total)
        self.assertEqual(target_line.distribution_id, target)

    def test_distribution_line_cannot_be_transferred_into_terminal_target(self):
        _, feed, _, _, source, _, line, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        target = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal.id,
            "distribution_date": "2026-02-04",
        })
        self.env["gest_agri.feed.distribution.line"].create({
            "distribution_id": target.id, "feed_id": feed.id,
            "quantity": 2, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        target.with_user(self.manager).action_done()
        source_ids, target_ids = source.line_ids.ids, target.line_ids.ids
        source_total, target_total = source.total_quantity, target.total_quantity

        with self.assertRaises(UserError):
            line.with_user(self.manager).write({"distribution_id": target.id})

        self.assertEqual(line.distribution_id, source)
        self.assertEqual(source.line_ids.ids, source_ids)
        self.assertEqual(target.line_ids.ids, target_ids)
        self.assertEqual(source.total_quantity, source_total)
        self.assertEqual(target.total_quantity, target_total)

    def test_manager_can_transfer_line_between_draft_distributions(self):
        _, _, _, _, source, _, line, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        target = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal.id,
            "distribution_date": "2026-02-05",
        })
        original_quantity = line.quantity

        line.with_user(self.manager).write({"distribution_id": target.id})

        self.assertEqual(line.distribution_id, target)
        self.assertNotIn(line.id, source.line_ids.ids)
        self.assertIn(line.id, target.line_ids.ids)
        self.assertAlmostEqual(source.total_quantity, 0.0)
        self.assertEqual(target.total_quantity, original_quantity)

    def test_manager_cannot_create_distribution_in_terminal_state(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        Distribution = self.env["gest_agri.feed.distribution"].with_user(self.manager)
        names = ["SEC state done create", "SEC state cancelled create"]
        for state, name in zip(("done", "cancelled"), names):
            with self.assertRaises(ValidationError):
                Distribution.create({
                    "name": name, "farm_id": self.farm_a.id,
                    "animal_id": animal.id, "distribution_date": "2026-02-06",
                    "state": state,
                })
        self.assertFalse(self.env["gest_agri.feed.distribution"].search([("name", "in", names)]))

    def test_distribution_line_multi_write_validates_all_sources_first(self):
        species, feed, _, _, source_done, _, done_line, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        source_draft = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal.id,
            "distribution_date": "2026-02-02",
        })
        draft_line = self.env["gest_agri.feed.distribution.line"].create({
            "distribution_id": source_draft.id, "feed_id": feed.id,
            "quantity": 3, "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        target = self.env["gest_agri.feed.distribution"].create({
            "farm_id": self.farm_a.id, "animal_id": animal.id,
            "distribution_date": "2026-02-03",
        })
        source_done.with_user(self.manager).action_done()
        ids_before = {
            source_done.id: source_done.line_ids.ids,
            source_draft.id: source_draft.line_ids.ids,
            target.id: target.line_ids.ids,
        }
        totals_before = (source_done.total_quantity, source_draft.total_quantity, target.total_quantity)

        with self.assertRaises(UserError):
            (done_line | draft_line).with_user(self.manager).write({"distribution_id": target.id})

        self.assertEqual(done_line.distribution_id, source_done)
        self.assertEqual(draft_line.distribution_id, source_draft)
        self.assertEqual(source_done.line_ids.ids, ids_before[source_done.id])
        self.assertEqual(source_draft.line_ids.ids, ids_before[source_draft.id])
        self.assertEqual(target.line_ids.ids, ids_before[target.id])
        self.assertEqual(
            (source_done.total_quantity, source_draft.total_quantity, target.total_quantity),
            totals_before,
        )

    def test_distribution_and_line_reject_cross_company_links(self):
        species, _, _, ration_line, distribution_a, _, _, _ = self._create_feed_security_fixture()
        other_company = self.env["res.company"].create({"name": "Société alimentation B"})
        multi_admin = self.env["res.users"].create({
            "name": "Administrateur multi-sociétés alimentation",
            "login": "agri_feed_multi_admin",
            "email": "agri_feed_multi_admin@example.com",
            "company_id": self.company.id,
            "company_ids": [(6, 0, [self.company.id, other_company.id])],
            "group_ids": [(6, 0, [self.base_user.id, self.group_admin.id])],
        })
        other_feed = self.env["gest_agri.feed"].create({
            "name": "Aliment société B cross-check", "code": "SEC-FEED-CROSS",
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
            "company_id": other_company.id,
        })
        other_ration = self.env["gest_agri.feed.ration"].create({
            "name": "Ration société B cross-check", "species_id": species.id,
            "company_id": other_company.id, "farm_id": self.env["gest_agri.farm"].create({"name": "Ferme ration cross", "code": "RAT-CROSS", "company_id": other_company.id}).id,
        })
        with self.assertRaises(UserError):
            ration_line.with_user(multi_admin).write({"feed_id": other_feed.id})
        with self.assertRaises(UserError):
            distribution_a.with_user(multi_admin).write({"ration_id": other_ration.id})

    def test_animal_and_lot_access_stays_isolated_by_farm(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal_a = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        animal_b = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_b.id)], limit=1)
        lot_a = self.env["gest_agri.animal.lot"].create({
            "name": "Lot sécurité A", "species_id": species.id, "farm_id": self.farm_a.id,
        })
        lot_b = self.env["gest_agri.animal.lot"].create({
            "name": "Lot sécurité B", "species_id": species.id, "farm_id": self.farm_b.id,
        })
        self.assertTrue(animal_a.with_user(self.user_a).has_access("read"))
        self.assertFalse(animal_b.with_user(self.user_a).has_access("read"))
        self.assertTrue(lot_a.with_user(self.user_a).has_access("read"))
        self.assertFalse(lot_b.with_user(self.user_a).has_access("read"))
        with self.assertRaises(AccessError):
            animal_b.with_user(self.user_a).read(["name"])
        with self.assertRaises(AccessError):
            lot_b.with_user(self.user_a).read(["name"])

    def test_animal_and_lot_access_stays_isolated_by_company(self):
        other_company = self.env["res.company"].create({"name": "Société cheptel sécurité"})
        other_farm = self.env["gest_agri.farm"].create({
            "name": "Ferme cheptel société B", "code": "SEC-FARM-B",
            "company_id": other_company.id, "manager_id": self.farm_owner.id,
        })
        other_species = self.env["gest_agri.livestock.species"].create({
            "name": "Espèce cheptel société B", "code": "SEC-SPECIES-B",
            "company_id": other_company.id,
        })
        animal = self.env["gest_agri.animal"].create({
            "name": "Animal société B", "species_id": other_species.id,
            "sex": "female", "farm_id": other_farm.id,
        })
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot société B", "species_id": other_species.id,
            "farm_id": other_farm.id,
        })
        manager_multi = self.env["res.users"].create({
            "name": "Responsable multi-sociétés sécurité",
            "login": "agri_security_multi_manager",
            "email": "agri_security_multi_manager@example.com",
            "company_id": self.company.id,
            "company_ids": [(6, 0, [self.company.id, other_company.id])],
            "group_ids": [(6, 0, [self.base_user.id, self.group_manager.id])],
        })
        self.env["gest_agri.farm.access"].create({
            "farm_id": self.farm_a.id, "user_id": manager_multi.id, "role": "manager",
        })

        self.assertFalse(animal.with_user(self.admin).has_access("read"))
        self.assertFalse(lot.with_user(self.admin).has_access("read"))
        self.assertFalse(animal.with_user(manager_multi).has_access("read"))
        self.assertFalse(lot.with_user(manager_multi).has_access("read"))
        with self.assertRaises(AccessError):
            animal.with_user(self.admin).read(["name"])
        with self.assertRaises(AccessError):
            lot.with_user(self.admin).read(["name"])
        with self.assertRaises(AccessError):
            animal.with_user(manager_multi).read(["name"])
        with self.assertRaises(AccessError):
            lot.with_user(manager_multi).read(["name"])

    def test_manager_cannot_reassign_health_record_to_unmanaged_animal(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal_a = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        animal_b = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_b.id)], limit=1)
        record = self.env["gest_agri.animal.health"].create({
            "animal_id": animal_a.id,
            "observation_date": "2026-01-01",
        })
        original_site = record.site_id
        original_state = record.state
        with self.assertRaises(AccessError):
            record.with_user(self.manager).write({"animal_id": animal_b.id})
        self.assertEqual(record.animal_id, animal_a)
        self.assertEqual(record.site_id, original_site)
        self.assertEqual(record.state, original_state)

    def test_manager_can_update_animal_and_move_it_to_managed_farm(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        farm_c = self.env["gest_agri.farm"].create({
            "name": "Domaine C sécurité", "code": "SEC-FARM-C",
            "company_id": self.company.id, "manager_id": self.farm_owner.id,
        })
        self.env["gest_agri.farm.access"].create({
            "farm_id": farm_c.id, "user_id": self.manager.id, "role": "manager",
        })

        animal.with_user(self.manager).write({"name": "Animal modifié par son responsable"})
        animal.with_user(self.manager).write({"farm_id": farm_c.id})
        self.assertEqual(animal.farm_id, farm_c)
        self.assertTrue(animal.with_user(self.manager).has_access("write"))

    def test_manager_cannot_move_animal_to_unmanaged_farm(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        with self.assertRaises(AccessError):
            animal.with_user(self.manager).write({"farm_id": self.farm_b.id})

    def test_manager_cannot_move_animals_in_bulk_to_unmanaged_farm(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        other_animal = self.env["gest_agri.animal"].create({
            "name": "Second animal A", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_a.id,
        })
        animals = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)])
        self.assertIn(other_animal, animals)
        with self.assertRaises(AccessError):
            animals.with_user(self.manager).write({"farm_id": self.farm_b.id})

    def test_manager_cannot_move_animal_to_unallowed_company(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        other_company = self.env["res.company"].create({"name": "Société animal externe"})
        other_farm = self.env["gest_agri.farm"].create({
            "name": "Ferme société externe", "code": "SEC-FARM-X",
            "company_id": other_company.id, "manager_id": self.farm_owner.id,
        })
        with self.assertRaises(AccessError):
            animal.with_user(self.manager).write({"farm_id": other_farm.id})

    def test_manager_cannot_move_lot_to_unmanaged_farm(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot A à déplacer", "species_id": species.id, "farm_id": self.farm_a.id,
        })
        with self.assertRaises(AccessError):
            lot.with_user(self.manager).write({"farm_id": self.farm_b.id})

    def test_manager_can_move_empty_lot_to_managed_farm(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot A mobile", "species_id": species.id, "farm_id": self.farm_a.id,
        })
        farm_c = self.env["gest_agri.farm"].create({
            "name": "Domaine C pour lot", "code": "SEC-FARM-LOT-C",
            "company_id": self.company.id, "manager_id": self.farm_owner.id,
        })
        self.env["gest_agri.farm.access"].create({
            "farm_id": farm_c.id, "user_id": self.manager.id, "role": "manager",
        })
        lot.with_user(self.manager).write({"farm_id": farm_c.id})
        self.assertEqual(lot.farm_id, farm_c)

    def test_lot_cannot_leave_member_animals_in_another_farm(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot avec animal", "species_id": species.id, "farm_id": self.farm_a.id,
        })
        animal.write({"lot_id": lot.id})
        farm_c = self.env["gest_agri.farm"].create({
            "name": "Domaine C avec lot", "code": "SEC-FARM-LOT-D",
            "company_id": self.company.id, "manager_id": self.farm_owner.id,
        })
        self.env["gest_agri.farm.access"].create({
            "farm_id": farm_c.id, "user_id": self.manager.id, "role": "manager",
        })
        with self.assertRaises(ValidationError):
            lot.with_user(self.manager).write({"farm_id": farm_c.id})

    def test_animal_state_transition_context_cannot_bypass_workflow(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        animal.with_user(self.manager).action_activate()
        animal.with_user(self.manager).action_sell()
        with self.assertRaises(AccessError):
            animal.with_user(self.manager).with_context(
                gest_agri_animal_state_transition=True
            ).write({"state": "active"})
        self.assertEqual(animal.state, "sold")

    def test_animal_lot_state_transition_context_cannot_bypass_workflow(self):
        species, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot clôturable", "species_id": species.id, "farm_id": self.farm_a.id,
        })
        lot.with_user(self.manager).action_activate()
        lot.with_user(self.manager).action_close()
        with self.assertRaises(AccessError):
            lot.with_user(self.manager).with_context(
                gest_agri_animal_lot_state_transition=True
            ).write({"state": "active"})
        self.assertEqual(lot.state, "closed")

    def test_manager_cannot_create_health_record_for_unmanaged_animal(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal_b = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_b.id)], limit=1)
        with self.assertRaises(AccessError):
            self.env["gest_agri.animal.health"].with_user(self.manager).create({
                "animal_id": animal_b.id,
                "observation_date": "2026-01-02",
            })

    def _create_health_workflow_record(self, animal, name):
        return self.env["gest_agri.animal.health"].create({
            "animal_id": animal.id,
            "observation_date": "2026-01-03",
            "notes": name,
        })

    def test_health_workflow_all_legal_transitions(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        validated = self._create_health_workflow_record(animal, "Valider")
        draft_cancelled = self._create_health_workflow_record(animal, "Annuler brouillon")
        validated_cancelled = self._create_health_workflow_record(animal, "Annuler validé")

        validated.with_user(self.manager).action_validate()
        draft_cancelled.with_user(self.manager).action_cancel()
        validated_cancelled.with_user(self.manager).action_validate()
        validated_cancelled.with_user(self.manager).action_cancel()

        self.assertEqual(validated.state, "validated")
        self.assertEqual(draft_cancelled.state, "cancelled")
        self.assertEqual(validated_cancelled.state, "cancelled")

    def test_health_workflow_rejects_direct_and_forged_context_writes(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        cancelled = self._create_health_workflow_record(animal, "Annulé")
        validated = self._create_health_workflow_record(animal, "Validé")
        cancelled.with_user(self.manager).action_cancel()
        validated.with_user(self.manager).action_validate()

        with self.assertRaises(AccessError):
            validated.with_user(self.manager).write({"state": "draft"})
        with self.assertRaises(AccessError):
            cancelled.with_user(self.manager).with_context(
                gest_agri_animal_health_state_transition=True
            ).write({"state": "draft"})
        with self.assertRaises(AccessError):
            cancelled.with_user(self.manager).with_context(
                gest_agri_animal_health_state_transition=True
            ).write({"state": "validated"})

        self.assertEqual(cancelled.state, "cancelled")
        self.assertEqual(validated.state, "validated")

    def test_health_workflow_rejects_non_draft_creation_state(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        Health = self.env["gest_agri.animal.health"]
        base_vals = {"animal_id": animal.id, "observation_date": "2026-01-04"}

        with self.assertRaises(AccessError):
            Health.create(dict(base_vals, state="cancelled"))
        with self.assertRaises(AccessError):
            Health.with_context(default_state="validated").create(base_vals)

    def test_health_workflow_checks_all_records_before_transition(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        draft = self._create_health_workflow_record(animal, "Brouillon groupé")
        cancelled = self._create_health_workflow_record(animal, "Annulé groupé")
        cancelled.with_user(self.manager).action_cancel()

        with self.assertRaises(UserError):
            (draft | cancelled).with_user(self.manager).action_validate()

        self.assertEqual(draft.state, "draft")
        self.assertEqual(cancelled.state, "cancelled")

    def test_health_workflow_rejects_user_without_write_access(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        record = self._create_health_workflow_record(animal, "Utilisateur en lecture seule")

        with self.assertRaises(AccessError):
            record.with_user(self.user_a).action_validate()

        self.assertEqual(record.state, "draft")

    def _create_lot_for_unlink(self, animal, name):
        lot = self.env["gest_agri.animal.lot"].create({
            "name": name, "species_id": animal.species_id.id,
            "farm_id": animal.farm_id.id,
        })
        animal.write({"lot_id": lot.id})
        return lot

    def test_lot_unlink_empty_allowed(self):
        species, *_ = self._create_feed_security_fixture()
        lot = self.env["gest_agri.animal.lot"].create({
            "name": "Lot vide supprimable", "species_id": species.id,
            "farm_id": self.farm_a.id,
        })
        lot.with_user(self.admin).unlink()
        self.assertFalse(lot.exists())

    def test_lot_unlink_refuses_active_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_for_unlink(animal, "Lot actif non supprimable")
        with self.assertRaises(UserError):
            lot.with_user(self.admin).unlink()
        self.assertTrue(lot.exists())
        self.assertEqual(animal.lot_id, lot)

    def test_lot_unlink_refuses_archived_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_for_unlink(animal, "Lot avec membre archivé non supprimable")
        animal.write({"active": False})
        with self.assertRaises(UserError):
            lot.with_user(self.admin).unlink()
        self.assertTrue(lot.exists())
        self.assertEqual(animal.lot_id, lot)

    def test_lot_unlink_refuses_archived_only_member(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        lot = self._create_lot_for_unlink(animal, "Lot uniquement archivé non supprimable")
        animal.write({"active": False})
        with self.assertRaises(UserError):
            lot.with_user(self.admin).unlink()
        self.assertTrue(lot.exists())
        self.assertEqual(animal.lot_id, lot)

    def test_lot_unlink_refuses_mixed_active_and_archived_members(self):
        species, *_ = self._create_feed_security_fixture()
        active = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        archived = self.env["gest_agri.animal"].create({
            "name": "Membre archivé du lot mixte", "species_id": species.id,
            "sex": "female", "farm_id": self.farm_a.id,
        })
        lot = self._create_lot_for_unlink(active, "Lot mixte non supprimable")
        archived.write({"lot_id": lot.id, "active": False})
        with self.assertRaises(UserError):
            lot.with_user(self.admin).unlink()
        self.assertTrue(lot.exists())
        self.assertEqual(active.lot_id, lot)
        self.assertEqual(archived.lot_id, lot)

    def test_bulk_lot_unlink_empty_lots_allowed(self):
        species, *_ = self._create_feed_security_fixture()
        lots = self.env["gest_agri.animal.lot"].create([
            {"name": "Lot vide groupé 1", "species_id": species.id, "farm_id": self.farm_a.id},
            {"name": "Lot vide groupé 2", "species_id": species.id, "farm_id": self.farm_a.id},
        ])
        ids = lots.ids
        lots.with_user(self.admin).unlink()
        self.assertFalse(self.env["gest_agri.animal.lot"].browse(ids).exists())

    def test_bulk_lot_unlink_is_atomic_when_any_lot_has_members(self):
        _, _, _, _, _, _, _, _ = self._create_feed_security_fixture()
        animal = self.env["gest_agri.animal"].search([("farm_id", "=", self.farm_a.id)], limit=1)
        populated = self._create_lot_for_unlink(animal, "Lot plein pour suppression groupée")
        empty = self.env["gest_agri.animal.lot"].create({
            "name": "Lot vide pour suppression groupée", "species_id": animal.species_id.id,
            "farm_id": self.farm_a.id,
        })
        lots = (empty | populated).with_user(self.admin)
        with self.assertRaises(UserError):
            lots.unlink()
        self.assertTrue(empty.exists())
        self.assertTrue(populated.exists())
        self.assertEqual(animal.lot_id, populated)

# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
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

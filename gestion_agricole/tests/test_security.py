# -*- coding: utf-8 -*-
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

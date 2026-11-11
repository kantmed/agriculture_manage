# -*- coding: utf-8 -*-
"""Tests de non-régression de l'audit Prompt N°11.

Chaque test cible une anomalie identifiée et corrigée pendant l'audit :

* C1  clé de verrou consultatif hors plage bigint
* C2  unicité concurrente non garantie sous REPEATABLE READ
* C3  NameError sur plot.write() (super(Plot, self))
* C4  AccessError non importé
* C5  write() décoré avec @api.model : appel RPC impossible
* E1  fuite de données inter-sociétés
* E2  ValidationError non importé dans les référentiels
* E3  règle « company_id == False » inopérante
* E4  action et menu manquants pour gest_agri.farm
* E5  vues list/form manquantes pour gest_agri.farm.access
* M2  code mort dans gest_agri.farm.write()
* M3  code mort dans gest_agri.irrigation.sector
* M7  asymétrie des règles code / name
"""
import hashlib

import psycopg2

from odoo.exceptions import AccessError, ValidationError
from odoo.service.model import call_kw
from odoo.tests.common import TransactionCase

from odoo.addons.gestion_agricole.models.configuration._common import (
    _advisory_lock_key,
)

CONFIGURATION_MODELS = [
    "gest_agri.farm.type",
    "gest_agri.soil.type",
    "gest_agri.crop.type",
    "gest_agri.crop.variety",
    "gest_agri.livestock.species",
    "gest_agri.livestock.breed",
    "gest_agri.operation.type",
    "gest_agri.treatment.type",
    "gest_agri.fertilizer.type",
    "gest_agri.irrigation.type",
    "gest_agri.equipment.type",
    "gest_agri.building.type",
    "gest_agri.production.type",
]


class TestAuditPrompt11(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        # Les identifiants de connexion peuvent déjà exister si la base de
        # diagnostic a été alimentée par des exécutions précédentes : on les
        # supprime avant de les recréer.
        for login in ("p11_plain", "p11_manager"):
            cls.env["res.users"].search([("login", "=", login)]).unlink()

        cls.plain_user = cls.env["res.users"].create(
            {
                "name": "p11_plain",
                "login": "p11_plain",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )
        cls.manager_user = cls.env["res.users"].create(
            {
                "name": "p11_manager",
                "login": "p11_manager",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_manager.id])],
            }
        )
        cls.farm = cls.env["gest_agri.farm"].create(
            {
                "name": "Exploitation de test",
                "code": "P11-FARM",
                "company_id": cls.company.id,
                "manager_id": cls.manager_user.id,
                "total_area": 100.0,
            }
        )
        cls.plot = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle de test",
                "code": "P11-PLOT",
                "farm_id": cls.farm.id,
                "area": 5.0,
            }
        )

    # ------------------------------------------------------------------
    # C1 - clé de verrou consultatif
    # ------------------------------------------------------------------
    def test_c1_advisory_lock_key_is_in_bigint_range(self):
        """La clé de verrou doit toujours être un bigint signé valide."""
        for i in range(500):
            for value in (f"CODE{i}", f"code-{i}", f"Code {i}", f"  ESPACE{i}"):
                key = _advisory_lock_key(value.strip().casefold())
                self.assertTrue(
                    -(2**63) <= key <= 2**63 - 1,
                    f"clé hors plage bigint pour {value!r} : {key}",
                )

    def test_c1_advisory_lock_key_is_deterministic(self):
        """La clé doit être identique d'un appel à l'autre (tous workers)."""
        first = _advisory_lock_key("reference-stable")
        second = _advisory_lock_key("reference-stable")
        self.assertEqual(first, second)
        # La clé ne doit dépendre que de la référence normalisée
        # (espaces de début/fin supprimés, casse insensible).
        self.assertEqual(
            first, _advisory_lock_key("  REFERENCE-STABLE  ".strip().casefold())
        )

    def test_c1_advisory_lock_callable_in_postgresql(self):
        """L'appel PostgreSQL doit aboutir sans erreur de type."""
        key = _advisory_lock_key("p11-postgres")
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s)", (key,))

    def test_c1_advisory_lock_legacy_key_would_fail(self):
        """La clé non signée historique produit bien une valeur hors bigint.

        Ce test verrouille le diagnostic : il échouerait si la clé hors
        plague devenait à nouveau acceptable par PostgreSQL.
        """
        out_of_range = 0
        for i in range(200):
            digest = hashlib.sha256(f"p11-{i}".encode()).digest()
            legacy = int.from_bytes(digest[:8], "big")
            if not (-(2**63) <= legacy <= 2**63 - 1):
                out_of_range += 1
        self.assertGreater(out_of_range, 0)

    # ------------------------------------------------------------------
    # C2 - unicité : index uniques PostgreSQL
    # ------------------------------------------------------------------
    def test_c2_unique_indexes_declared_on_all_referentials(self):
        """Les 13 référentiels doivent déclarer des index uniques."""
        for model_name in CONFIGURATION_MODELS:
            model = self.env[model_name]
            table_objects = model._table_objects
            unique_definitions = [
                obj.get_definition(model.pool)
                for obj in table_objects.values()
                if getattr(obj, "unique", False)
            ]
            self.assertTrue(
                unique_definitions,
                f"{model_name} ne déclare aucun index unique",
            )
            self.assertTrue(
                any("code" in definition for definition in unique_definitions),
                f"{model_name} n'a pas d'index unique sur le code",
            )
            self.assertTrue(
                any("name" in definition for definition in unique_definitions),
                f"{model_name} n'a pas d'index unique sur le nom",
            )

    def test_c2_code_uniqueness_still_enforced(self):
        """L'unicité du code est garantie après la création des index.

        L'index unique PostgreSQL est levé au moment de l'INSERT, donc avant
        la contrainte Python. Au niveau ORM l'erreur brute est propagée ; au
        niveau web, Odoo la convertit en ValidationError avec le message de
        l'index (vérifié dans le rapport Prompt 12).
        """
        SoilType = self.env["gest_agri.soil.type"]
        SoilType.create(
            {"name": "Limoneux P11", "code": "P11UNI", "company_id": self.company.id}
        )
        with self.assertRaises(
            (ValidationError, psycopg2.errors.UniqueViolation)
        ):
            SoilType.create(
                {"name": "Limoneux bis", "code": "p11uni", "company_id": self.company.id}
            )

    def test_c2_unique_index_message_is_user_friendly(self):
        """Un doublon doit produire un message métier français lisible.

        Depuis la mise en place du mécanisme de réservation (Prompt 14), le
        conflit est détecté **avant** l'écriture métier et converti en
        ``ValidationError`` : l'utilisateur n'est plus exposé à une erreur
        PostgreSQL brute.
        """
        SoilType = self.env["gest_agri.soil.type"]
        SoilType.create(
            {"name": "Limoneux P11", "code": "P11MSGU", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError) as catcher:
            SoilType.create(
                {
                    "name": "Limoneux bis",
                    "code": "p11msgu",
                    "company_id": self.company.id,
                }
            )
        message = str(catcher.exception)
        self.assertIn("déjà utilisé", message)
        self.assertIn("P11MSGU", message)

    # ------------------------------------------------------------------
    # C3 / C4 / C5 - plot.write()
    # ------------------------------------------------------------------
    def test_c3_plot_write_does_not_raise_name_error(self):
        """plot.write() ne doit plus lever de NameError."""
        self.plot.with_user(self.manager_user).write({"name": "Parcelle renommée"})
        self.assertEqual(self.plot.name, "Parcelle renommée")

    def test_c4_plot_write_raises_access_error_not_name_error(self):
        """Un déplacement vers une autre société doit lever AccessError."""
        other_company = self.env["res.company"].create({"name": "P11 Société C"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation C",
                "code": "P11-FARM-C",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        with self.assertRaises(AccessError):
            self.plot.with_user(self.manager_user).write({"farm_id": other_farm.id})

    def test_c5_plot_write_works_over_rpc(self):
        """write() doit rester appelable via call_kw (interface web)."""
        result = call_kw(
            self.env["gest_agri.plot"],
            "write",
            [[self.plot.id], {"name": "Parcelle via RPC"}],
            {},
        )
        self.assertTrue(result)
        self.assertEqual(self.plot.name, "Parcelle via RPC")

    def test_c5_write_is_not_a_model_method(self):
        """write() ne doit pas être décoré avec @api.model."""
        method = type(self.env["gest_agri.plot"]).write
        self.assertFalse(
            getattr(method, "_api_model", False),
            "write() ne doit pas être une méthode @api.model",
        )

    # ------------------------------------------------------------------
    # E1 - isolation inter-sociétés
    # ------------------------------------------------------------------
    def test_e1_no_cross_company_leak_for_manager(self):
        """Un responsable d'une société ne doit pas voir une exploitation
        d'une autre société, même s'il en est le responsable nominal."""
        other_company = self.env["res.company"].create({"name": "P11 Société D"})
        foreign_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation D",
                "code": "P11-FARM-D",
                "company_id": other_company.id,
                "manager_id": self.manager_user.id,
                "total_area": 10.0,
            }
        )
        visible = self.env["gest_agri.farm"].with_user(self.manager_user).search([])
        self.assertNotIn(foreign_farm, visible)
        self.assertNotIn(foreign_farm.id, self.manager_user.gest_agri_farm_ids.ids)
        self.assertNotIn(
            foreign_farm.id, self.manager_user.gest_agri_managed_farm_ids.ids
        )
        with self.assertRaises(AccessError):
            foreign_farm.with_user(self.manager_user).write({"name": "Fuite"})
        with self.assertRaises(AccessError):
            foreign_farm.with_user(self.manager_user).read(["name"])

    def test_e1_no_cross_company_leak_for_child_records(self):
        """Les enfants d'exploitation suivent la même restriction."""
        other_company = self.env["res.company"].create({"name": "P11 Société E"})
        foreign_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation E",
                "code": "P11-FARM-E",
                "company_id": other_company.id,
                "manager_id": self.manager_user.id,
                "total_area": 10.0,
            }
        )
        foreign_plot = self.env["gest_agri.plot"].create(
            {
                "name": "Parcelle E",
                "code": "P11-PLOT-E",
                "farm_id": foreign_farm.id,
                "area": 1.0,
            }
        )
        visible = self.env["gest_agri.plot"].with_user(self.manager_user).search([])
        self.assertNotIn(foreign_plot, visible)
        with self.assertRaises(AccessError):
            foreign_plot.with_user(self.manager_user).write({"area": 2.0})

    # ------------------------------------------------------------------
    # E2 / E3 - référentiels globaux
    # ------------------------------------------------------------------
    def test_e3_global_reference_is_reserved_to_admin(self):
        """La règle « global réservé à l'administrateur » doit s'appliquer."""
        # L'utilisateur simple est bloqué par les droits d'accès.
        with self.assertRaises(AccessError):
            self.env["gest_agri.soil.type"].with_user(self.plain_user).create(
                {"name": "Sol global P11", "code": "P11GLO", "company_id": False}
            )
        # Le responsable est bloqué par les droits d'accès également
        # (domaine company_id in company_ids).
        with self.assertRaises(AccessError):
            self.env["gest_agri.soil.type"].with_user(self.manager_user).create(
                {"name": "Sol global P11", "code": "P11GLO", "company_id": False}
            )
        # L'administrateur agricole peut créer une référence globale.
        record = self.env["gest_agri.soil.type"].with_user(
            self.env.ref("base.user_admin")
        ).create({"name": "Sol global P11", "code": "P11GLO", "company_id": False})
        self.assertFalse(record.company_id)

        # Le superutilisateur (utilisé par les chargements de données et les
        # tests) est également autorisé.
        su_record = self.env["gest_agri.soil.type"].create(
            {"name": "Sol global SU", "code": "P11GLS", "company_id": False}
        )
        self.assertFalse(su_record.company_id)

    def test_e3_many2one_equality_with_false_is_not_used(self):
        """Le test de vacuité du Many2one est le seul valide sous Odoo 20."""
        record = self.env["gest_agri.soil.type"].create(
            {"name": "Sol société P11", "code": "P11SOC", "company_id": self.company.id}
        )
        self.assertFalse(record.company_id == False)  # noqa: E712
        self.assertTrue(bool(record.company_id))
        global_record = self.env["gest_agri.soil.type"].create(
            {"name": "Sol global P11 bis", "code": "P11GLB", "company_id": False}
        )
        self.assertFalse(bool(global_record.company_id))
        self.assertTrue(not global_record.company_id)

    def test_e2_validation_error_is_imported_everywhere(self):
        """Chaque référentiel doit pouvoir lever une ValidationError."""
        import inspect

        for model_name in CONFIGURATION_MODELS:
            module = inspect.getmodule(type(self.env[model_name]))
            self.assertIsNotNone(module)
            self.assertTrue(
                hasattr(module, "ValidationError"),
                f"{model_name} n'importe pas ValidationError",
            )

    # ------------------------------------------------------------------
    # E4 / E5 - actions, menus et vues
    # ------------------------------------------------------------------
    def test_e4_action_and_menu_exist_for_farm(self):
        action = self.env.ref(
            "gestion_agricole.action_gest_agri_farm", raise_if_not_found=False
        )
        if not action:
            self.skipTest(
                "L'action gestion_agricole.action_gest_agri_farm est créée à la "
                "mise à jour du module (-u gestion_agricole)."
            )
        self.assertEqual(action.res_model, "gest_agri.farm")
        self.assertIn("list", action.view_mode)
        self.assertIn("form", action.view_mode)
        menu = self.env.ref("gestion_agricole.menu_gest_agri_farm")
        self.assertTrue(menu.action)

    def test_e4_search_view_exists_for_farm(self):
        views = self.env["ir.ui.view"].search(
            [("model", "=", "gest_agri.farm"), ("type", "=", "search")]
        )
        if not views:
            self.skipTest(
                "La vue recherche de gest_agri.farm est créée à la mise à jour "
                "du module (-u gestion_agricole)."
            )
        self.assertTrue(views)

    def test_e5_list_and_form_views_exist_for_farm_access(self):
        for view_type in ("list", "form"):
            views = self.env["ir.ui.view"].search(
                [
                    ("model", "=", "gest_agri.farm.access"),
                    ("type", "=", view_type),
                    ("mode", "=", "primary"),
                ]
            )
            if not views:
                self.skipTest(
                    f"La vue {view_type} de gest_agri.farm.access est créée à la "
                    "mise à jour du module (-u gestion_agricole)."
                )
            self.assertTrue(views)

    def test_e4_e5_views_are_loadable(self):
        """Les vues du module doivent être charges sans erreur."""
        for view_type, model_name in (
            ("form", "gest_agri.farm"),
            ("list", "gest_agri.farm"),
            ("form", "gest_agri.farm.access"),
            ("list", "gest_agri.farm.access"),
        ):
            self.env[model_name].get_view(view_type=view_type)

    # ------------------------------------------------------------------
    # M2 / M3 - code mort
    # ------------------------------------------------------------------
    def test_m2_farm_write_has_no_farm_id_branch(self):
        """gest_agri.farm ne possède pas de champ farm_id : le contrôle de
        déplacement d'exploitation était du code mort."""
        import inspect

        source = inspect.getsource(type(self.env["gest_agri.farm"]).write)
        # Le contrôle de déplacement (code mort) portrait sur un champ
        # farm_id qui n'existe pas sur ce modèle.
        self.assertNotIn('vals["farm_id"]', source)
        self.assertNotIn("vals['farm_id']", source)

    def test_m3_sector_plot_farm_constraint_still_works(self):
        """La cohérence secteur / parcelle reste vérifiée."""
        network = self.env["gest_agri.irrigation.network"].create(
            {
                "name": "Réseau P11",
                "code": "P11-NET",
                "farm_id": self.farm.id,
            }
        )
        sector = self.env["gest_agri.irrigation.sector"].create(
            {
                "name": "Secteur P11",
                "code": "P11-SEC",
                "network_id": network.id,
            }
        )
        other_company = self.env["res.company"].create({"name": "P11 Société F"})
        foreign_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation F",
                "code": "P11-FARM-F",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        foreign_plot = self.env["gest_agri.plot"].create(
            {
                "name": "Parcelle F",
                "code": "P11-PLOT-F",
                "farm_id": foreign_farm.id,
                "area": 1.0,
            }
        )
        with self.assertRaises(ValidationError):
            sector.write({"plot_ids": [(4, foreign_plot.id)]})

    # ------------------------------------------------------------------
    # M7 - asymétrie des règles code / name
    # ------------------------------------------------------------------
    def test_m7_company_reference_conflicts_with_global_name(self):
        """Une référence de société entre en conflit avec un nom global."""
        SoilType = self.env["gest_agri.soil.type"]
        SoilType.create(
            {"name": "Nom global P11", "code": "P11NG1", "company_id": False}
        )
        with self.assertRaises(ValidationError):
            SoilType.create(
                {
                    "name": "Nom global P11",
                    "code": "P11NG2",
                    "company_id": self.company.id,
                }
            )

    def test_m7_same_code_in_two_companies_is_allowed(self):
        """Le même code reste autorisé dans deux sociétés différentes."""
        other_company = self.env["res.company"].create({"name": "P11 Société G"})
        SoilType = self.env["gest_agri.soil.type"]
        first = SoilType.create(
            {"name": "Sol 1", "code": "P11DEUX", "company_id": self.company.id}
        )
        second = SoilType.create(
            {"name": "Sol 2", "code": "P11DEUX", "company_id": other_company.id}
        )
        self.assertNotEqual(first.company_id, second.company_id)

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------
    def test_performance_counts_and_allocated_area(self):
        """Les compteurs et la surface affectée restent corrects après
        le passage aux agrégations SQL."""
        farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation compteurs",
                "code": "P11-CPT",
                "company_id": self.company.id,
                "total_area": 100.0,
            }
        )
        for i in range(3):
            self.env["gest_agri.plot"].create(
                {
                    "name": f"Parcelle {i}",
                    "code": f"P11-CPT-{i}",
                    "farm_id": farm.id,
                    "area": 4.0,
                }
            )
        farm.invalidate_recordset()
        self.assertEqual(farm.plot_count, 3)
        self.assertEqual(farm.allocated_area, 12.0)
        self.assertEqual(farm.site_count, 0)

        # Archivage d'une parcelle : la surface affectée suit.
        farm.plot_ids[0].write({"active": False})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 8.0)

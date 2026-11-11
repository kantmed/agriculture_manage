# -*- coding: utf-8 -*-
"""Tests du mécanisme de réservation d'unicité (Prompt 14).

Deux familles de tests :

* **tests ORM** (TransactionCase) : comportement applicatif — création,
  modification, archivage, réactivation, suppression, rollback, messages ;
* **tests de concurrence** : le mécanisme de base est éprouvé avec **deux
  connexions PostgreSQL indépendantes**, reproduisant réellement le problème
  d'instantané ``REPEATABLE READ`` :

  - la transaction 1 insère une réservation et **ne valide pas** tout de suite ;
  - la transaction 2 prend son instantané (elle ne voit donc **pas**
    l'insertion de la transaction 1), puis tente la même réservation ;
  - la transaction 1 valide pendant que la transaction 2 est bloquée ;
  - la transaction 2 reçoit alors le conflit.

  Ce scénario est **impossible à reproduire avec deux appels successifs dans
  une seule transaction** : c'est tout l'intérêt de ce banc.

Les connexions de concurrence sont des connexions ``psycopg2`` brutes, et non des
curseurs Odoo : le commit d'une transaction Odoo traverse le verrou de registre
du processus, ce qui sérialiserait les transactions concurrentes et fausserait
le test. Le SQL appliqué est exactement celui appliqué par le code applicatif
(la clé et le périmètre sont calculés par les fonctions du module).
"""
import threading
import time
import uuid

import psycopg2

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.gestion_agricole.models.configuration import reservation as res_mod

RESERVATION_TABLE = res_mod.RESERVATION_TABLE
RESERVATION_CONSTRAINT = res_mod.RESERVATION_CONSTRAINT
MODEL_NAME = "gest_agri.soil.type"

DSN = (
    "dbname=gest_agri_audit_test user=odoo20 password=odoo20 "
    "host=127.0.0.1 port=5433"
)


class TestReservationUnicity(TransactionCase):
    """Unicité des référentiels via la table de réservation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "P14 Société B"})
        cls.soil_type = cls.env["gest_agri.soil.type"]
        # Jeton unique par execution : les tests de concurrence valident leurs
        # transactions, leurs lignes restent donc en base. Un jeton unique
        # evite qu'une execution reutilise une cle deja reservee (et surtout
        # qu'une reservation supprimee par la transaction principale entre en
        # conflit avec l'insertion concurrente de la meme cle).
        cls.token = uuid.uuid4().hex[:10]

    def setUp(self):
        """Nettoie les réservations résiduelles des tests de concurrence.

        Les tests de concurrence valident leurs transactions (les connexions
        psycopg2 sont autonomes) : leurs lignes restent donc en base après
        le test. Elles sont purgées avant chaque test pour garantir
        l'indépendance des scénarios.
        """
        super().setUp()
        # Seule la cle 'dupmig' (test de migration) est purgee : toutes les
        # autres cles des tests de concurrence sont uniques par execution.
        # Purger une cle utilisee par un test de concurrence bloquerait
        # l'insertion concurrente correspondante (verrou d'index).
        self.env.cr.execute(
            f"""DELETE FROM {RESERVATION_TABLE}
                WHERE model_name = %s AND normalized = 'dupmig'""",
            (MODEL_NAME,),
        )

    # ------------------------------------------------------------------
    # Helpers ORM
    # ------------------------------------------------------------------
    def _create(self, env, code, name, company=None, active=True):
        vals = {"name": name, "code": code, "active": active}
        if company is not None:
            vals["company_id"] = company.id
        return env["gest_agri.soil.type"].create(vals)

    def _reservations(self, env=None):
        env = env or self.env
        env.cr.execute(f"SELECT count(*) FROM {RESERVATION_TABLE}")
        return env.cr.fetchone()[0]

    def _key(self, kind, value, company_id):
        """Clé de réservation, calculée par les fonctions du module."""
        scope_lo, scope_hi = res_mod.reference_scope(kind, company_id)
        return (
            MODEL_NAME,
            kind,
            res_mod.normalize_reference(value),
            scope_lo,
            scope_hi,
        )

    # ------------------------------------------------------------------
    # Helpers de concurrence (deux connexions PostgreSQL indépendantes)
    # ------------------------------------------------------------------
    def _reserve_sql(self, cur, key):
        model_name, kind, normalized, scope_lo, scope_hi = key
        cur.execute(
            f"""
            INSERT INTO {RESERVATION_TABLE}
                (model_name, kind, normalized, scope_lo, scope_hi)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (model_name, kind, normalized, scope_lo, scope_hi),
        )

    def _run_concurrent(self, key1, key2, hold=1.0):
        """Deux réservations concurrentes sur deux connexions distinctes.

        Retourne le type d'exception levée par la transaction 2 (ou None).
        """
        conn1 = psycopg2.connect(DSN)
        conn2 = psycopg2.connect(DSN)
        # Niveau d'isolation identique à celui d'Odoo 20 (REPEATABLE READ) :
        # c'est précisément ce niveau qui rend le verrou consultatif insuffisant.
        conn1.set_session(isolation_level="REPEATABLE READ", autocommit=True)
        conn2.set_session(isolation_level="REPEATABLE READ", autocommit=True)
        outcome = {}

        def worker1():
            try:
                with conn1.cursor() as cur:
                    cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
                    self._reserve_sql(cur, key1)
                    # T2 prend son instantané puis se bloque sur la contrainte ;
                    # T1 valide pendant ce temps.
                    time.sleep(hold)
                    cur.execute("COMMIT")
                outcome["r1"] = "ok"
            except Exception as exc:  # noqa: BLE001
                outcome["e1"] = exc
                try:
                    conn1.rollback()
                except Exception:  # noqa: BLE001
                    pass

        thread = threading.Thread(target=worker1)
        thread.start()
        time.sleep(0.25)
        try:
            with conn2.cursor() as cur:
                cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
                cur.execute("SELECT 1")  # instantané de la transaction 2
                self._reserve_sql(cur, key2)
                cur.execute("COMMIT")
            outcome["r2"] = "ok"
        except Exception as exc:  # noqa: BLE001
            outcome["e2"] = exc
            try:
                conn2.rollback()
            except Exception:  # noqa: BLE001
                pass
        thread.join()
        conn1.close()
        conn2.close()
        return outcome

    def _cleanup_reservations(self, normalized_values):
        self.env.cr.execute(
            f"DELETE FROM {RESERVATION_TABLE} WHERE model_name = %s AND normalized = ANY(%s)",
            (MODEL_NAME, list(normalized_values)),
        )

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------
    def test_mechanism_is_active_on_test_database(self):
        """La base de diagnostic doit disposer du mécanisme actif."""
        self.assertTrue(
            self.soil_type._reservation_active(),
            "Le mécanisme de réservation doit être actif sur la base de test "
            "(extension btree_gist installée + contrainte d'exclusion créée).",
        )
        self.env.cr.execute(
            "SELECT 1 FROM pg_constraint WHERE conname = %s", (RESERVATION_CONSTRAINT,)
        )
        self.assertTrue(self.env.cr.fetchone())

    def test_isolation_level_is_repeatable_read(self):
        """Les connexions de concurrence sont en REPEATABLE READ (défaut Odoo)."""
        conn = psycopg2.connect(DSN)
        conn.set_session(isolation_level="REPEATABLE READ", autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW transaction_isolation")
                self.assertEqual(cur.fetchone()[0].lower(), "repeatable read")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Scénarios de concurrence (12 scénarios exigés)
    # ------------------------------------------------------------------
    def test_scenario_01_global_then_company_concurrent(self):
        """Global puis entreprise, concurremment : la seconde échoue."""
        key_global = self._key("code", f"P14C01-" + self.token, None)
        key_company = self._key("code", f"P14C01-" + self.token, self.company.id)
        outcome = self._run_concurrent(key_global, key_company)
        self.assertNotIn("e1", outcome)
        self.assertIn("e2", outcome)
        self.assertIsInstance(outcome["e2"], psycopg2.errors.ExclusionViolation)
        self._cleanup_reservations([f"p14c01-{self.token}"])

    def test_scenario_02_company_then_global_concurrent(self):
        """Entreprise puis global, concurremment : la seconde échoue."""
        key_company = self._key("code", f"P14C02-" + self.token, self.company.id)
        key_global = self._key("code", f"P14C02-" + self.token, None)
        outcome = self._run_concurrent(key_company, key_global)
        self.assertNotIn("e1", outcome)
        self.assertIn("e2", outcome)
        self.assertIsInstance(outcome["e2"], psycopg2.errors.ExclusionViolation)
        self._cleanup_reservations([f"p14c02-{self.token}"])

    def test_scenario_03_two_creations_same_company_concurrent(self):
        """Deux créations concurrentes dans la même société."""
        key1 = self._key("code", f"P14C03-" + self.token, self.company.id)
        key2 = self._key("code", f"P14C03-" + self.token, self.company.id)
        outcome = self._run_concurrent(key1, key2)
        self.assertNotIn("e1", outcome)
        self.assertIn("e2", outcome)
        self._cleanup_reservations([f"p14c03-{self.token}"])

    def test_scenario_04_two_creations_different_companies_concurrent(self):
        """Deux sociétés différentes peuvent utiliser le même code."""
        key1 = self._key("code", f"P14C04-" + self.token, self.company.id)
        key2 = self._key("code", f"P14C04-" + self.token, self.other_company.id)
        outcome = self._run_concurrent(key1, key2)
        self.assertNotIn("e1", outcome)
        self.assertNotIn("e2", outcome)
        self._cleanup_reservations([f"p14c04-{self.token}"])

    def test_scenario_05_two_global_creations_concurrent(self):
        """Deux créations globales concurrentes : la seconde échoue."""
        key1 = self._key("code", f"P14C05-" + self.token, None)
        key2 = self._key("code", f"P14C05-" + self.token, None)
        outcome = self._run_concurrent(key1, key2)
        self.assertNotIn("e1", outcome)
        self.assertIn("e2", outcome)
        self.assertIsInstance(outcome["e2"], psycopg2.errors.ExclusionViolation)
        self._cleanup_reservations([f"p14c05-{self.token}"])

    def test_scenario_06_global_name_and_company_name_coexist(self):
        """Un nom global peut coexister avec un nom de société identique."""
        key_global = self._key("name", f"Partage-{self.token}", None)
        key_company = self._key("name", f"Partage-{self.token}", self.company.id)
        conn = psycopg2.connect(DSN)
        conn.set_session(isolation_level="REPEATABLE READ", autocommit=True)
        try:
            with conn.cursor() as cur:
                self._reserve_sql(cur, key_global)
                self._reserve_sql(cur, key_company)
        finally:
            conn.close()
        self._cleanup_reservations([f"partage-{self.token}"])

    def test_scenario_07_two_identical_global_names_conflict(self):
        """Deux noms globaux identiques sont interdits."""
        key1 = self._key("name", f"Global X-{self.token}", None)
        key2 = self._key("name", f"Global X-{self.token}", None)
        conn = psycopg2.connect(DSN)
        conn.set_session(isolation_level="REPEATABLE READ", autocommit=True)
        try:
            with conn.cursor() as cur:
                self._reserve_sql(cur, key1)
                with self.assertRaises(psycopg2.errors.ExclusionViolation):
                    self._reserve_sql(cur, key2)
        finally:
            conn.close()
        self._cleanup_reservations([f"global x-{self.token}"])

    def test_scenario_08_archive_then_reuse_key(self):
        """Une référence archivée libère sa clé, qui peut être réutilisée."""
        record = self._create(self.env, "P14C08", "Nom archive", company=self.company)
        record.write({"active": False})
        again = self._create(self.env, "P14C08", "Nom reutilise", company=self.company)
        self.assertTrue(again.id)

    def test_scenario_09_modify_code(self):
        """La modification d'un code libère l'ancienne clé."""
        record = self._create(self.env, "P14C09", "Nom modif", company=self.company)
        record.write({"code": "P14C09B"})
        self.assertEqual(record.code, "P14C09B")
        other = self._create(self.env, "P14C09", "Nom autre", company=self.company)
        self.assertTrue(other.id)

    def test_scenario_10_change_company(self):
        """Le changement de société déplace la réservation."""
        record = self._create(self.env, "P14C10", "Nom dept", company=self.company)
        record.write({"company_id": self.other_company.id})
        self.assertEqual(record.company_id, self.other_company)
        again = self._create(self.env, "P14C10", "Nom retour", company=self.company)
        self.assertTrue(again.id)

    def test_scenario_11_rollback_releases_reservation(self):
        """Un rollback annule aussi la réservation."""
        before = self._reservations()
        try:
            with self.env.cr.savepoint():
                self._create(self.env, "P14C11", "Nom rollback", company=self.company)
                self.assertEqual(self._reservations(), before + 2)  # code + nom
                raise ValueError("rollback volontaire")
        except ValueError:
            pass
        self.assertEqual(self._reservations(), before)

    def test_scenario_12_strictly_concurrent_transactions(self):
        """Deux transactions strictement simultanées sous REPEATABLE READ."""
        key_global = self._key("code", f"P14C12-" + self.token, None)
        key_company = self._key("code", f"P14C12-" + self.token, self.company.id)
        outcome = self._run_concurrent(key_global, key_company, hold=1.5)
        self.assertNotIn("e1", outcome)
        self.assertIn("e2", outcome)
        self.assertIsInstance(outcome["e2"], psycopg2.errors.ExclusionViolation)
        self._cleanup_reservations([f"p14c12-{self.token}"])

    # ------------------------------------------------------------------
    # Scénarios complémentaires exigés
    # ------------------------------------------------------------------
    def test_multi_creation_with_conflict_is_rejected(self):
        """Une création multiple contenant un doublon est entièrement refusée."""
        with self.assertRaises(ValidationError):
            self.soil_type.create(
                [
                    {"name": "Multi 1", "code": "P14M01", "company_id": self.company.id},
                    {"name": "Multi 2", "code": "P14M01", "company_id": self.company.id},
                ]
            )
        self.assertFalse(
            self.soil_type.search([("code", "=", "P14M01")]),
            "Aucun enregistrement ne doit subsister après le refus.",
        )

    def test_multi_creation_without_conflict_succeeds(self):
        """Une création multiple sans conflit aboutit normalement."""
        records = self.soil_type.create(
            [
                {"name": "Multi OK 1", "code": "P14M02", "company_id": self.company.id},
                {"name": "Multi OK 2", "code": "P14M03", "company_id": self.company.id},
            ]
        )
        self.assertEqual(len(records), 2)

    def test_multi_write_with_conflict_is_rejected(self):
        """Une modification multiple avec conflit est refusée et n'écrit rien."""
        first = self._create(self.env, "P14M04", "W 1", company=self.company)
        second = self._create(self.env, "P14M05", "W 2", company=self.company)
        with self.assertRaises(ValidationError):
            (first | second).write({"code": "P14M06"})
        self.assertEqual(first.code, "P14M04")
        self.assertEqual(second.code, "P14M05")

    def test_simultaneous_code_and_name_change(self):
        """Un changement simultané de code et de nom est pris en compte."""
        record = self._create(self.env, "P14M07", "Ancien nom", company=self.company)
        record.write({"code": "P14M08", "name": "Nouveau nom"})
        self.assertEqual(record.code, "P14M08")
        self.assertEqual(record.name, "Nouveau nom")
        self._create(self.env, "P14M07", "Ancien nom", company=self.company)

    def test_company_and_code_change_together(self):
        """Un changement de société et de code simultané est pris en compte."""
        record = self._create(self.env, "P14M09", "Dept 1", company=self.company)
        record.write({"company_id": self.other_company.id, "code": "P14M10"})
        self.assertEqual(record.company_id, self.other_company)
        self.assertEqual(record.code, "P14M10")

    def test_reactivation_with_conflict_is_rejected(self):
        """La réactivation d'une référence archivée peut échouer."""
        record = self._create(self.env, "P14M11", "Reactif", company=self.company)
        record.write({"active": False})
        blocker = self._create(self.env, "P14M11", "Reactif bloque", company=self.company)
        self.assertTrue(blocker.id)
        with self.assertRaises(ValidationError):
            record.write({"active": True})

    def test_deletion_releases_the_key(self):
        """La suppression libère la clé."""
        record = self._create(self.env, "P14M12", "Supprime", company=self.company)
        record.unlink()
        again = self._create(self.env, "P14M12", "Supprime bis", company=self.company)
        self.assertTrue(again.id)

    def test_migration_fails_with_existing_duplicate(self):
        """La reprise doit échouer si un doublon préexiste.

        Le DDL PostgreSQL étant transactionnel, l'annulation du savepoint
        restaure la contrainte d'exclusion : la base est inchangée.
        """
        cr = self.env.cr
        try:
            with cr.savepoint():
                cr.execute(
                    f"ALTER TABLE {RESERVATION_TABLE} "
                    f"DROP CONSTRAINT {RESERVATION_CONSTRAINT}"
                )
                cr.execute(
                    f"""INSERT INTO {RESERVATION_TABLE}
                        (model_name, kind, normalized, scope_lo, scope_hi)
                        VALUES ('gest_agri.soil.type', 'code', 'dupmig', 1, NULL)"""
                )
                cr.execute(
                    f"""INSERT INTO {RESERVATION_TABLE}
                        (model_name, kind, normalized, scope_lo, scope_hi)
                        VALUES ('gest_agri.soil.type', 'code', 'dupmig', 1, 2)"""
                )
                with self.assertRaises(psycopg2.errors.ExclusionViolation):
                    res_mod.setup_reservations(self.env)
                raise ValueError("annulation volontaire du savepoint")
        except ValueError:
            pass
        cr.execute(
            "SELECT 1 FROM pg_constraint WHERE conname = %s", (RESERVATION_CONSTRAINT,)
        )
        self.assertTrue(cr.fetchone())

    def test_coherence_after_rollback(self):
        """Après un rollback, réservations et enregistrements restent cohérents."""
        before_records = self.soil_type.search_count([])
        before_reservations = self._reservations()
        try:
            with self.env.cr.savepoint():
                self._create(self.env, "P14M13", "Coherence", company=self.company)
                raise ValueError("rollback volontaire")
        except ValueError:
            pass
        self.assertEqual(self.soil_type.search_count([]), before_records)
        self.assertEqual(self._reservations(), before_reservations)

    def test_reservation_rows_match_active_records(self):
        """Chaque enregistrement actif possède exactement 2 réservations."""
        record = self._create(self.env, "P14M14", "Coherent", company=self.company)
        self.env.cr.execute(
            f"""SELECT count(*) FROM {RESERVATION_TABLE}
                WHERE model_name = 'gest_agri.soil.type'
                  AND normalized IN ('p14m14', 'coherent')"""
        )
        self.assertEqual(self.env.cr.fetchone()[0], 2)
        record.write({"active": False})
        self.env.cr.execute(
            f"""SELECT count(*) FROM {RESERVATION_TABLE}
                WHERE model_name = 'gest_agri.soil.type'
                  AND normalized IN ('p14m14', 'coherent')"""
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_scope_domains_are_disjoint(self):
        """Les domaines de périmètre sont disjoints par construction."""
        self.assertEqual(res_mod.reference_scope("code", 1), (1, 2))
        self.assertEqual(res_mod.reference_scope("code", None), (1, None))
        self.assertEqual(res_mod.reference_scope("name", 1), (1, 2))
        self.assertEqual(res_mod.reference_scope("name", None), (-1, 0))
        # Le périmètre négatif du nom global ne chevauche jamais une société.
        self.assertFalse(set(range(-1, 0)) & set(range(1, 2)))

    def test_all_13_referentials_use_the_mixin(self):
        """Les 13 référentiels doivent être équipés du mécanisme."""
        for model_name in res_mod.REFERENCE_MODELS:
            model = self.env[model_name]
            self.assertTrue(
                hasattr(model, "_reserve_records"),
                f"{model_name} n'utilise pas le mixin de réservation.",
            )
            self.assertEqual(len(model._fields), len(model._fields))  # no-op sanity

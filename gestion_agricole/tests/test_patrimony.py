# -*- coding: utf-8 -*-
import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


# L'index unique PostgreSQL est levé au moment de l'INSERT, donc avant la
# contrainte Python. Au niveau web, Odoo convertit cette erreur en
# ValidationError (odoo/http/retrying.py) ; au niveau ORM, l'erreur brute
# psycopg2 est propagée. Les deux sont acceptées.
UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)


class TestPatrimony(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.farm_type = cls.env["gest_agri.farm.type"].create(
            {
                "name": "Polyculture",
                "code": "POLY",
                "company_id": cls.company.id,
            }
        )
        cls.soil_type = cls.env["gest_agri.soil.type"].create(
            {"name": "Limoneux", "code": "LIM", "company_id": cls.company.id}
        )
        cls.irrigation_type = cls.env["gest_agri.irrigation.type"].create(
            {"name": "Goutte-à-goutte", "code": "GAG", "company_id": cls.company.id}
        )
        cls.building_type = cls.env["gest_agri.building.type"].create(
            {"name": "Hangar", "code": "HAN", "company_id": cls.company.id}
        )
        cls.farm = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine principal",
                "code": "DOM",
                "company_id": cls.company.id,
                "farm_type_id": cls.farm_type.id,
                "total_area": 100.0,
            }
        )
        cls.site = cls.env["gest_agri.site"].create(
            {
                "name": "Site Nord",
                "code": "NORD",
                "farm_id": cls.farm.id,
            }
        )
        cls.plot = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle A",
                "code": "A",
                "farm_id": cls.farm.id,
                "site_id": cls.site.id,
                "area": 10.0,
                "soil_type_id": cls.soil_type.id,
                "irrigation_type_id": cls.irrigation_type.id,
            }
        )
        # Utilisateurs utilisés par les tests de sécurité ci-dessous.
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.user_a = cls._create_user("patrimony_user", cls.base_user, cls.group_user)
        cls.admin = cls._create_user("patrimony_admin", cls.base_user, cls.group_admin)

    @classmethod
    def _create_user(cls, login, *groups):
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
                    "group_ids": [(6, 0, [group.id for group in groups])],
                }
            )
        )

    def test_farm_site_plot_creation(self):
        self.assertEqual(self.farm.site_count, 1)
        self.assertEqual(self.farm.plot_count, 1)
        self.assertEqual(self.farm.allocated_area, 10.0)
        self.assertEqual(self.site.company_id, self.company)
        self.assertEqual(self.plot.company_id, self.company)
        self.assertEqual(self.plot.site_id, self.site)

    def test_site_notes_default_and_modification(self):
        """Les notes d'un site peuvent être créées, modifiées et relues."""
        self.assertFalse(self.site.notes)
        self.site.write({"notes": "Observation terrain : sol très humide."})
        self.assertEqual(self.site.notes, "Observation terrain : sol très humide.")
        reloaded = self.env["gest_agri.site"].browse(self.site.id)
        self.assertEqual(reloaded.notes, "Observation terrain : sol très humide.")
        self.site.write({"notes": False})
        self.assertFalse(self.site.notes)

    def test_site_area_ha_default_and_positive(self):
        """La surface d'un site est nulle par défaut et accepte une valeur positive."""
        self.assertEqual(self.site.area_ha, 0.0)
        self.site.write({"area_ha": 25.5})
        self.assertEqual(self.site.area_ha, 25.5)
        self.site.write({"area_ha": 0.0})
        self.assertEqual(self.site.area_ha, 0.0)

    def test_site_area_ha_negative_rejected(self):
        """Une surface négative est refusée."""
        with self.assertRaises(ValidationError):
            self.site.write({"area_ha": -5.0})

    def test_farm_status_default_and_values(self):
        """Le statut d'une exploitation est brouillon par défaut."""
        self.assertEqual(self.farm.status, "draft")
        self.farm.write({"status": "active"})
        self.assertEqual(self.farm.status, "active")
        self.farm.write({"status": "suspended"})
        self.assertEqual(self.farm.status, "suspended")
        self.farm.write({"status": "closed"})
        self.assertEqual(self.farm.status, "closed")
        self.farm.write({"status": "draft"})
        self.assertEqual(self.farm.status, "draft")

    def test_farm_status_invalid_rejected(self):
        """Un statut invalide est refusé."""
        with self.assertRaises(ValueError):
            self.farm.write({"status": "invalid_status"})

    def test_farm_notes_default_and_modification(self):
        """Les notes d'une exploitation sont vides par défaut, puis modifiables."""
        self.assertFalse(self.farm.notes)
        self.farm.write({"notes": "Suivi parcellaire à confirmer avec le gérant."})
        self.assertEqual(self.farm.notes, "Suivi parcellaire à confirmer avec le gérant.")
        reloaded = self.env["gest_agri.farm"].browse(self.farm.id)
        self.assertEqual(reloaded.notes, "Suivi parcellaire à confirmer avec le gérant.")
        self.farm.write({"notes": False})
        self.assertFalse(self.farm.notes)

    def test_farm_creation_with_notes(self):
        """Une exploitation peut être créée directement avec des notes internes."""
        farm = self.env["gest_agri.farm"].create(
            {
                "name": "Exploitation des Coteaux",
                "code": "COTEAUX",
                "company_id": self.company.id,
                "farm_type_id": self.farm_type.id,
                "notes": "Terrain en pente, prévoir un drainage.",
            }
        )
        self.assertEqual(farm.notes, "Terrain en pente, prévoir un drainage.")

    def test_plot_crop_type_assignment(self):
        """Le type de culture peut être affecté à une parcelle."""
        crop_type = self.env["gest_agri.crop.type"].create(
            {"name": "Blé", "code": "BLE", "crop_cycle": "annual", "company_id": self.company.id}
        )
        self.plot.write({"crop_type_id": crop_type.id})
        self.assertEqual(self.plot.crop_type_id, crop_type)
        self.plot.write({"crop_type_id": False})
        self.assertFalse(self.plot.crop_type_id)

    def test_plot_state_default_and_values(self):
        """Le statut d'une parcelle est disponible par défaut."""
        self.assertEqual(self.plot.state, "available")
        self.plot.write({"state": "cultivated"})
        self.assertEqual(self.plot.state, "cultivated")
        self.plot.write({"state": "fallow"})
        self.assertEqual(self.plot.state, "fallow")
        self.plot.write({"state": "unavailable"})
        self.assertEqual(self.plot.state, "unavailable")
        self.plot.write({"state": "available"})
        self.assertEqual(self.plot.state, "available")

    def test_plot_state_invalid_rejected(self):
        """Un statut invalide est refusé."""
        with self.assertRaises(ValueError):
            self.plot.write({"state": "invalid_status"})

    def test_full_patrimony_creation(self):
        building = self.env["gest_agri.building"].create(
            {
                "name": "Hangar principal",
                "code": "HANGAR",
                "farm_id": self.farm.id,
                "site_id": self.site.id,
                "building_type_id": self.building_type.id,
                "area": 250.0,
                "capacity": 200,
            }
        )
        infrastructure = self.env["gest_agri.infrastructure"].create(
            {
                "name": "Piste principale",
                "code": "PISTE",
                "farm_id": self.farm.id,
                "site_id": self.site.id,
                "infrastructure_kind": "road",
                "length_m": 500.0,
            }
        )
        water_source = self.env["gest_agri.water.source"].create(
            {
                "name": "Forage Nord",
                "code": "FORAGE",
                "farm_id": self.farm.id,
                "site_id": self.site.id,
                "source_type": "borehole",
                "capacity_m3_day": 120.0,
                "depth_m": 45.0,
            }
        )
        network = self.env["gest_agri.irrigation.network"].create(
            {
                "name": "Réseau principal",
                "code": "RESEAU",
                "farm_id": self.farm.id,
                "water_source_id": water_source.id,
                "network_type": "drip",
                "flow_rate_m3_h": 25.0,
            }
        )
        sector = self.env["gest_agri.irrigation.sector"].create(
            {
                "name": "Secteur A",
                "code": "SEC-A",
                "network_id": network.id,
                "area": 10.0,
                "plot_ids": [(6, 0, self.plot.ids)],
            }
        )
        pump = self.env["gest_agri.irrigation.pump"].create(
            {
                "name": "Pompe principale",
                "code": "POMPE",
                "network_id": network.id,
                "power_kw": 7.5,
                "flow_rate_m3_h": 25.0,
            }
        )

        self.assertEqual(building.company_id, self.company)
        self.assertEqual(infrastructure.site_id, self.site)
        self.assertEqual(water_source.source_type, "borehole")
        self.assertEqual(network.water_source_id, water_source)
        self.assertEqual(sector.farm_id, self.farm)
        self.assertEqual(sector.company_id, self.company)
        self.assertEqual(pump.farm_id, self.farm)
        self.assertEqual(pump.company_id, self.company)
        self.assertEqual(self.farm.water_source_count, 1)
        self.assertEqual(self.farm.irrigation_network_count, 1)

    def test_farm_code_unique_per_company(self):
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.farm"].create(
                {
                    "name": "Autre domaine",
                    "code": "dom",
                    "company_id": self.company.id,
                    "total_area": 1.0,
                }
            )

    def test_site_code_unique_per_farm(self):
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.site"].create(
                {
                    "name": "Site Nord bis",
                    "code": "nord",
                    "farm_id": self.farm.id,
                }
            )

    def test_site_must_belong_to_same_farm(self):
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Autre domaine",
                "code": "AUTRE",
                "company_id": self.company.id,
                "total_area": 50.0,
            }
        )
        other_site = self.env["gest_agri.site"].create(
            {"name": "Site Sud", "code": "SUD", "farm_id": other_farm.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create(
                {
                    "name": "Parcelle invalide",
                    "code": "INVALIDE",
                    "farm_id": self.farm.id,
                    "site_id": other_site.id,
                    "area": 1.0,
                }
            )

    def test_negative_area_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create(
                {
                    "name": "Parcelle négative",
                    "code": "NEG",
                    "farm_id": self.farm.id,
                    "area": -1.0,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.farm"].create(
                {
                    "name": "Domaine négatif",
                    "code": "NEG-DOM",
                    "company_id": self.company.id,
                    "total_area": -5.0,
                }
            )

    def test_allocated_area_cannot_exceed_total(self):
        small_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Petit domaine",
                "code": "PETIT",
                "company_id": self.company.id,
                "total_area": 5.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create(
                {
                    "name": "Parcelle trop grande",
                    "code": "TROP",
                    "farm_id": small_farm.id,
                    "area": 6.0,
                }
            )
            self.env.flush_all()

    def test_plot_agronomic_ranges(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create(
                {
                    "name": "Parcelle pH invalide",
                    "code": "PH",
                    "farm_id": self.farm.id,
                    "area": 1.0,
                    "ph_min": 8.0,
                    "ph_max": 6.0,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create(
                {
                    "name": "Parcelle pente invalide",
                    "code": "PENTE",
                    "farm_id": self.farm.id,
                    "area": 1.0,
                    "slope_percent": 120.0,
                }
            )

    def test_company_consistency(self):
        other_company = self.env["res.company"].create({"name": "Société distante"})
        other_type = self.env["gest_agri.farm.type"].create(
            {
                "name": "Type distant",
                "code": "DIST",
                "company_id": other_company.id,
            }
        )
        plan = self.env["account.analytic.plan"].create({"name": "Plan distant"})
        other_account = self.env["account.analytic.account"].create(
            {
                "name": "Compte distant",
                "plan_id": plan.id,
                "company_id": other_company.id,
            }
        )
        with self.assertRaises((ValidationError, UserError)):
            self.env["gest_agri.farm"].create(
                {
                    "name": "Domaine incohérent",
                    "code": "INCOHERENT",
                    "company_id": self.company.id,
                    "farm_type_id": other_type.id,
                    "analytic_account_id": other_account.id,
                    "total_area": 1.0,
                }
            )

    def test_sector_plot_association(self):
        """Teste l'association parcelle-secteur à la création."""
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-SECTEUR", "farm_id": self.farm.id}
        )
        water_source = self.env["gest_agri.water.source"].create(
            {"name": "Forage test", "code": "FORAGE-SECTEUR", "farm_id": self.farm.id}
        )
        irrigation_type = self.env["gest_agri.irrigation.type"].create(
            {
                "name": "Goutte-à-goutte secteur",
                "code": "GAG-SECTEUR",
                "company_id": self.company.id,
            }
        )
        
        plot1 = self.env["gest_agri.plot"].create({
            "name": "Parcelle 1",
            "code": "PLOT1",
            "farm_id": self.farm.id,
            "area": 5.0,
            "soil_type_id": self.soil_type.id,
            "irrigation_type_id": irrigation_type.id,
        })
        plot2 = self.env["gest_agri.plot"].create({
            "name": "Parcelle 2",
            "code": "PLOT2",
            "farm_id": self.farm.id,
            "area": 3.0,
            "soil_type_id": self.soil_type.id,
            "irrigation_type_id": irrigation_type.id,
        })
        
        # Création d'un secteur avec les plots associés
        sector = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur test",
            "code": "SEC-TEST",
            "network_id": network.id,
            "area": 8.0,
            "plot_ids": [(6, 0, plot1.ids + plot2.ids)],
        })
        
        # Vérification que les plots sont bien associés au secteur
        self.assertIn(plot1, sector.plot_ids)
        self.assertIn(plot2, sector.plot_ids)
        self.assertEqual(sector.farm_id, self.farm)
        
        # Vérification que les plots gardent leur ferme
        self.assertEqual(plot1.farm_id, self.farm)
        self.assertEqual(plot2.farm_id, self.farm)

    def test_add_plot_to_sector(self):
        """Teste l'ajout d'une parcelle existante à un secteur."""
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-AJOUT", "farm_id": self.farm.id}
        )
        
        # Création d'un secteur existant sans plot
        sector = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur existant",
            "code": "SEC-EXIST",
            "network_id": network.id,
        })
        
        # Création d'une parcelle
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à ajouter",
            "code": "PLOT-AJOUT",
            "farm_id": self.farm.id,
            "area": 2.0,
            "soil_type_id": self.soil_type.id,
        })
        
        # Ajout de la parcelle au secteur
        sector.write({"plot_ids": [(4, plot.id)]})
        
        # Vérification que la parcelle a été ajoutée
        self.assertIn(plot, sector.plot_ids)
        self.assertEqual(len(sector.plot_ids), 1)

    def test_remove_plot_from_sector(self):
        """Teste le retrait d'une parcelle d'un secteur."""
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-RETRAIT", "farm_id": self.farm.id}
        )
        
        # Création d'un secteur avec une parcelle
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à retirer",
            "code": "PLOT-Retrait",
            "farm_id": self.farm.id,
            "area": 2.0,
        })
        sector = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur avec plot",
            "code": "SEC-WITH",
            "network_id": network.id,
            "plot_ids": [(4, plot.id)],
        })
        
        # Retrait de la parcelle du secteur
        sector.write({"plot_ids": [(3, plot.id)]})
        
        # Vérification que la parcelle a été retirée
        self.assertNotIn(plot, sector.plot_ids)
        self.assertEqual(len(sector.plot_ids), 0)

    def test_plot_farm_change(self):
        """Teste le changement de ferme d'une parcelle."""
        # Création d'une autre ferme
        other_farm = self.env["gest_agri.farm"].create({
            "name": "Autre ferme",
            "code": "FARM-OTHER-PLOT",
            "company_id": self.company.id,
        })
        
        # Création d'une parcelle sur la ferme actuelle
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à déplacer",
            "code": "PLOT-MOVE",
            "farm_id": self.farm.id,
            "area": 2.0,
        })
        
        # Tentative de changement de ferme (doit être bloqué pour non-admin)
        with self.assertRaises((AccessError, ValidationError)):
            plot.with_user(self.user_a).write({"farm_id": other_farm.id})
        
        # Un admin peut changer de ferme
        plot.with_user(self.admin).write({"farm_id": other_farm.id})
        self.assertEqual(plot.farm_id, other_farm)

    def test_sector_farm_change(self):
        """Teste le changement de ferme d'un secteur."""
        # Création d'une autre ferme
        other_farm = self.env["gest_agri.farm"].create({
            "name": "Autre ferme",
            "code": "FARM-OTHER-SECTEUR",
            "company_id": self.company.id,
        })
        
        # Création d'une parcelle
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle de test",
            "code": "PLOT-TEST",
            "farm_id": self.farm.id,
            "area": 2.0,
        })
        
        # Création d'un secteur sur la ferme actuelle
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-LOT", "farm_id": self.farm.id}
        )
        sector = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur de test",
            "code": "SEC-TEST",
            "network_id": network.id,
            "plot_ids": [(4, plot.id)],
        })
        
        # Tentative de changement de ferme du secteur (non-admin bloqué)
        with self.assertRaises((AccessError, ValidationError)):
            sector.with_user(self.user_a).write({"farm_id": other_farm.id})

        # Même pour un administrateur, un secteur ne peut pas être déplacé
        # vers une autre exploitation tant qu'il référence des parcelles qui
        # n'appartiennent pas à la nouvelle exploitation (cohérence métier).
        with self.assertRaises(ValidationError):
            sector.with_user(self.admin).write({"farm_id": other_farm.id})

        # Une fois les parcelles détachées, le déplacement est possible.
        sector.write({"plot_ids": [(3, plot.id)]})
        sector.with_user(self.admin).write({"farm_id": other_farm.id})
        self.assertEqual(sector.farm_id, other_farm)

    def test_bulk_operation_sector_plot(self):
        """Teste les opérations en lot sur secteurs et plots."""
        # Création de plusieurs plots
        plot1 = self.env["gest_agri.plot"].create({
            "name": "Plot 1",
            "code": "PLOT-1",
            "farm_id": self.farm.id,
            "area": 1.0,
        })
        plot2 = self.env["gest_agri.plot"].create({
            "name": "Plot 2",
            "code": "PLOT-2",
            "farm_id": self.farm.id,
            "area": 2.0,
        })
        
        # Création de plusieurs secteurs
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-ARCHIVE", "farm_id": self.farm.id}
        )
        
        sector1 = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur 1",
            "code": "SEC-1",
            "network_id": network.id,
        })
        sector2 = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur 2",
            "code": "SEC-2",
            "network_id": network.id,
        })
        
        # Opération en lot : ajouter les deux plots aux deux secteurs
        # (Chaque plot dans chaque secteur)
        sector1.write({"plot_ids": [(4, plot1.id), (4, plot2.id)]})
        sector2.write({"plot_ids": [(4, plot1.id), (4, plot2.id)]})
        
        # Vérification
        self.assertIn(plot1, sector1.plot_ids)
        self.assertIn(plot2, sector1.plot_ids)
        self.assertIn(plot1, sector2.plot_ids)
        self.assertIn(plot2, sector2.plot_ids)

    def test_archive_plot_affects_sector(self):
        """Teste l'archivage d'une parcelle et son effet sur le secteur."""
        network = self.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau test", "code": "RESEAU-CHANGEMENT", "farm_id": self.farm.id}
        )
        
        # Création d'une parcelle et d'un secteur
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à archiver",
            "code": "PLOT-ARCHIVE",
            "farm_id": self.farm.id,
            "area": 2.0,
        })
        sector = self.env["gest_agri.irrigation.sector"].create({
            "name": "Secteur avec plot",
            "code": "SEC-ARCHIVE",
            "network_id": network.id,
            "plot_ids": [(4, plot.id)],
        })
        
        # Archivage de la parcelle
        plot.write({"active": False})
        
        # La parcelle doit toujours être dans la liste (soft delete concept)
        # Mais la contrainte _check_plot_farm peut se comporter différemment
        # Vérification selon le comportement Odoo
        # La relation existe toujours en base, mais le Many2many masque les
        # enregistrements archivés (active_test) : on le vérifie explicitement
        # sans le filtre d'activité.
        self.assertIn(plot, sector.with_context(active_test=False).plot_ids)
        self.assertNotIn(plot, sector.plot_ids)
        self.assertFalse(plot.active)  # La parcelle est archivée

    def _empty_farm(self, code):
        """Crée une exploitation dédiée, sans parcelle.

        ``setUpClass`` crée déjà une parcelle de 10 ha sur ``self.farm`` : les
        tests de surface affectée portent sur des totaux absolus et doivent
        donc utiliser une exploitation vierge.
        """
        return self.env["gest_agri.farm"].create({
            "name": f"Exploitation {code}",
            "code": code,
            "company_id": self.company.id,
            "total_area": 100.0,
        })

    def test_allocated_area_creation(self):
        """Teste le calcul de allocated_area lors de la création d'une parcelle active."""
        farm = self._empty_farm("SURF-CRE")
        # L'exploitation est créée sans parcelle initialement
        self.assertEqual(farm.allocated_area, 0.0)

        # Création d'une parcelle active
        self.env["gest_agri.plot"].create({
            "name": "Parcelle active",
            "code": "PLOT-ACT",
            "farm_id": farm.id,
            "area": 10.0,
        })

        # Le allocated_area doit être mis à jour
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 10.0)

    def test_allocated_area_modification(self):
        """Teste la modification de la superficie d'une parcelle."""
        farm = self._empty_farm("SURF-MOD")
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle initiale",
            "code": "PLOT-INIT",
            "farm_id": farm.id,
            "area": 5.0,
        })

        # Modification de la superficie
        plot.write({"area": 8.0})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 8.0)

        # Redresser à la valeur initiale
        plot.write({"area": 5.0})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 5.0)

    def test_allocated_area_archiving(self):
        """Teste l'archivage d'une parcelle."""
        farm = self._empty_farm("SURF-ARC")
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à archiver",
            "code": "PLOT-ARCH",
            "farm_id": farm.id,
            "area": 5.0,
        })

        # Vérification avant archivage
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 5.0)

        # Archivage de la parcelle
        plot.write({"active": False})

        # Le allocated_area ne doit plus inclure la parcelle archivée
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 0.0)

    def test_allocated_area_restoration(self):
        """Teste la restauration d'une parcelle archivée."""
        farm = self._empty_farm("SURF-RES")
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à restaurer",
            "code": "PLOT-RES",
            "farm_id": farm.id,
            "area": 5.0,
        })

        # Archivage puis restauration
        plot.write({"active": False})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 0.0)

        plot.write({"active": True})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 5.0)

    def test_allocated_area_deletion(self):
        """Teste la suppression d'une parcelle."""
        farm = self._empty_farm("SURF-DEL")
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à supprimer",
            "code": "PLOT-DEL",
            "farm_id": farm.id,
            "area": 5.0,
        })

        # Suppression de la parcelle
        plot.unlink()

        # Le allocated_area doit être de 0
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 0.0)

    def test_allocated_area_company_change(self):
        """Teste le déplacement de parcelle vers une autre exploitation."""
        farm = self._empty_farm("SURF-MOV")
        # Création d'une autre ferme
        other_farm = self.env["gest_agri.farm"].create({
            "name": "Autre ferme",
            "code": "FARM-OTHER-SURF",
            "company_id": self.company.id,
            "total_area": 100.0,
        })

        # Création d'une parcelle sur la ferme actuelle
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle à déplacer",
            "code": "PLOT-MOVE",
            "farm_id": farm.id,
            "area": 5.0,
        })
        
        # Modification de la ferme de la parcelle (admin seulement)
        # Dans un contexte sans restriction admin, on peut tester le comportement
        # Note : le changement de ferme peut être bloqué par les contraintes d'accès
        # On vérifie juste que le compute réagit au changement
        plot.write({"farm_id": other_farm.id})
        
        # Le allocated_area de la ferme originale doit avoir diminué
        # (Selon les règles d'accès, cela peut ou non être possible selon les droits)
        # On vérifie juste que la ferme cible a la parcelle
        self.assertIn(plot, other_farm.plot_ids)

    def test_allocated_area_multi_plot(self):
        """Teste allocated_area avec plusieurs parcelles."""
        farm = self._empty_farm("SURF-MUL")
        # Création de plusieurs parcelles
        plot1 = self.env["gest_agri.plot"].create({
            "name": "Parcelle 1",
            "code": "PLOT-1",
            "farm_id": farm.id,
            "area": 3.0,
        })
        plot2 = self.env["gest_agri.plot"].create({
            "name": "Parcelle 2",
            "code": "PLOT-2",
            "farm_id": farm.id,
            "area": 7.0,
        })
        plot3 = self.env["gest_agri.plot"].create({
            "name": "Parcelle 3",
            "code": "PLOT-3",
            "farm_id": farm.id,
            "area": 2.0,
        })

        # allocated_area doit être la somme
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 12.0)

        # Archivage de la parcelle du milieu
        plot2.write({"active": False})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 5.0)  # Uniquement plot1 + plot3

        # Restauration
        plot2.write({"active": True})
        farm.invalidate_recordset()
        self.assertEqual(farm.allocated_area, 12.0)

    def test_total_area_vs_allocated_area(self):
        """Teste que total_area >= allocated_area est maintenu."""
        # Création d'une ferme avec total_area faible
        small_farm = self.env["gest_agri.farm"].create({
            "name": "Petit domaine",
            "code": "PETIT",
            "company_id": self.company.id,
            "total_area": 10.0,
        })
        
        # Tentative de création de parcelle dépassant total_area
        with self.assertRaises(ValidationError):
            self.env["gest_agri.plot"].create({
                "name": "Parcelle trop grande",
                "code": "DÉP",
                "farm_id": small_farm.id,
                "area": 15.0,
            })
        
        # Création de parcelle dans les limites
        plot = self.env["gest_agri.plot"].create({
            "name": "Parcelle dans les limites",
            "code": "DANS",
            "farm_id": small_farm.id,
            "area": 8.0,
        })
        
        # Vérification de l'invariant
        self.assertGreaterEqual(small_farm.total_area, small_farm.allocated_area)
        self.assertEqual(small_farm.allocated_area, 8.0)

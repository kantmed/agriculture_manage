import uuid

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAgricultureStock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation test stock",
            "company_id": cls.company.id,
            "total_area": 10,
        })

    def test_product_agriculture_classification_fields(self):
        template = self.env["product.template"].create({
            "name": "Semence test",
            "agriculture_category": "seed",
        })
        self.assertEqual(template.agriculture_category, "seed")
        self.assertTrue(template.agriculture_is_input)

    def test_operation_line_uses_company_currency(self):
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Opération test devise",
        })
        line = self.env["agriculture.farm.operation.line"].create({
            "operation_id": operation.id,
            "name": "Intrant test",
        })

        self.assertEqual(line.currency_id, self.company.currency_id)

    def test_stock_consumption_rejects_incompatible_unit(self):
        product = self.env["product.template"].create({
            "name": "Produit avec unité test",
        }).product_variant_id
        warehouse = self.env["stock.warehouse"].create({
            "name": "Magasin unité test",
            "code": "UTS",
            "company_id": self.company.id,
        })
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Opération unité test",
        })
        line = self.env["agriculture.farm.operation.line"].create({
            "operation_id": operation.id,
            "name": "Ligne unité test",
            "product_id": product.id,
            "warehouse_id": warehouse.id,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })

        with self.assertRaises(ValidationError):
            line.consume_stock = True

    def test_prepare_stock_issue_uses_company_production_location(self):
        crop = self.env["agriculture.farm.crop"].create({
            "name": "Culture stock test",
            "crop_type_id": self.env.ref("agriculture_manage_crop.crop_type_cereal").id,
            "abbreviation": f"S{uuid.uuid4().hex[:12]}",
        })
        campaign = self.env["agriculture.farm.crop.campaign"].create({
            "name": "Campagne stock test",
            "farm_id": self.farm.id,
            "crop_id": crop.id,
        })
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Opération sortie stock test",
            "campaign_id": campaign.id,
        })
        warehouse = self.env["stock.warehouse"].create({
            "name": "Magasin sortie test",
            "code": "SIT",
            "company_id": self.company.id,
        })
        product = self.env["product.template"].create({
            "name": "Intrant stock test",
            "is_storable": True,
        }).product_variant_id
        self.env["agriculture.farm.operation.line"].create({
            "operation_id": operation.id,
            "name": "Intrant test",
            "product_id": product.id,
            "warehouse_id": warehouse.id,
            "quantity": 1,
            "uom_id": product.uom_id.id,
            "consume_stock": True,
        })

        operation.action_prepare_stock_issue()

        picking = operation.stock_picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.location_dest_id.usage, "production")
        self.assertEqual(picking.location_dest_id.company_id, self.company)

    def test_warehouse_cannot_belong_to_farm_of_another_company(self):
        other_company = self.env["res.company"].create({"name": "Autre société test"})
        other_farm = self.env["agriculture.farm"].create({
            "name": "Exploitation autre société",
            "company_id": other_company.id,
            "total_area": 10,
        })
        warehouse = self.env["stock.warehouse"].create({
            "name": "Magasin test stock",
            "code": "TST",
            "company_id": self.company.id,
        })
        with self.assertRaises(ValidationError):
            warehouse.farm_id = other_farm

    def test_operation_validation_does_not_create_duplicate_stock_picking(self):
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Opération sans consommation stock",
        })
        product = self.env["product.template"].create({
            "name": "Produit prestation test",
            "is_storable": True,
        }).product_variant_id
        self.env["agriculture.farm.operation.line"].create({
            "operation_id": operation.id,
            "name": "Ligne non stock",
            "product_id": product.id,
            "quantity": 1,
            "uom_id": product.uom_id.id,
            "consume_stock": False,
        })

        operation.action_validate()

        self.assertEqual(operation.state, "done")
        self.assertFalse(operation.stock_picking_ids)

    def test_prepared_move_is_linked_to_operation_line(self):
        crop = self.env["agriculture.farm.crop"].create({
            "name": "Culture lien stock test",
            "crop_type_id": self.env.ref("agriculture_manage_crop.crop_type_cereal").id,
            "abbreviation": f"L{uuid.uuid4().hex[:12]}",
        })
        campaign = self.env["agriculture.farm.crop.campaign"].create({
            "name": "Campagne lien stock test",
            "farm_id": self.farm.id,
            "crop_id": crop.id,
        })
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Opération lien stock test",
            "campaign_id": campaign.id,
        })
        warehouse = self.env["stock.warehouse"].create({
            "name": "Magasin lien test",
            "code": "LST",
            "company_id": self.company.id,
        })
        product = self.env["product.template"].create({
            "name": "Intrant lien test",
            "is_storable": True,
        }).product_variant_id
        line = self.env["agriculture.farm.operation.line"].create({
            "operation_id": operation.id,
            "name": "Ligne intrant lien",
            "product_id": product.id,
            "warehouse_id": warehouse.id,
            "quantity": 1,
            "uom_id": product.uom_id.id,
            "consume_stock": True,
        })

        operation.action_prepare_stock_issue()

        self.assertEqual(len(line.stock_move_ids), 1)
        self.assertEqual(line.stock_move_ids.agriculture_operation_line_id, line)
        self.assertEqual(line.stock_move_id, line.stock_move_ids[:1])

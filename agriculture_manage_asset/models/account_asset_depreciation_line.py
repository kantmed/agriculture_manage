from odoo import models


class AccountAssetDepreciationLine(models.Model):
    _inherit = "account.asset.depreciation.line"

    def create_move(self, post_move=True):
        """Create entries first, apply farm analytics, then post when requested."""
        move_ids = super().create_move(post_move=False)
        moves = self.env["account.move"].browse(move_ids)
        for depreciation in self.filtered(lambda line: line.move_id):
            asset = depreciation.asset_id
            distribution = asset._agriculture_get_analytic_distribution()
            if not distribution:
                continue
            expense_lines = depreciation.move_id.line_ids.filtered(
                lambda line: line.account_id == asset.account_depreciation_expense_id
            )
            for expense_line in expense_lines:
                expense_line.analytic_distribution = distribution
        if post_move and moves:
            lines_to_post = self.filtered(
                lambda line: line.move_id and line.asset_id.open_asset
            )
            moves_to_post = lines_to_post.mapped("move_id")
            if moves_to_post:
                moves_to_post.action_post()
        return moves.ids

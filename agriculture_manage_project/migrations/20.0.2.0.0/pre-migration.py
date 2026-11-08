def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    # Projects must no longer be linked to agricultural campaigns or campaign budgets.
    for column in ("agriculture_campaign_id", "agriculture_budget_id"):
        if _column_exists(cr, "project_project", column):
            cr.execute('UPDATE project_project SET "%s" = NULL WHERE "%s" IS NOT NULL' % (column, column))
    if _column_exists(cr, "project_task", "agriculture_campaign_id"):
        cr.execute(
            "UPDATE project_task SET agriculture_campaign_id = NULL "
            "WHERE agriculture_campaign_id IS NOT NULL"
        )

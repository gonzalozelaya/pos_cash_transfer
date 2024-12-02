{
    "name": "POS Cash Transfer",
    "version": "1.0",
    "depends": ["point_of_sale", "account"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "/pos_cash_transfer/static/src/js/cash_move_popup.js",
            "/pos_cash_transfer/static/src/xml/pos_cash_transfer_views.xml",
        ],
    },
    "installable": True,
    "application": False,
}
from import_data_func.add_new_category import import_categories_from_csv
from import_exampla_data_func.add_new_Product import example_import_all_product
from import_exampla_data_func.add_new_package import example_import_all_packages
from import_exampla_data_func.add_others_investments import example_import_all_investment
from postgreSQLConnect import db_session
from app import app


def run_import():
    example_import_all_product()
    example_import_all_packages()
    example_import_all_investment()
    import_categories_from_csv(
        '../example_import_data_csv/csv_categories/categories.csv',
        db_session
    )


if __name__ == "__main__":
    with app.app_context():
        run_import()
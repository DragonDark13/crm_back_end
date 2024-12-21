from datetime import datetime
import logging
from decimal import Decimal

from peewee import Model, CharField, FloatField, IntegerField, SqliteDatabase, IntegrityError

# Ініціалізуємо базу даних
from models import StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Product, UserRole, \
    Customer, User

db = SqliteDatabase('shop_crm.db')

# Створюємо таблицю в базі даних
db.connect()
db.drop_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Customer,
                UserRole, User])
db.create_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Customer,
                  UserRole, User])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Приклад додавання товарів
# data = [
# {"name": "Палочка Воландеморта", "supplier_name": "skladoptom.com.ua", "quantity": 1, "purchase_total_price": 507.6,
#  "purchase_price_per_item": 507.6},
# {"name": "Палочка Грюма", "supplier_name": "skladoptom.com.ua", "quantity": 1, "purchase_total_price": 507.6,
#  "purchase_price_per_item": 507.6},
# {"name": "Брелок с гербом Пуффендуя", "supplier_name": "skladoptom.com.ua", "quantity": 1,
#  "purchase_total_price": 65.49,
#  "purchase_price_per_item": 65.49},
# {"name": "Брелок с гербом Когтевран", "supplier_name": "misteria.prom.ua", "quantity": 1,
#  "purchase_total_price": 86,
#  "purchase_price_per_item": 86},
# {"name": "Брелок Дары Смерти", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 81,
#  "purchase_price_per_item": 81},
# {"name": "Брелок Грифиндор круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 60,
#  "purchase_price_per_item": 60},
# {"name": "Брелок Слизерин круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 60,
#  "purchase_price_per_item": 60},
# {"name": "Брелок Когтевран круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 60,
#  "purchase_price_per_item": 60},
# {"name": "Брелок Пуфендуй круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 60,
#  "purchase_price_per_item": 60},
# {"name": "Брелок Хогвартс круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 0,
#  "purchase_price_per_item": 0},
# {"name": "Светильник Сова", "supplier_name": "misteria.prom.ua", "quantity": 1, "purchase_total_price": 390,
#  "purchase_price_per_item": 390},
# {"name": "Сервиз чайный Хогвартс", "supplier_name": "Настя @tykkinykki", "quantity": 1,
#  "purchase_total_price": 3800,
#  "purchase_price_per_item": 3800},
# {"name": "Шарф Гриффиндор", "supplier_name": "Татьяна Явтуховская", "quantity": 1, "purchase_total_price": 900,
#  "purchase_price_per_item": 900},
# {"name": "Чашка с молнией", "supplier_name": "starsandsky.com.ua", "quantity": 1, "purchase_total_price": 165,
#  "purchase_price_per_item": 165},
# {"name": "Чашка с гербом Хогвартса", "supplier_name": "starsandsky.com.ua", "quantity": 1,
#  "purchase_total_price": 165,
#  "purchase_price_per_item": 165},
# {"name": "Чашка с оленем", "supplier_name": "starsandsky.com.ua", "quantity": 1, "purchase_total_price": 165,
#  "purchase_price_per_item": 165},
# {"name": "Чашка с совой", "supplier_name": "starsandsky.com.ua", "quantity": 1, "purchase_total_price": 135,
#  "purchase_price_per_item": 135},
# {"name": "Чашка с башней", "supplier_name": "starsandsky.com.ua", "quantity": 1, "purchase_total_price": 135,
#  "purchase_price_per_item": 135},
# {"name": "Мешочки тканевые 23х17", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
#  "quantity": 1, "purchase_total_price": 92, "purchase_price_per_item": 23},
# {"name": "Мешочки тканевые 13х10", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
#  "quantity": 1, "purchase_total_price": 100, "purchase_price_per_item": 10},
# {"name": "Мешочки тканевые 10х8", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
#  "quantity": 1, "purchase_total_price": 120, "purchase_price_per_item": 8}
# ]


data = [
    {"name": "Шоколад", "quantity": 3, "selling_price_per_item": 280},
    {"name": "Грифіндорський шарф", "quantity": 1, "selling_price_per_item": 1350},
    {"name": "Паличка Волдеморта", "quantity": 1, "selling_price_per_item": 810},
    {"name": "Паличка Аластора Грюма", "quantity": 1, "selling_price_per_item": 760},
    {"name": "Набір для каліграфії", "quantity": 1, "selling_price_per_item": 350},
    {"name": "Світильник 'Сова'", "quantity": 1, "selling_price_per_item": 600},
    {"name": "Чашка учня Гогвордсу", "quantity": 2, "selling_price_per_item": 300},
    {"name": "Чай 'Амортензія'", "quantity": 2, "selling_price_per_item": 60},
    {"name": "Набір шкарпеток ГП 36-42р.", "quantity": 6, "selling_price_per_item": 70},
    {"name": "Набір шкарпеток ГП 41-45р.", "quantity": 6, "selling_price_per_item": 70},
    {"name": "Карта Мародерів", "quantity": 2, "selling_price_per_item": 375},
    {"name": "Драконячі яйця", "quantity": 5, "selling_price_per_item": 25},
    {"name": "Ручки що ростуть", "quantity": 4, "selling_price_per_item": 55},
    {"name": "Олівці що ростуть", "quantity": 5, "selling_price_per_item": 45},
    {"name": "Набір з олівців що ростуть (12 шт)", "quantity": 1, "selling_price_per_item": 450},
    {"name": "Окуляри Гаррі Поттера", "quantity": 4, "selling_price_per_item": 65},
    {"name": "Ложки дерев'яні", "quantity": 2, "selling_price_per_item": 135},
    {"name": "Ложка дерев'яна з чаєм", "quantity": 1, "selling_price_per_item": 170},
    {"name": "Диплом про закінчення Хогвардса в рамці", "quantity": 3, "selling_price_per_item": 240},
    {"name": "Пазл Хатинка Гегріда без рамці", "quantity": 5, "selling_price_per_item": 360},
    {"name": "Записник учня Гогвордсу", "quantity": 5, "selling_price_per_item": 65},
    {"name": "Диплом про закінчення Гогвордсу", "quantity": 5, "selling_price_per_item": 240},
    {"name": "Лист з Гогвордсу", "quantity": 5, "selling_price_per_item": 30},
    {"name": "Квиток на автобус", "quantity": 5, "selling_price_per_item": 45},
    {"name": "Квиток на Гогвардс Експресс", "quantity": 2, "selling_price_per_item": 45},
    {"name": "Готовий набір лист з Гогвордсу", "quantity": 2, "selling_price_per_item": 200},
    {"name": "Гребінець", "quantity": 1, "selling_price_per_item": 350},
    {"name": "Кулон Маховик Часу", "quantity": 1, "selling_price_per_item": 160},
    {"name": "Кулон Платформа 9 3/4", "quantity": 2, "selling_price_per_item": 150},
    {"name": "Брелок Гогвордс", "quantity": 1, "selling_price_per_item": 140},
    {"name": "Брелок Гафлпафф", "quantity": 1, "selling_price_per_item": 140},
    {"name": "Чокер синій", "quantity": 1, "selling_price_per_item": 290},
    {"name": "Газета 'Щоденний віщун'", "quantity": 5, "selling_price_per_item": 120},
    {"name": "Свічки що вмикаются дотиком", "quantity": 8, "selling_price_per_item": 145},
    {"name": "Свічка Доббі", "quantity": 1, "selling_price_per_item": 400},
    {"name": "Свічка Розподільчий капелюх", "quantity": 1, "selling_price_per_item": 90},
    {"name": "Свічка Вежа Гогвордсу", "quantity": 2, "selling_price_per_item": 285},
    {"name": "Свічка Мандрагора в Горщику", "quantity": 1, "selling_price_per_item": 400},
    {"name": "Свічка Дамблдор", "quantity": 1, "selling_price_per_item": 210},
    {"name": "Свічка Снейп", "quantity": 1, "selling_price_per_item": 285},
    {"name": "Свічка Макгонагал", "quantity": 1, "selling_price_per_item": 150},
    {"name": "Карта Гогвордс", "quantity": 1, "selling_price_per_item": 255},
    {"name": "Рюкзак", "quantity": 1, "selling_price_per_item": 1950}
]

# Створення початкових категорій у базі даних
categories = ['Сувеніри', 'Гаррі Поттер', 'Володар Перснів']

for category_name in categories:
    Category.get_or_create(name=category_name)

    # Функція для завантаження продуктів у базу даних


def load_products_to_db(data):
    """Створює новий товар та обробляє його закупівлю."""
    logging.info(f"Array '{data}'.")

    for product_data in data:
        logging.info(f"Processing product '{product_data}'.")

        # Дефолтна категорія на випадок відсутності категорії у даних
        default_category = Category.get_or_create(name='Сувеніри')[0]

        # Перевірка обов'язкових полів для створення продукту
        required_product_fields = ['name']
        missing_product_fields = [field for field in required_product_fields if field not in product_data]
        if missing_product_fields:
            logging.error(f"Missing required fields for product: {', '.join(missing_product_fields)}")
            continue

        # Перевірка обов'язкових полів для закупки
        required_purchase_fields = ['quantity']
        missing_purchase_fields = [field for field in required_purchase_fields if field not in product_data]
        if missing_purchase_fields:
            logging.error(f"Missing required fields for purchase: {', '.join(missing_purchase_fields)}")
            continue

        # Перевірка кількості на позитивність
        quantity = float(product_data['quantity'])
        if quantity <= 0:
            # Якщо кількість менша або дорівнює 0, просто створюємо продукт без запису закупки
            try:
                supplier_name = product_data.get('supplier_name', "Unknown Supplier")
                supplier, created = Supplier.get_or_create(name=supplier_name)
                created_date = product_data.get('created_date', datetime.now())

                # Створюємо продукт з початковою кількістю 0
                product, product_created = Product.get_or_create(
                    name=product_data['name'],
                    supplier=supplier,
                    defaults={
                        'quantity': 0,  # Початкова кількість 0
                        'purchase_total_price': 0,
                        'purchase_price_per_item': 0,
                        'selling_total_price': 0,
                        'selling_price_per_item': product_data.get('selling_price_per_item', 0),
                        'created_date': created_date
                    }
                )

                logging.info(f"Product '{product_data['name']}' created without purchase. Quantity is zero.")
                continue  # Перейти до наступного продукту, не обробляючи закупку

            except IntegrityError as e:
                logging.error(f"Error adding product '{product_data['name']}': {e}")
                continue  # Продовжити до наступного продукту

        # Валідація ціни за одиницю
        try:
            purchase_price_per_item = float(
                product_data.get('purchase_price_per_item', 0))  # Якщо значення немає, встановлюємо 0
            if purchase_price_per_item <= 0:
                logging.info(
                    f"Invalid purchase price for product '{product_data.get('name', 'Unknown')}'. Setting it to 0.")
                purchase_price_per_item = 0  # Встановлюємо 0 для недійсного значення
        except (ValueError, TypeError):
            logging.error(
                f"Invalid purchase price format for product '{product_data.get('name', 'Unknown')}'. Setting it to 0.")
            purchase_price_per_item = 0  # Встановлюємо 0 для недійсного формату

        try:
            # Знаходимо або створюємо постачальника
            supplier_name = product_data.get('supplier_name', "Unknown Supplier")
            supplier, created = Supplier.get_or_create(name=supplier_name)
            created_date = product_data.get('created_date', datetime.now())

            # Створюємо або знаходимо продукт
            product, product_created = Product.get_or_create(
                name=product_data['name'],
                supplier=supplier,
                defaults={
                    'quantity': 0,  # Початкова кількість 0
                    'purchase_total_price': 0,
                    'purchase_price_per_item': 0,
                    'selling_total_price': 0,
                    'selling_price_per_item': product_data.get('selling_price_per_item', 0),
                    'created_date': created_date
                }
            )

            # Оновлюємо категорії продукту
            category_ids = product_data.get('category_ids', [default_category.id])
            if category_ids:
                categories = Category.select().where(Category.id.in_(category_ids))
                for category in categories:
                    ProductCategory.create(product=product, category=category)

            # Оновлюємо інформацію про продукт після закупки
            purchase_total_price = Decimal(
                product_data.get('purchase_total_price', 0))  # Якщо ключ відсутній, використовується 0
            product.quantity += quantity
            product.purchase_total_price += purchase_total_price
            product.purchase_price_per_item = Decimal(
                product_data.get('purchase_price_per_item', 0))
            product.save()

            # Створюємо запис в історії закупок
            PurchaseHistory.create(
                product=product,
                purchase_price_per_item=purchase_price_per_item,
                purchase_total_price=purchase_total_price,
                supplier=supplier,
                purchase_date=product_data.get('purchase_date', datetime.now()),
                quantity_purchase=quantity
            )

            # Оновлюємо StockHistory
            StockHistory.create(
                product=product,
                change_amount=quantity,
                change_type='create',
                timestamp=product_data.get('purchase_date', datetime.now())
            )

            logging.info(f"Product '{product_data['name']}' added successfully.")

        except IntegrityError as e:
            logging.error(f"Error adding product '{product_data['name']}': {e}")


# Виклик функції
load_products_to_db(data)

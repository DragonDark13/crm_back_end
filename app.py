from datetime import datetime
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_migrate import Migrate
from peewee import SqliteDatabase, fn, SQL, IntegrityError
from playhouse.shortcuts import model_to_dict
from models import Product, StockHistory, PurchaseHistory, SaleHistory, \
    Category, ProductCategory, Supplier, User, Customer  # Імпортуємо модель Product з файлу models.py

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Підключаємо базу даних
db = SqliteDatabase('shop_crm.db')
migrate = Migrate(app, db)


def verify_product_sale_history():
    products = Product.select()  # Отримуємо всі продукти

    for product in products:
        # Підраховуємо загальну кількість проданих товарів і суму продажів для кожного продукту
        sale_records = SaleHistory.select().where(SaleHistory.product == product)

        total_quantity_sold = sum(record.quantity_sold for record in sale_records)
        total_selling_price = sum(record.selling_total_price for record in sale_records)

        # Порівнюємо з полями product.selling_quantity та product.selling_total_price
        if total_quantity_sold == product.selling_quantity and total_selling_price == product.selling_total_price:
            print(f"Product '{product.name}' verification successful!")
        else:
            print(f"Product '{product.name}' verification failed!")
            print(f"Expected quantity sold: {product.selling_quantity}, calculated: {total_quantity_sold}")
            print(f"Expected total selling price: {product.selling_total_price}, calculated: {total_selling_price}")


# Виклик перевірки при запуску програми
verify_product_sale_history()


@app.route('/api/products', methods=['GET'])
def get_products():
    """Отримати всі товари разом з категоріями"""
    products = Product.select()
    product_list = []

    for product in products:
        # Перетворюємо продукт в словник і додаємо категорії
        product_dict = model_to_dict(product, exclude=[ProductCategory])

        # Переконайтесь, що purchase_total_price і purchase_price_per_item у форматі чисел
        product_dict['purchase_total_price'] = float(product.purchase_total_price)
        product_dict['purchase_price_per_item'] = float(product.purchase_price_per_item)

        if product.selling_total_price:
            product_dict['selling_total_price'] = float(product.selling_total_price)
        else:
            product_dict['selling_total_price'] = float('0.00')  # ��кщо продажу немає

        if product.selling_price_per_item:
            product_dict['selling_price_per_item'] = float(product.selling_price_per_item)
        else:
            product_dict['selling_price_per_item'] = 0.00  # ��кщо продажу немає

        # Отримуємо категорії продукту
        product_dict['category_ids'] = [pc.category.id for pc in product.categories]

        # Додаємо постачальника продукту (якщо він є)
        if product.supplier:
            product_dict['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_info': product.supplier.contact_info
            }
        else:
            product_dict['supplier'] = None  # Якщо постачальника немає

        product_list.append(product_dict)
    return jsonify(product_list), 200


@app.route('/api/product', methods=['POST'])
def create_and_purchase_product():
    """Створити новий товар і обробити закупку"""
    data = request.get_json()

    # Перевірка обов'язкових полів для створення продукту
    required_product_fields = ['name', 'category_ids', 'created_date']
    missing_product_fields = [field for field in required_product_fields if field not in data]
    if missing_product_fields:
        return jsonify({'error': f"Missing required fields for product: {', '.join(missing_product_fields)}"}), 400

    # Перевірка обов'язкових полів для закупки
    required_purchase_fields = ['quantity', 'purchase_price_per_item', 'purchase_total_price', 'supplier_id']
    missing_purchase_fields = [field for field in required_purchase_fields if field not in data]
    if missing_purchase_fields:
        return jsonify({'error': f"Missing required fields for purchase: {', '.join(missing_purchase_fields)}"}), 400

    errors = {}

    # Валідація кількості
    try:
        quantity = float(data['quantity'])
        if quantity <= 0:
            errors['quantity'] = "Quantity must be greater than 0."
    except ValueError:
        errors['quantity'] = "Quantity must be a valid number."

    # Валідація ціни за одиницю
    try:
        purchase_price_per_item = float(data['purchase_price_per_item'])
        if purchase_price_per_item <= 0:
            errors['purchase_price_per_item'] = "Price per item must be greater than 0."
    except ValueError:
        errors['purchase_price_per_item'] = "Price per item must be a valid number."

    # Якщо є помилки валідації, повертаємо їх
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        # Створення нового продукту з кількістю 0
        product = Product.create(
            name=data['name'],
            quantity=0,  # Початкова кількість 0
            created_date=data.get('created_date', datetime.now())
        )

        # Оновлюємо категорії
        category_ids = data.get('category_ids', [])
        if category_ids:
            categories = Category.select().where(Category.id.in_(category_ids))
            for category in categories:
                ProductCategory.create(product=product, category=category)

        # Обробка закупки
        supplier_id = data['supplier_id']
        try:
            supplier = Supplier.get(Supplier.id == supplier_id)
            product.supplier = supplier
        except Supplier.DoesNotExist:
            return jsonify({'error': 'Supplier not found'}), 404

        purchase_total_price = Decimal(data['purchase_total_price'])
        product.quantity += quantity
        product.purchase_total_price = purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item
        product.selling_price_per_item = Decimal(data['selling_price_per_item'])

        product.save()

        # Створення нового запису в історії закупок
        PurchaseHistory.create(
            product=product,
            purchase_price_per_item=purchase_price_per_item,
            purchase_total_price=purchase_total_price,
            supplier=supplier,
            purchase_date=data.get('purchase_date', datetime.now()),
            quantity_purchase=quantity
        )

        # Оновлення StockHistory
        StockHistory.create(
            product=product,
            change_amount=quantity,
            change_type='create',
            timestamp=data.get('purchase_date', datetime.now())
        )

        # Повертаємо створений продукт у вигляді JSON
        created_product = model_to_dict(product, backrefs=True, exclude=[ProductCategory])
        return jsonify(created_product), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Отримати товар за ID"""
    try:
        product = Product.get(Product.id == product_id)
        return jsonify(model_to_dict(product)), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Оновити товар з валідацією і збереженням всіх змін"""
    data = request.get_json()

    # Перевірка обов'язкових полів
    required_fields = ['quantity', 'purchase_price_per_item', 'purchase_total_price', 'created_date']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

    errors = {}

    # Валідація полів
    try:
        quantity = float(data['quantity'])
        if quantity < 0:
            errors['quantity'] = "Quantity must be greater than or equal to 0."
    except ValueError:
        errors['quantity'] = "Quantity must be a valid number."

    try:
        purchase_price_per_item = float(data['purchase_price_per_item'])
        if purchase_price_per_item < 0:
            errors['purchase_price_per_item'] = "Price per item must be greater than or equal to 0."
    except ValueError:
        errors['purchase_price_per_item'] = "Price per item must be a valid number."

    # expected_total_price = quantity * purchase_price_per_item
    purchase_total_price = data.get('purchase_total_price')
    selling_price_per_item = data.get('selling_price_per_item')

    # if purchase_total_price != expected_total_price:
    #     errors['purchase_total_price'] = f"Total price should be {expected_total_price}, but received {purchase_total_price}."

    # Якщо є помилки валідації, повертаємо їх
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        # Перевіряємо, чи існує продукт
        product = Product.get(Product.id == product_id)

        # Оновлюємо постачальника, якщо він був переданий
        supplier_id = data.get('supplier_id')
        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        created_date = data.get('created_date')

        # Оновлення поля created_date у продукті
        if created_date:
            product.created_date = created_date
        else:
            product.created_date = datetime.now()

        # Розрахунок зміни кількості
        change_amount = data['quantity'] - product.quantity

        # Оновлення полів продукту
        product.quantity = quantity
        product.purchase_total_price = purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item
        product.selling_price_per_item = selling_price_per_item

        # Оновлюємо категорії, якщо вони передані
        category_ids = data.get('category_ids', [])
        if category_ids:
            # Очищаємо попередні категорії
            ProductCategory.delete().where(ProductCategory.product == product).execute()

            # Додаємо нові категорії
            categories = Category.select().where(Category.id.in_(category_ids))
            for category in categories:
                ProductCategory.create(product=product, category=category)

        product.save()

        # # Запис змін в історію
        # if change_amount != 0:
        #     change_type = 'add' if change_amount > 0 else 'subtract'
        #     StockHistory.create(
        #         product=product,
        #         change_amount=abs(change_amount),
        #         change_type=change_type
        #     )

        # Шукаємо відповідний запис в StockHistory
        stock_history_record = StockHistory.get_or_none(
            (StockHistory.product == product) &
            (StockHistory.change_type == 'create')
        )

        # Якщо запис існує, оновлюємо його
        if stock_history_record:
            stock_history_record.timestamp = created_date if created_date else datetime.now()
            stock_history_record.change_amount = quantity
            stock_history_record.save()  # Зберігаємо зміни в записі

        # Якщо запису немає, створюємо новий
        else:
            StockHistory.create(
                product=product,
                change_amount=quantity,
                change_type='create',
                timestamp=created_date if created_date else datetime.now()
            )

        # Повертаємо оновлений продукт у вигляді JSON
        updated_product = model_to_dict(product, backrefs=True, exclude=[ProductCategory])
        return jsonify(updated_product), 200

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Видалити товар та всі пов'язані записи"""
    try:
        product = Product.get(Product.id == product_id)

        ProductCategory.delete().where(ProductCategory.product == product).execute()
        # Видалення всіх пов'язаних продажів
        SaleHistory.delete().where(SaleHistory.product == product).execute()

        # Видалення всіх пов'язаних покупок
        PurchaseHistory.delete().where(PurchaseHistory.product == product).execute()

        # Видалення всіх записів змін запасів
        StockHistory.delete().where(StockHistory.product == product).execute()

        # Видалення самого товару
        product.delete_instance()

        return jsonify({'message': 'Product and related records deleted successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Отримати історію змін запасів, покупок і продажів для товару"""
    try:
        product = Product.get(Product.id == product_id)

        # Отримання історії змін запасів
        stock_history = StockHistory.select().where(StockHistory.product == product)
        stock_history_list = [
            {
                **model_to_dict(record),
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S')  # Або інший бажаний формат
            }
            for record in stock_history
        ]

        # Отримання історії покупок
        purchase_history = PurchaseHistory.select().where(PurchaseHistory.product == product)
        purchase_history_list = [model_to_dict(purchase) for purchase in purchase_history]

        # Отримання історії продажів
        sale_history = SaleHistory.select().where(SaleHistory.product == product)
        sale_history_list = [
            {
                **model_to_dict(sale),
                'selling_price_per_item': float(sale.selling_price_per_item),  # Конвертація в число
                'selling_total_price': float(sale.selling_total_price)  # Конвертація в число
            }
            for sale in sale_history
        ]

        # Об'єднуємо всі списки в один об'єкт
        combined_history = {
            'stock_history': stock_history_list,
            'purchase_history': purchase_history_list,
            'sale_history': sale_history_list
        }

        return jsonify(combined_history), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>/purchase', methods=['POST'])
def purchase_product(product_id):
    """Обробити покупку товару і записати в історію"""
    data = request.get_json()

    # Перевірка, чи продукт існує
    try:
        product = Product.get(Product.id == product_id)
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    # Валідація даних
    try:
        # Валідація кількості
        quantity = data['quantity']
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400

        # Валідація ціни та інших полів
        purchase_price_per_item = Decimal(data['purchase_price_per_item'])  # Перетворення у Decimal
        purchase_total_price = Decimal(data['purchase_total_price'])  # Перетворення у Decimal
        supplier_id = data['supplier_id']
        purchase_date = data.get('purchase_date')  # Можна вказати значення за замовчуванням

        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        # Перевірка на від'ємні значення ціни
        if purchase_price_per_item <= 0 or purchase_total_price <= 0:
            return jsonify({'error': 'Price must be greater than 0'}), 400

        # Оновлення кількості товару в таблиці Product
        product.quantity += quantity
        product.purchase_total_price += purchase_total_price
        product.save()
        product.purchase_price_per_item = product.purchase_total_price / product.quantity
        product.save()
        # Створення нового запису в історії покупок
        PurchaseHistory.create(
            product=product,
            purchase_price_per_item=purchase_price_per_item,
            purchase_total_price=purchase_total_price,
            supplier=supplier,
            purchase_date=purchase_date,
            quantity_purchase=quantity
        )
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    # Повертаємо відповідь
    return jsonify({'message': 'Purchase recorded successfully'}), 201


@app.route('/api/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Записати продаж товару і додати в історію продажів"""
    try:
        # Перевірка, чи існує продукт
        product = Product.get(Product.id == product_id)
        data = request.get_json()

        # Валідація даних
        required_fields = ['customer', 'quantity', 'selling_price_per_item', 'selling_total_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        quantity_sold = data['quantity']
        if quantity_sold <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400

        selling_price_per_item = data['selling_price_per_item']
        selling_total_price = data['selling_total_price']
        if selling_price_per_item <= 0 or selling_total_price <= 0:
            return jsonify({'error': 'Price per item and total price must be greater than 0'}), 400

        # Перевірка, чи є достатня кількість товару на складі
        if product.quantity < quantity_sold:
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        # Оновлення кількості товару
        product.quantity -= quantity_sold
        product.selling_quantity = product.selling_quantity + quantity_sold
        product.selling_price_per_item = selling_price_per_item
        product.selling_total_price = product.selling_total_price + selling_total_price
        product.save()

        # Створення нового запису продажу в історії
        customer = Customer.get(Customer.id == data['customer'])
        SaleHistory.create(
            product=product,
            customer=customer,
            quantity_sold=quantity_sold,
            selling_price_per_item=selling_price_per_item,
            selling_total_price=selling_total_price,
            sale_date=data.get('sale_date', datetime.now())  # Якщо немає дати, використати поточну
        )

        return jsonify({'message': 'Sale recorded successfully'}), 201

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400


@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    """Отримати список всіх категорій"""
    categories = Category.select()  # Отримуємо всі категорії
    category_list = [model_to_dict(category) for category in categories]  # Перетворюємо на список словників
    return jsonify(category_list), 200  # Повертаємо JSON відповідь


@app.route('/api/categories', methods=['POST'])
def create_category():
    """Створити нову категорію"""
    data = request.get_json()
    try:
        category, created = Category.get_or_create(name=data['name'])
        if created:
            return jsonify({'message': 'Category created successfully', 'category': model_to_dict(category)}), 201
        else:
            return jsonify({'message': 'Category already exists', 'category': model_to_dict(category)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/product/<int:product_id>/categories', methods=['POST'])
def assign_categories_to_product(product_id):
    """Прив'язати категорії до товару"""
    data = request.get_json()
    try:
        product = Product.get(Product.id == product_id)
        category_ids = data['category_ids']  # список ID категорій

        # Додаємо категорії до товару
        for category_id in category_ids:
            category = Category.get(Category.id == category_id)
            ProductCategory.get_or_create(product=product, category=category)

        return jsonify({'message': 'Categories assigned successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404
    except Category.DoesNotExist:
        return jsonify({'error': 'One or more categories not found'}), 404


@app.route('/api/product/<int:product_id>/categories', methods=['GET'])
def get_product_categories(product_id):
    """Отримати категорії товару"""
    try:
        product = Product.get(Product.id == product_id)
        categories = [model_to_dict(category) for category in product.categories]
        return jsonify(categories), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/supplier', methods=['POST'])
def create_supplier():
    """Додати нового постачальника"""
    data = request.get_json()

    # Перевірка наявності обов'язкового поля
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    supplier, created = Supplier.get_or_create(name=data['name'], defaults={'contact_info': data.get('contact_info')})

    if created:
        return jsonify({'message': 'Supplier created successfully', 'supplier_id': supplier.id}), 201
    else:
        return jsonify({'error': 'Supplier already exists'}), 409


@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    """Отримати список усіх постачальників"""
    suppliers = Supplier.select()
    suppliers_list = [model_to_dict(supplier) for supplier in suppliers]

    return jsonify(suppliers_list), 200


def get_supplier_purchase_history(supplier_id):
    supplier = Supplier.get_by_id(supplier_id)

    # Отримання історії закупівель
    purchase_history = (PurchaseHistory
                        .select(PurchaseHistory, Product)
                        .join(Product)
                        .where(PurchaseHistory.supplier == supplier))

    products = set()  # Унікальний список продуктів

    for purchase in purchase_history:
        products.add(purchase.product)

    return {
        "supplier": supplier.name,
        "purchase_history": purchase_history,
        "products": list(products)
    }


@app.route('/api/supplier/<int:supplier_id>/purchase-history', methods=['GET'])
def get_supplier_purchase_history_api(supplier_id):
    supplier_data = get_supplier_purchase_history(supplier_id)  # Використовуємо раніше створену функцію
    return jsonify({
        "supplier": supplier_data['supplier'],
        "purchase_history": [{
            "product": purchase.product.name,
            "quantity_purchase": purchase.quantity_purchase,
            "purchase_date": purchase.purchase_date,
            "purchase_price_per_item": purchase.purchase_price_per_item,
            "purchase_total_price": purchase.purchase_total_price
        } for purchase in supplier_data['purchase_history']],
        "products": [{"id": product.id, "name": product.name} for product in supplier_data['products']]
    })


def get_supplier_products(supplier_id):
    supplier = Supplier.get_by_id(supplier_id)

    # Отримання продуктів, пов'язаних із постачальником
    products = Product.select().where(Product.supplier == supplier)

    return {
        "supplier": supplier.name,
        "products": products
    }


@app.route('/api/supplier/<int:supplier_id>/products', methods=['GET'])
def get_supplier_products_api(supplier_id):
    supplier_data = get_supplier_products(supplier_id)  # Використовуємо функцію для отримання продуктів
    return jsonify({
        "supplier": supplier_data['supplier'],
        "products": [{"id": product.id, "name": product.name} for product in supplier_data['products']]
    })


@app.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    required_fields = ['name', 'email']

    # Перевірка на обов'язкові поля
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    try:
        # Створення нового покупця
        customer = Customer.create(
            name=data['name'],
            contact_info=data.get('contact_info'),
            address=data.get('address'),
            email=data['email'],
            phone_number=data.get('phone_number')
        )
        return jsonify({'message': 'Customer created successfully', 'customer': model_to_dict(customer)}), 201
    except IntegrityError:
        return jsonify({'error': 'Customer with this email already exists'}), 400


@app.route('/api/customers', methods=['GET'])
def get_all_customers():
    customers = Customer.select()
    customer_list = [model_to_dict(customer) for customer in customers]
    return jsonify(customer_list), 200


@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    try:
        customer = Customer.get_by_id(customer_id)
        customer_data = model_to_dict(customer)

        # Отримуємо продажі, пов'язані з покупцем
        sales = SaleHistory.select().where(SaleHistory.customer == customer)
        customer_data['sales'] = [model_to_dict(sale) for sale in sales]

        return jsonify(customer_data), 200
    except Customer.DoesNotExist:
        return jsonify({'error': 'Customer not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)

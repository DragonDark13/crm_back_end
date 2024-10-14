from flask import Blueprint, jsonify, request
from peewee import DoesNotExist
from models import Category, Product, ProductCategory
from playhouse.shortcuts import model_to_dict

# Створюємо Blueprint для категорій
category_bp = Blueprint('categories', __name__)


@category_bp.route('/api/categories', methods=['GET'])
def get_all_categories():
    """Отримати список всіх категорій"""
    categories = Category.select()  # Отримуємо всі категорії
    category_list = [model_to_dict(category) for category in categories]  # Перетворюємо на список словників
    return jsonify(category_list), 200  # Повертаємо JSON відповідь


@category_bp.route('/api/categories', methods=['POST'])
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


@category_bp.route('/api/product/<int:product_id>/categories', methods=['POST'])
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


@category_bp.route('/api/product/<int:product_id>/categories', methods=['GET'])
def get_product_categories(product_id):
    """Отримати категорії товару"""
    try:
        product = Product.get(Product.id == product_id)
        categories = [model_to_dict(category) for category in product.categories]
        return jsonify(categories), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

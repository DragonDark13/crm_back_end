from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import Category, Product, product_categories_table

# Create a Blueprint for categories

category_bp = Blueprint('categories', __name__)


@category_bp.route('/api/categories', methods=['GET'])
def get_all_categories():
    """Retrieve all categories."""
    from postgreSQLConnect import db_session

    with db_session() as session:
        categories = session.query(Category).all()
        category_list = [{'id': cat.id, 'name': cat.name} for cat in categories]
    return jsonify(category_list), 200


@category_bp.route('/api/categories', methods=['POST'])
def create_category():
    """Create a new category."""
    from postgreSQLConnect import db_session

    data = request.get_json()
    try:
        with db_session() as session:
            category = Category(name=data['name'])
            session.add(category)
            session.commit()
            return jsonify({'message': 'Category created successfully',
                            'category': {'id': category.id, 'name': category.name}}), 201
    except IntegrityError:
        return jsonify({'message': 'Category already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@category_bp.route('/api/product/<int:product_id>/categories', methods=['POST'])
def assign_categories_to_product(product_id):
    """Assign categories to a product."""
    from postgreSQLConnect import db_session

    data = request.get_json()
    try:
        with db_session() as session:
            product = session.query(Product).get(product_id)
            if not product:
                return jsonify({'error': 'Product not found'}), 404

            category_ids = data.get('category_ids', [])
            for category_id in category_ids:
                category = session.query(Category).get(category_id)
                if not category:
                    return jsonify({'error': f'Category with ID {category_id} not found'}), 404
                # Avoid duplicate entries
                if category not in product.categories:
                    product.categories.append(category)

            session.commit()
            return jsonify({'message': 'Categories assigned successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@category_bp.route('/api/product/<int:product_id>/categories', methods=['GET'])
def get_product_categories(product_id):
    """Retrieve categories of a product."""
    try:
        with db_session() as session:
            product = session.query(Product).get(product_id)
            if not product:
                return jsonify({'error': 'Product not found'}), 404

            categories = [{'id': cat.id, 'name': cat.name} for cat in product.categories]
            return jsonify(categories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

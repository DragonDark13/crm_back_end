from database import db_session
from models import PackagingMaterial, PackagingStockHistory, PackagingPurchaseHistory


def delete_all_packaging_materials():
    try:
        # Видалення всіх упаковочних матеріалів разом з пов'язаними даними
        db_session.query(PackagingMaterial).delete(synchronize_session=False)
        db_session.query(PackagingStockHistory).delete(synchronize_session=False)
        db_session.query(PackagingPurchaseHistory).delete(synchronize_session=False)

        # Підтвердження змін
        db_session.commit()
        print("Усі упаковочні матеріали та пов'язані дані були успішно видалені.")
    except Exception as e:
        # Якщо сталася помилка, скасувати зміни
        db_session.rollback()
        print(f"Сталася помилка: {e}")
    finally:
        # Закрити сесію
        db_session.close()


# Виклик функції
delete_all_packaging_materials()

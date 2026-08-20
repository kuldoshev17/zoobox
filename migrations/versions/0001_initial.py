"""Create the initial ZooPet schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

order_status = postgresql.ENUM("NEW", "CONFIRMED", "PACKING", "DELIVERING", "DELIVERED", "CANCELLED", name="orderstatus", create_type=False)
payment_method = postgresql.ENUM("CASH", "CLICK", "PAYME", name="paymentmethod", create_type=False)
payment_status = postgresql.ENUM("PENDING", "PAID", "FAILED", name="paymentstatus", create_type=False)
subscription_tier = postgresql.ENUM("EKO", "BASIC", "PLUS", "PREMIUM", name="subscriptiontier", create_type=False)
pet_species = postgresql.ENUM("CAT", "DOG", name="petspecies", create_type=False)
food_type = postgresql.ENUM("DRY", "WET", name="foodtype", create_type=False)
age_group = postgresql.ENUM("ADULT", "YOUNG", "SENIOR", name="agegroup", create_type=False)
sterilization = postgresql.ENUM("STERILIZED", "NOT_STERILIZED", name="sterilization", create_type=False)
subscription_status = postgresql.ENUM("ACTIVE", "CANCELLED", name="subscriptionstatus", create_type=False)

enum_types = (
    (order_status, "orderstatus"), (payment_method, "paymentmethod"),
    (payment_status, "paymentstatus"), (subscription_tier, "subscriptiontier"),
    (pet_species, "petspecies"), (food_type, "foodtype"),
    (age_group, "agegroup"), (sterilization, "sterilization"),
    (subscription_status, "subscriptionstatus"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type, enum_name in enum_types:
        postgresql.ENUM(*enum_type.enums, name=enum_name).create(bind, checkfirst=True)

    op.create_table("categories", sa.Column("id", sa.Integer(), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("icon", sa.String(10)), sa.Column("sort_order", sa.Integer()), sa.Column("is_active", sa.Boolean()), sa.Column("species", pet_species), sa.PrimaryKeyConstraint("id"))
    op.create_table("customers", sa.Column("id", sa.Integer(), nullable=False), sa.Column("telegram_id", sa.String(50), nullable=False), sa.Column("full_name", sa.String(200), nullable=False), sa.Column("phone", sa.String(30), nullable=False), sa.Column("password_hash", sa.String(200), nullable=False), sa.Column("address", sa.String(400)), sa.Column("created_at", sa.DateTime()), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("phone"), sa.UniqueConstraint("telegram_id"))
    op.create_table("admins", sa.Column("id", sa.Integer(), nullable=False), sa.Column("username", sa.String(80), nullable=False), sa.Column("password_hash", sa.String(200), nullable=False), sa.Column("telegram_id", sa.String(50)), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("username"))
    op.create_table("subscription_plans", sa.Column("id", sa.Integer(), nullable=False), sa.Column("tier", subscription_tier, nullable=False), sa.Column("species", pet_species, nullable=False), sa.Column("name", sa.String(80), nullable=False), sa.Column("price", sa.Float(), nullable=False), sa.Column("description", sa.Text()), sa.Column("is_active", sa.Boolean()), sa.Column("sort_order", sa.Integer()), sa.PrimaryKeyConstraint("id"))
    op.create_table("products", sa.Column("id", sa.Integer(), nullable=False), sa.Column("category_id", sa.Integer(), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("price", sa.Float(), nullable=False), sa.Column("old_price", sa.Float()), sa.Column("image_url", sa.String(200)), sa.Column("stock", sa.Integer()), sa.Column("unit", sa.String(30)), sa.Column("is_active", sa.Boolean()), sa.Column("created_at", sa.DateTime()), sa.Column("species", pet_species), sa.Column("brand", sa.String(100)), sa.Column("food_type", food_type), sa.Column("age_group", age_group), sa.Column("composition", sa.String(200)), sa.Column("sterilization", sterilization), sa.ForeignKeyConstraint(["category_id"], ["categories.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("product_variants", sa.Column("id", sa.Integer(), nullable=False), sa.Column("product_id", sa.Integer(), nullable=False), sa.Column("label", sa.String(50), nullable=False), sa.Column("price", sa.Float(), nullable=False), sa.Column("stock", sa.Integer()), sa.ForeignKeyConstraint(["product_id"], ["products.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("orders", sa.Column("id", sa.Integer(), nullable=False), sa.Column("customer_id", sa.Integer(), nullable=False), sa.Column("status", order_status), sa.Column("payment_method", payment_method), sa.Column("payment_status", payment_status), sa.Column("delivery_address", sa.String(400)), sa.Column("delivery_phone", sa.String(30)), sa.Column("comment", sa.String(400)), sa.Column("total_amount", sa.Float()), sa.Column("delivery_fee", sa.Float()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("order_items", sa.Column("id", sa.Integer(), nullable=False), sa.Column("order_id", sa.Integer(), nullable=False), sa.Column("product_id", sa.Integer(), nullable=False), sa.Column("product_name", sa.String(200)), sa.Column("unit_price", sa.Float()), sa.Column("quantity", sa.Integer()), sa.ForeignKeyConstraint(["order_id"], ["orders.id"]), sa.ForeignKeyConstraint(["product_id"], ["products.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("subscriptions", sa.Column("id", sa.Integer(), nullable=False), sa.Column("customer_id", sa.Integer(), nullable=False), sa.Column("plan_id", sa.Integer(), nullable=False), sa.Column("status", subscription_status), sa.Column("created_at", sa.DateTime()), sa.Column("cancelled_at", sa.DateTime()), sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]), sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=False)
    op.create_index("ix_customers_telegram_id", "customers", ["telegram_id"], unique=False)
    op.create_index("uq_active_subscription_customer", "subscriptions", ["customer_id"], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))


def downgrade() -> None:
    for table in ("subscriptions", "order_items", "orders", "product_variants", "products", "subscription_plans", "admins", "customers", "categories"):
        op.drop_table(table)
    bind = op.get_bind()
    for enum_type, enum_name in reversed(enum_types):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)

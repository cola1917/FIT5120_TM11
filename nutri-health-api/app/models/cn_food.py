"""
CN2026 remote food catalog models.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


class CnCtgnme(Base):
    __tablename__ = "cn_ctgnme"

    food_category_code = Column(Integer, primary_key=True)
    category_description = Column(String(255), nullable=False)


class CnGpcnme(Base):
    __tablename__ = "cn_gpcnme"

    gpc_code = Column(String(32), primary_key=True)
    gpc_description = Column(String(255), nullable=False)


class CnNutdes(Base):
    __tablename__ = "cn_nutdes"

    nutrient_code = Column(Integer, primary_key=True)
    nutrient_description = Column(String(255), nullable=False)
    nutrient_unit = Column(String(32), nullable=True)


class CnFdes(Base):
    __tablename__ = "cn_fdes"

    cn_code = Column(Integer, primary_key=True)
    gtin = Column(String(32), nullable=True, unique=True)
    food_category_code = Column(Integer, ForeignKey("cn_ctgnme.food_category_code"), nullable=True)
    gpc_product_code = Column(String(32), ForeignKey("cn_gpcnme.gpc_code"), nullable=True)
    descriptor = Column(Text, nullable=False)
    brand_name = Column(String(255), nullable=True)
    brand_owner_name = Column(String(255), nullable=True)
    form_of_food = Column(String(64), nullable=True)
    health_grade = Column(String(1), nullable=True)
    hcl_compliant = Column(Boolean, nullable=True)
    is_halal_auto = Column(Boolean, nullable=True)
    discontinued_date = Column(Date, nullable=True)


class CnNutval(Base):
    __tablename__ = "cn_nutval"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cn_code = Column(Integer, ForeignKey("cn_fdes.cn_code"), nullable=False)
    nutrient_code = Column(Integer, ForeignKey("cn_nutdes.nutrient_code"), nullable=False)
    nutrient_value = Column(Float, nullable=True)
    source_code = Column(Integer, nullable=True)
    value_type_code = Column(Integer, nullable=True)
    per_unit = Column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "cn_code",
            "nutrient_code",
            "source_code",
            "value_type_code",
            "per_unit",
            name="uq_cn_nutval_source",
        ),
    )


class CnWght(Base):
    __tablename__ = "cn_wght"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cn_code = Column(Integer, ForeignKey("cn_fdes.cn_code"), nullable=False)
    sequence_num = Column(Integer, nullable=False)
    measure_description = Column(String(255), nullable=True)
    amount = Column(Float, nullable=True)
    unit_amount = Column(Float, nullable=True)
    type_of_unit = Column(String(16), nullable=True)
    source_code = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "cn_code",
            "sequence_num",
            "measure_description",
            name="uq_cn_wght_measure",
        ),
    )


class CnFoodTag(Base):
    __tablename__ = "cn_food_tags"

    tag_id = Column(Integer, primary_key=True)
    cn_code = Column(Integer, ForeignKey("cn_fdes.cn_code"), nullable=False)
    tag_type = Column(String(32), nullable=False)
    tag_value = Column(String(128), nullable=False)


class RemoteAlternative(Base):
    __tablename__ = "remote_alternative"

    alt_id = Column(Integer, primary_key=True)
    original_cn_code = Column(Integer, ForeignKey("cn_fdes.cn_code"), nullable=False)
    suggested_cn_code = Column(Integer, ForeignKey("cn_fdes.cn_code"), nullable=False)
    swap_reason_en = Column(Text, nullable=False)
    swap_score = Column(Integer, nullable=False)

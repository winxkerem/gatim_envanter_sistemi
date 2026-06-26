from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError
from app.models import db, Category, InventoryItem

class InventoryItemForm(FlaskForm):
    """Form to add or edit an inventory item."""
    name = StringField("Malzeme Adı", validators=[DataRequired(), Length(max=100)])
    sku = StringField("Stok Kodu (SKU)", validators=[DataRequired(), Length(max=50)])
    quantity = IntegerField("Stok Miktarı", validators=[DataRequired(), NumberRange(min=0, message="Stok miktarı negatif olamaz.")])
    critical_level = IntegerField("Kritik Seviye (Minimum Uyarı Sınırı)", validators=[DataRequired(), NumberRange(min=0, message="Kritik seviye negatif olamaz.")])
    category_id = SelectField("Kategori", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Kaydet")

    def __init__(self, original_sku=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_sku = original_sku

    def validate_sku(self, sku):
        """Ensure SKU uniqueness when changing it."""
        if sku.data != self.original_sku:
            item = db.session.query(InventoryItem).filter_by(sku=sku.data).first()
            if item:
                raise ValidationError("Bu SKU koduna sahip başka bir malzeme zaten mevcut.")

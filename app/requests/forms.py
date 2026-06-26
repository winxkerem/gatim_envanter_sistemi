from flask_wtf import FlaskForm
from wtforms import IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class RequestForm(FlaskForm):
    """Form to request an inventory item."""
    quantity = IntegerField(
        "Talep Adedi", 
        validators=[DataRequired(message="Lütfen miktar giriniz."), NumberRange(min=1, message="Talep adedi en az 1 olmalıdır.")]
    )
    submit = SubmitField("Talep Gönder")

class RejectForm(FlaskForm):
    """Form for managers to specify rejection remarks."""
    remarks = TextAreaField(
        "Red Gerekçesi", 
        validators=[DataRequired(message="Lütfen bir red gerekçesi belirtiniz.")]
    )
    submit = SubmitField("Talebi Reddet")

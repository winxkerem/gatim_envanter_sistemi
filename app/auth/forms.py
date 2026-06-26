from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import db, User, Department

class LoginForm(FlaskForm):
    """User login form."""
    username = StringField("Kullanıcı Adı", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Şifre", validators=[DataRequired()])
    submit = SubmitField("Giriş Yap")

class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField("Kullanıcı Adı", validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField("E-posta Adresi", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Şifre", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Şifre Tekrar", 
        validators=[DataRequired(), EqualTo("password", message="Şifreler eşleşmelidir.")]
    )
    department_id = SelectField("Departman", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Kayıt Ol")

    def validate_username(self, username):
        """Ensure username is unique."""
        user = db.session.query(User).filter_by(username=username.data).first()
        if user:
            raise ValidationError("Bu kullanıcı adı zaten alınmış.")

    def validate_email(self, email):
        """Ensure email is unique."""
        user = db.session.query(User).filter_by(email=email.data).first()
        if user:
            raise ValidationError("Bu e-posta adresi zaten kayıtlı.")

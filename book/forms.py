# book/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    """自定义用户注册表单"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '请输入邮箱'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入用户名'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加样式到所有字段
        for field_name, field in self.fields.items():
            if field_name not in ['username', 'email']:
                field.widget.attrs.update({'class': 'form-control', 'placeholder': field.label})


class CustomAuthenticationForm(AuthenticationForm):
    """自定义用户登录表单"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '用户名或邮箱'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '密码'
        })
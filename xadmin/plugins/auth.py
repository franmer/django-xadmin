# coding=utf-8
from django import forms
from django.contrib.auth.forms import (UserCreationForm, UserChangeForm,
                                       AdminPasswordChangeForm, PasswordChangeForm)
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.forms import ModelMultipleChoiceField
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper
from xadmin.sites import site
from xadmin.util import unquote
from users.models import User
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, ModelAdminView, CommAdminView, csrf_protect_m

#debugger
"""import pdb
pdb.set_trace()"""

ACTION_NAME = {
    'add': _('Can add %s'),
    'change': _('Can change %s'),
    'edit': _('Can edit %s'),
    'delete': _('Can delete %s'),
    'view': _('Can view %s'),
}

class MyUserCreationForm(UserCreationForm):
    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    class Meta(UserCreationForm.Meta):
        model = User

def get_permission_name(p):
    action = p.codename.split('_')[0]
    if action in ACTION_NAME:
        return ACTION_NAME[action] % str(p.content_type)
    else:
        return p.name


class PermissionModelMultipleChoiceField(ModelMultipleChoiceField):

    def label_from_instance(self, p):
        return get_permission_name(p)


class GroupAdmin(object):
    search_fields = ('name',)
    ordering = ('name',)
    style_fields = {'permissions': 'm2m_transfer'}
    model_icon = 'fa fa-group'

    def get_field_attrs(self, db_field, **kwargs):
        attrs = super(GroupAdmin, self).get_field_attrs(db_field, **kwargs)
        if db_field.name == 'permissions':
            attrs['form_class'] = PermissionModelMultipleChoiceField
        return attrs


class UserAdmin(object):
    change_user_password_template = None
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    style_fields = {'user_permissions': 'm2m_transfer'}
    model_icon = 'fa fa-user'
    relfield_style = 'fk-ajax'

    def get_field_attrs(self, db_field, **kwargs):
        attrs = super(UserAdmin, self).get_field_attrs(db_field, **kwargs)
        if db_field.name == 'user_permissions':
            attrs['form_class'] = PermissionModelMultipleChoiceField
        return attrs

    def get_model_form(self, **kwargs):
        if self.org_obj is None:
            self.form = MyUserCreationForm #sgiso demor change
        else:
            self.form = UserChangeForm
        return super(UserAdmin, self).get_model_form(**kwargs)

    def get_form_layout(self):
        if self.org_obj:
            self.form_layout = (
                Main(
                    Fieldset('',
                             'username', 'password',
                             css_class='unsort no_title'
                             ),
                    Fieldset(_('Personal info'),
                             Row('first_name', 'last_name'),
                             'email'
                             ),
                    Fieldset(_('Permissions'),
                             'groups', 'user_permissions'
                             ),
                    Fieldset(_('Important dates'),
                             'last_login', 'date_joined'
                             ),
                ),
                Side(
                    Fieldset(_('Status'),
                             'is_active', 'is_staff', 'is_superuser',
                             ),
                )
            )
        return super(UserAdmin, self).get_form_layout()


class PermissionAdmin(object):

    def show_name(self, p):
        return get_permission_name(p)
    show_name.short_description = _('Permission Name')
    show_name.is_column = True

    model_icon = 'fa fa-lock'
    list_display = ('show_name', )

site.register(Group, GroupAdmin)
site.register(User, UserAdmin)
site.register(Permission, PermissionAdmin)


class UserFieldPlugin(BaseAdminPlugin):

    user_fields = []

    def get_field_attrs(self, __, db_field, **kwargs):
        if not self.user.is_superuser:
            if self.user_fields and db_field.name in self.user_fields:
                return {'widget': forms.HiddenInput}
        return __()

    def get_form_datas(self, datas):
        if not self.user.is_superuser:
            if self.user_fields and 'data' in datas:
                if hasattr(datas['data'],'_mutable') and not datas['data']._mutable:
                    datas['data'] = datas['data'].copy()
                for f in self.user_fields:
                    datas['data'][f] = self.user.pk
        return datas

site.register_plugin(UserFieldPlugin, ModelFormAdminView)


class ProyectoFieldPlugin(BaseAdminPlugin):

    proyecto_fields = []

    def get_field_attrs(self, __, db_field, **kwargs):
        if not self.user.is_superuser:
            #if not self.user.es_empleado(): #esto no está del todo bien, pero bueno. es para evitaar
            if self.proyecto_fields and db_field.name in self.proyecto_fields:
                return {'widget': forms.HiddenInput}
        return __()

    def get_form_datas(self, datas):
        if not self.user.is_superuser:
            #if not self.user.es_empleado():   #esto no está del todo bien, pero bueno.
            if self.proyecto_fields and 'data' in datas:
                if hasattr(datas['data'],'_mutable') and not datas['data']._mutable:
                    datas['data'] = datas['data'].copy()
                for f in self.proyecto_fields:
                    datas['data'][f] = self.user.get_proyecto().pk
                    #http://stackoverflow.com/questions/929029/how-do-i-access-the-child-classes-of-an-object-in-django-without-knowing-the-nam
                    #https://github.com/chrisglass/django_polymorphic
        return datas

site.register_plugin(ProyectoFieldPlugin, ModelFormAdminView)


class EmpresaFieldPlugin(BaseAdminPlugin):

    empresa_fields = []

    def get_field_attrs(self, __, db_field, **kwargs):
        if not self.user.is_superuser:
            if self.empresa_fields and db_field.name in self.empresa_fields:
                return {'widget': forms.HiddenInput}
        return __()

    def get_form_datas(self, datas):
        if not self.user.is_superuser:
            if self.empresa_fields and 'data' in datas:
                if hasattr(datas['data'],'_mutable') and not datas['data']._mutable:
                    datas['data'] = datas['data'].copy()
                for f in self.empresa_fields:
                    datas['data'][f] = self.user.get_proyecto().empresa_erp.pk  #Mejorar este acceso desde la clase padre si se puede.
        return datas

site.register_plugin(EmpresaFieldPlugin, ModelFormAdminView)

"""
class SeguridadPorProyectoPlugin(BaseAdminPlugin):

    seguridad_por_proyecto = False

    def aplicar_seguridad_por_proyecto(self):
        #eSgISO hack for proyecto in foreignkey fields
        if not self.user.is_superuser: #and self.request.user.get_proyecto(): (hacrea algo aqui para bool)            
            for key in self.form_obj.fields:            
                try: #try porque igual algunos fields no tiene queryset porque no son foreigkey. Mejorarlo.
                    #self.form_obj[key].queryset = self.form_obj[key].queryset.filter(proyecto = self.request.user.get_proyecto())
                    self.form_obj.fields[key].queryset = self.form_obj.fields[key].queryset.filter(proyecto = self.request.user.get_proyecto())
                    #.values()[idx]
                except:
                    pass
        #self.form_obj.fields['clienteproveedor'].queryset = self.form_obj.fields['clienteproveedor'].queryset.filter(proyecto=self.request.user.cliente.proyecto)
        #Orig that worked: self.form_obj.fields['clienteproveedor'].queryset = self.form_obj.fields['clienteproveedor'].queryset.filter(proyecto=self.request.user.cliente.proyecto)
        #eSgISO hack for proyecto in foreignkey fields

    def setup_forms(self):
        super de setuf forms...
        if self.seguridad_por_proyecto
            self.aplicar_seguridad_por_proyecto()

site.register_plugin(SeguridadPorProyectoPlugin, ModelFormAdminView)
"""



"""class ModelPermissionPlugin(BaseAdminPlugin):

    user_can_access_owned_objects_only = False
    user_owned_objects_field = 'user'

    def queryset(self, qs):
        if self.user_can_access_owned_objects_only and \
                not self.user.is_superuser:
            filters = {self.user_owned_objects_field: self.user}
            qs = qs.filter(**filters)
        return qs

site.register_plugin(ModelPermissionPlugin, ModelAdminView)"""


#Intentar corregir esto, y que sea como plugin, ahora está hackeado en list.py eSgISO security directamente el queryset method
"""class ProyectoEmpresaUsuarioModelPermissionPlugin(BaseAdminPlugin):

    user_can_access_proyecto_empresa_user_objects_only = False
    #user_owned_objects_field = 'user'

    def queryset(self, qs):
        if self.user_can_access_proyecto_empresa_user_objects_only and not self.user.is_superuser:
            #filters = {self.user_owned_objects_field: self.user}
            #filters = {'user': self.user, 'empresa': self.user.cliente.proyecto.empresa_erp, 'proyecto': self.user.cliente.proyecto}
            filters = {}
            filters['user'] = self.user
            filters['empresa'] = self.user.cliente.proyecto.empresa_erp
            filters['proyecto'] = self.user.cliente.proyecto
            filters['user_id'] = self.user
            filters['empresa_id'] = self.user.cliente.proyecto.empresa_erp
            filters['proyecto_id'] = self.user.cliente.proyecto
            filters['user_pk'] = self.user
            filters['empresa_pk'] = self.user.cliente.proyecto.empresa_erp
            filters['proyecto_pk'] = self.user.cliente.proyecto
            qs = 0#qs.filter(**filters)
        return qs

site.register_plugin(ProyectoEmpresaUsuarioModelPermissionPlugin, ModelAdminView)
"""

class AccountMenuPlugin(BaseAdminPlugin):

    def block_top_account_menu(self, context, nodes):
        return '<li><a href="%s"><i class="fa fa-key"></i> %s</a></li>' % (self.get_admin_url('account_password'), _('Change Password'))

site.register_plugin(AccountMenuPlugin, CommAdminView)


class ChangePasswordView(ModelAdminView):
    model = User
    change_password_form = AdminPasswordChangeForm
    change_user_password_template = None

    @csrf_protect_m
    def get(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        self.obj = self.get_object(unquote(object_id))
        self.form = self.change_password_form(self.obj)

        return self.get_response()

    def get_media(self):
        media = super(ChangePasswordView, self).get_media()
        media = media + self.vendor('xadmin.form.css', 'xadmin.page.form.js') + self.form.media
        return media

    def get_context(self):
        context = super(ChangePasswordView, self).get_context()
        helper = FormHelper()
        helper.form_tag = False
        self.form.helper = helper
        context.update({
            'title': _('Change password: %s') % escape(unicode(self.obj)),
            'form': self.form,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_view_permission': True,
            'original': self.obj,
        })
        return context

    def get_response(self):
        return TemplateResponse(self.request, [
            self.change_user_password_template or
            'xadmin/auth/user/change_password.html'
        ], self.get_context(), current_app=self.admin_site.name)

    @method_decorator(sensitive_post_parameters())
    @csrf_protect_m
    def post(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        self.obj = self.get_object(unquote(object_id))
        self.form = self.change_password_form(self.obj, request.POST)

        if self.form.is_valid():
            self.form.save()
            self.message_user(_('Password changed successfully.'), 'success')
            return HttpResponseRedirect(self.model_admin_url('change', self.obj.pk))
        else:
            return self.get_response()


class ChangeAccountPasswordView(ChangePasswordView):
    change_password_form = PasswordChangeForm

    @csrf_protect_m
    def get(self, request):
        self.obj = self.user
        self.form = self.change_password_form(self.obj)

        return self.get_response()

    def get_context(self):
        context = super(ChangeAccountPasswordView, self).get_context()
        context.update({
            'title': _('Change password'),
            'account_view': True,
        })
        return context

    @method_decorator(sensitive_post_parameters())
    @csrf_protect_m
    def post(self, request):
        self.obj = self.user
        self.form = self.change_password_form(self.obj, request.POST)

        if self.form.is_valid():
            self.form.save()
            self.message_user(_('Password changed successfully.'), 'success')
            return HttpResponseRedirect(self.get_admin_url('index'))
        else:
            return self.get_response()

site.register_view(r'^auth/user/(.+)/update/password/$',
                   ChangePasswordView, name='user_change_password')
site.register_view(r'^account/password/$', ChangeAccountPasswordView,
                   name='account_password')

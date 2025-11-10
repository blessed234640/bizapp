from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Project, Task, TaskLog, RoleUpgradeRequest, ProjectMember

# Админка для пользователей с 4 ролями
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('email', 'first_name', 'last_name')}),
        ('Права доступа', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser'),
            'description': 'Роли: гость (только просмотр), пользователь (создание проектов), менеджер (управление проектами), администратор (полный доступ)'
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_active'),
        }),
    )
    readonly_fields = ['date_joined']

# Админка для участников проектов
class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']

# Админка для задач
class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ['title', 'assigned_to', 'status', 'priority']
    readonly_fields = ['created_at']
    show_change_link = True

# Админка для проектов
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'created_at', 'get_member_count', 'get_task_count']
    list_filter = ['created_at', 'owner']
    search_fields = ['title', 'description', 'owner__username']
    inlines = [ProjectMemberInline, TaskInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'owner')
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    
    def get_member_count(self, obj):
        # ИСПРАВЛЕНО: используем related_name 'members' вместо 'projectmember_set'
        return obj.members.count()
    get_member_count.short_description = 'Количество Участников'
    
    def get_task_count(self, obj):
        return obj.task_set.count()
    get_task_count.short_description = 'Задач'

# Админка для задач
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assigned_to', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at', 'project']
    search_fields = ['title', 'description', 'project__title', 'assigned_to__username']
    list_editable = ['status', 'priority']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'project', 'assigned_to')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority', 'metadata')
        }),
        ('Системные поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

# Админка для участников проектов
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'role', 'joined_at']
    list_filter = ['role', 'joined_at', 'project']
    search_fields = ['user__username', 'project__title']
    list_editable = ['role']

# Админка для логов задач
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['task__title', 'user__username']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False

# Админка для запросов на повышение роли
class RoleUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_user_role', 'requested_role', 'status', 'created_at']
    list_filter = ['status', 'requested_role', 'current_user_role']
    list_editable = ['status']
    search_fields = ['user__username', 'reason']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'current_user_role', 'requested_role', 'status', 'reason')
        }),
        ('Рассмотрение', {
            'fields': ('reviewed_by', 'reviewed_at'),
            'classes': ('collapse',)
        }),
        ('Дата создания', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

# Регистрация всех моделей
admin.site.register(User, CustomUserAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(ProjectMember, ProjectMemberAdmin)
admin.site.register(TaskLog, TaskLogAdmin)
admin.site.register(RoleUpgradeRequest, RoleUpgradeRequestAdmin)

# Убираем стандартные группы и разрешения если не нужны
from django.contrib.auth.models import Group, Permission
admin.site.unregister(Group)
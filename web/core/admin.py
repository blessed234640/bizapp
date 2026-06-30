from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Project, Task, TaskLog, RoleUpgradeRequest, ProjectMember, Department

# Админка для департаментов
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

# Админка для пользователей
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'department', 'is_active', 'date_joined']
    list_filter = ['role', 'department', 'is_active']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('email', 'first_name', 'last_name', 'department')}),
        ('Права доступа', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser'),
            'description': 'Роли: intern (просмотр), user (создание), manager (управление), admin (полный доступ).'
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ['date_joined']

# Админка для участников проектов
class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    fields = ['user', 'joined_at']
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
    list_display = ['title', 'department', 'owner', 'created_at']
    list_filter = ['department', 'owner', 'created_at']
    search_fields = ['title', 'description']
    inlines = [ProjectMemberInline, TaskInline]
    readonly_fields = ['created_at']

# Админка для задач
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assigned_to', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title', 'description']
    list_editable = ['status', 'priority']
    readonly_fields = ['created_at', 'updated_at']

# Админка для участников проектов
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'joined_at']
    list_filter = ['project', 'joined_at']
    search_fields = ['user__username', 'project__title']

# Админка для логов задач
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'timestamp']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False

# Админка для запросов на повышение роли
class RoleUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_user_role', 'requested_role', 'status', 'created_at']
    list_filter = ['status', 'requested_role']
    list_editable = ['status']
    readonly_fields = ['created_at']

# Регистрация моделей
admin.site.register(Department, DepartmentAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(ProjectMember, ProjectMemberAdmin)
admin.site.register(TaskLog, TaskLogAdmin)
admin.site.register(RoleUpgradeRequest, RoleUpgradeRequestAdmin)
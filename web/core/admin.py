from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Project, Task, TaskLog, RoleUpgradeRequest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password_hash')}),
        ('Personal info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password_hash', 'role', 'is_staff', 'is_superuser'),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Менеджеры видят только пользователей с ролями guest и user
        if request.user.role == 'manager' and not request.user.is_superuser:
            return qs.filter(role__in=['guest', 'user'])
        return qs
    
    def has_change_permission(self, request, obj=None):
        if obj and request.user.role == 'manager' and not request.user.is_superuser:
            # Менеджеры могут редактировать только обычных пользователей
            return obj.role in ['guest', 'user']
        return super().has_change_permission(request, obj)

@admin.register(RoleUpgradeRequest)
class RoleUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_user_role', 'requested_role', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status', 'requested_role', 'created_at')
    readonly_fields = ('created_at',)  # УБРАЛ current_role отсюда
    search_fields = ('user__username', 'user__email')
    actions = ['approve_requests', 'reject_requests']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, 'role') and request.user.role == 'manager' and not request.user.is_superuser:
            return qs.filter(requested_role__in=['user', 'manager'])
        return qs
    
    def has_change_permission(self, request, obj=None):
        if obj and hasattr(request.user, 'role') and request.user.role in ['admin', 'manager']:
            return True
        return False
    
    def approve_requests(self, request, queryset):
        for upgrade_request in queryset:
            if upgrade_request.status == 'pending':
                user = upgrade_request.user
                user.role = upgrade_request.requested_role
                user.save()
                
                upgrade_request.status = 'approved'
                upgrade_request.reviewed_by = request.user
                upgrade_request.reviewed_at = timezone.now()
                upgrade_request.save()
        
        self.message_user(request, "Выбранные заявки одобрены")
    approve_requests.short_description = "Одобрить выбранные заявки"
    
    def reject_requests(self, request, queryset):
        queryset.update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, "Выбранные заявки отклонены")
    reject_requests.short_description = "Отклонить выбранные заявки"

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Менеджеры и пользователи видят только свои проекты
        if request.user.role == 'user' and not request.user.is_superuser:
            return qs.filter(owner=request.user)
        elif request.user.role == 'manager' and not request.user.is_superuser:
            # Менеджеры видят все проекты
            return qs
        return qs

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description')

@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'user', 'timestamp')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('timestamp',)
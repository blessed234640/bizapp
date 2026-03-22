import json
from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from .models import Project, Task
from django.db.models import Count

from django.contrib.auth.decorators import login_required

def dashboard(request):
    """Главный дашборд (теперь на JWT)"""
    return render(request, 'dashboard.html')

def login_view(request):
    """Страница входа"""
    return render(request, 'login.html')

def logout_view(request):
    """Страница выхода (редирект на логин)"""
    from django.shortcuts import redirect
    return redirect('/login/')

def api_projects(request):
    """Список проектов для дашборда с учетом ролей"""
    user = request.user
    if not user.is_authenticated:
        return JsonResponse([], safe=False)

    if user.role in ['admin', 'manager']:
        projects = Project.objects.select_related('department', 'owner').all().order_by('-created_at')
    elif user.role == 'user':
        from django.db.models import Q
        projects = Project.objects.select_related('department', 'owner').filter(
            Q(department=user.department) | Q(owner=user) | Q(members__user=user)
        ).distinct().order_by('-created_at')
    else:
        return JsonResponse([], safe=False)

    data = [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'department_name': p.department.name if p.department else None,
        'owner_name': p.owner.username if p.owner else "Система",
        'created_at': p.created_at.isoformat()
    } for p in projects]
    
    return JsonResponse(data, safe=False)

def api_tasks(request):
    """Список задач для дашборда с учетом ролей"""
    user = request.user
    if not user.is_authenticated:
        return JsonResponse([], safe=False)

    if user.role in ['admin', 'manager']:
        tasks = Task.objects.select_related('project', 'assigned_to', 'project__department').all().order_by('-created_at')
    elif user.role == 'user':
        from django.db.models import Q
        tasks = Task.objects.select_related('project', 'assigned_to', 'project__department').filter(
            Q(assigned_to=user) | Q(project__department=user.department) | Q(project__members__user=user)
        ).distinct().order_by('-created_at')
    else:
        return JsonResponse([], safe=False)

    data = [{
        'id': t.id,
        'project_id': t.project.id,
        'project_title': t.project.title,
        'title': t.title,
        'description': t.description,
        'status': t.status,
        'priority': t.priority,
        'assigned_to_name': t.assigned_to.username if t.assigned_to else None,
        'created_at': t.created_at.isoformat()
    } for t in tasks]
    
    return JsonResponse(data, safe=False)

def api_stats(request):
    """Статистика задач с кэшированием (общий ключ с FastAPI)"""
    cache_key = 'reports:tasks_stats'
    stats_json = cache.get(cache_key)
    
    if stats_json:
        # FastAPI сохраняет как JSON строку через redis.setex
        if isinstance(stats_json, str):
            try:
                stats = json.loads(stats_json)
                return JsonResponse(stats, safe=False)
            except:
                pass
        else:
            return JsonResponse(stats_json, safe=False)
    
    # Если в кэше нет, считаем сами
    query_set = Task.objects.values('status').annotate(count=Count('id'))
    stats = list(query_set)
    # Кэшируем на 30 минут (совпадает с FastAPI)
    cache.set(cache_key, json.dumps(stats), 1800)
    return JsonResponse(stats, safe=False)
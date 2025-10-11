from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile
from src.modules.project_ed.models import Role, Position, Faculty, Department

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    # Позволяем админу указывать пользователя (write-only)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, write_only=True, allow_null=True)
    """Сериализатор для профиля пользователя."""
    
    # Названия связанных объектов
    role_name = serializers.CharField(read_only=True)
    position_name = serializers.CharField(read_only=True)
    faculty_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(read_only=True)
    # Изменяемые ссылочные поля
    role_ref = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), allow_null=True, required=False)
    position_ref = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all(), allow_null=True, required=False)
    faculty_ref = serializers.PrimaryKeyRelatedField(queryset=Faculty.objects.all(), allow_null=True, required=False)
    department_ref = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), allow_null=True, required=False)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user',
            'role_name', 'position_name', 'faculty_name', 'department_name',
            'role_ref', 'position_ref', 'faculty_ref', 'department_ref',
            'is_public', 'show_email'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # Определяем целевого пользователя: для админа из payload, иначе текущий
        request_user = self.context['request'].user
        target_user = validated_data.pop('user', None)
        if not (getattr(request_user, 'is_staff', False) or getattr(request_user, 'is_superuser', False)):
            target_user = request_user
        if target_user is None:
            target_user = request_user

        profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'user': target_user})
        for field in ['role_ref', 'position_ref', 'faculty_ref', 'department_ref', 'is_public', 'show_email']:
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        profile.save()
        return profile

    def update(self, instance, validated_data):
        # Не даём обычному пользователю менять чужой профиль (исключение — ProjectEd-админ)
        request_user = self.context['request'].user
        is_admin = False
        try:
            is_admin = (getattr(request_user, 'is_staff', False) or getattr(request_user, 'is_superuser', False)) or (getattr(getattr(request_user, 'project_ed_profile', None), 'role_name', None) == 'Администратор')
        except Exception:
            is_admin = False
        if not is_admin and instance.user_id != request_user.id:
            raise serializers.ValidationError('Недостаточно прав для изменения этого профиля')
        validated_data.pop('user', None)
        return super().update(instance, validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор пользователя с профилем ProjectEd."""
    
    # Данные из профиля ProjectEd (теперь все в одном месте)
    role_name = serializers.CharField(source='project_ed_profile.role_name', read_only=True)
    position_name = serializers.CharField(source='project_ed_profile.position_name', read_only=True)
    faculty_name = serializers.CharField(source='project_ed_profile.faculty_name', read_only=True)
    department_name = serializers.CharField(source='project_ed_profile.department_name', read_only=True)
    
    # Аватар пользователя
    avatar_url = serializers.SerializerMethodField()
    
    # Отчество из CMS профиля
    middle_name = serializers.SerializerMethodField()
    
    # Расширенные данные профиля
    profile = UserProfileSerializer(source='project_ed_profile', read_only=True)
    
    # Статистика проектов
    projects_count = serializers.SerializerMethodField()
    active_projects_count = serializers.SerializerMethodField()
    completed_projects_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'middle_name', 'email',
            'role_name', 'position_name', 'faculty_name', 'department_name',
            'avatar_url', 'profile', 'projects_count', 'active_projects_count', 
            'completed_projects_count'
        ]
    
    def get_projects_count(self, obj):
        """Общее количество проектов пользователя."""
        return obj.project_ed_projects.count()
    
    def get_active_projects_count(self, obj):
        """Количество активных проектов."""
        return obj.project_ed_projects.filter(status='active').count()
    
    def get_completed_projects_count(self, obj):
        """Количество завершенных проектов."""
        return obj.project_ed_projects.filter(status='completed').count()
    
    def get_avatar_url(self, obj):
        """Получить URL аватара пользователя."""
        request = self.context.get('request')
        if request and hasattr(obj, 'avatar') and obj.avatar and obj.avatar.image:
            return request.build_absolute_uri(obj.avatar.image.url)
        return None

    def get_middle_name(self, obj):
        """Получить отчество из CMS профиля."""
        try:
            profile = getattr(obj, 'adp_profile', None)
            return profile.middle_name if profile else None
        except Exception:
            return None
    
    def to_representation(self, instance):
        """Фильтрация данных в зависимости от настроек приватности."""
        data = super().to_representation(instance)
        
        # Получаем профиль пользователя
        profile = getattr(instance, 'project_ed_profile', None)
        
        # Если профиль не публичный, скрываем некоторую информацию
        if profile and not profile.is_public:
            # Скрываем email, если не разрешено
            if not profile.show_email:
                data.pop('email', None)
        
        return data


class UserListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка пользователей (краткая информация)."""
    
    # Данные из профиля ProjectEd (имена)
    role_name = serializers.CharField(source='project_ed_profile.role_name', read_only=True)
    position_name = serializers.CharField(source='project_ed_profile.position_name', read_only=True)
    faculty_name = serializers.CharField(source='project_ed_profile.faculty_name', read_only=True)
    department_name = serializers.CharField(source='project_ed_profile.department_name', read_only=True)
    
    # Аватар пользователя
    avatar_url = serializers.SerializerMethodField()
    
    # Отчество из CMS профиля
    middle_name = serializers.SerializerMethodField()
    
    # Идентификаторы и короткие имена для админ-страниц
    profile_id = serializers.SerializerMethodField()
    role_ref = serializers.SerializerMethodField()
    position_ref = serializers.SerializerMethodField()
    faculty_ref = serializers.SerializerMethodField()
    department_ref = serializers.SerializerMethodField()
    faculty_short_name = serializers.SerializerMethodField()
    department_short_name = serializers.SerializerMethodField()
    
    # Статистика проектов
    projects_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'middle_name',
            'role_name', 'position_name', 'faculty_name', 'department_name',
            'avatar_url',
            'profile_id', 'role_ref', 'position_ref', 'faculty_ref', 'department_ref',
            'faculty_short_name', 'department_short_name',
            'projects_count'
        ]
    
    def get_projects_count(self, obj):
        """Общее количество проектов пользователя."""
        return obj.project_ed_projects.count()

    def get_avatar_url(self, obj):
        """Получить URL аватара пользователя."""
        request = self.context.get('request')
        if request and hasattr(obj, 'avatar') and obj.avatar and obj.avatar.image:
            return request.build_absolute_uri(obj.avatar.image.url)
        return None

    def get_middle_name(self, obj):
        """Получить отчество из CMS профиля."""
        try:
            profile = getattr(obj, 'adp_profile', None)
            return profile.middle_name if profile else None
        except Exception:
            return None

    def _get_profile(self, obj):
        return getattr(obj, 'project_ed_profile', None)

    def get_profile_id(self, obj):
        profile = self._get_profile(obj)
        return profile.id if profile else None

    def get_role_ref(self, obj):
        profile = self._get_profile(obj)
        return profile.role_ref_id if profile else None

    def get_position_ref(self, obj):
        profile = self._get_profile(obj)
        return profile.position_ref_id if profile else None

    def get_faculty_ref(self, obj):
        profile = self._get_profile(obj)
        return profile.faculty_ref_id if profile else None

    def get_department_ref(self, obj):
        profile = self._get_profile(obj)
        return profile.department_ref_id if profile else None

    def get_faculty_short_name(self, obj):
        profile = self._get_profile(obj)
        faculty = getattr(profile, 'faculty_ref', None)
        return getattr(faculty, 'short_name', None) or getattr(faculty, 'short', None) if faculty else None

    def get_department_short_name(self, obj):
        profile = self._get_profile(obj)
        department = getattr(profile, 'department_ref', None)
        return getattr(department, 'short_name', None) or getattr(department, 'short', None) if department else None
import django_filters

from .models import Lead


class LeadFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    requirement_type = django_filters.CharFilter(field_name="requirement_type")
    assigned_to = django_filters.NumberFilter(field_name="assigned_to_id")

    class Meta:
        model = Lead
        fields = ["status", "requirement_type", "assigned_to"]

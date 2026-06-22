from rest_framework import serializers

from apps.compliance.service import report_for

from .models import Clause, Draft, Template


class ClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clause
        fields = [
            "id", "clause_type", "text", "citations", "confidence",
            "confidence_score", "grounded", "rationale", "model",
            "prompt_version", "accepted", "order",
        ]


class DraftSerializer(serializers.ModelSerializer):
    clauses = ClauseSerializer(many=True, read_only=True)

    class Meta:
        model = Draft
        fields = [
            "id", "title", "instrument", "category", "estimated_value_cr",
            "selection_method", "brief", "namespaces", "answers", "status",
            "locked", "version", "template_key", "created_at", "updated_at", "clauses",
        ]


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "key", "name", "instrument", "category", "selection_method",
                  "version", "sections", "description", "recommended"]


class DraftListSerializer(serializers.ModelSerializer):
    """Compact row for the dashboard table — embeds a compliance summary so the
    list renders without an N+1 of detail calls."""

    compliance = serializers.SerializerMethodField()
    clause_count = serializers.SerializerMethodField()

    class Meta:
        model = Draft
        fields = [
            "id", "title", "instrument", "category", "estimated_value_cr",
            "selection_method", "status", "version", "created_at", "updated_at",
            "compliance", "clause_count",
        ]

    def get_clause_count(self, obj):
        return obj.clauses.count()

    def get_compliance(self, obj):
        # A draft with no clauses hasn't been validated yet ("Not run").
        if not obj.clauses.exists():
            return {"verdict": "Not run", "summary": {"fail": 0, "warning": 0, "pass": 0},
                    "finalisation_blocked": False}
        r = report_for(obj)
        return {"verdict": r["verdict"], "summary": r["summary"],
                "finalisation_blocked": r["finalisation_blocked"]}

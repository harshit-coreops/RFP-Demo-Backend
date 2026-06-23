from rest_framework import serializers

from .models import ReviewSession, Suggestion


class SuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        fields = [
            "id", "target", "category", "severity", "issue", "original_text",
            "span", "suggested_text", "rationale", "citation", "origin", "status",
            "final_text", "clause_id",
        ]


class ReviewSessionSerializer(serializers.ModelSerializer):
    suggestions = SuggestionSerializer(many=True, read_only=True)
    counts = serializers.SerializerMethodField()

    class Meta:
        model = ReviewSession
        fields = ["id", "title", "instrument", "draft", "status", "created_at",
                  "suggestions", "counts"]

    def get_counts(self, obj):
        s = obj.suggestions.all()
        return {
            "total": s.count(),
            "open": s.filter(status="open").count(),
            "by_category": {c: s.filter(category=c).count() for c in
                            s.values_list("category", flat=True).distinct()},
        }

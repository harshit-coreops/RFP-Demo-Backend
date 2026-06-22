from rest_framework import serializers

from .models import Chunk, KnowledgeSource


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    namespace = serializers.CharField(read_only=True)
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeSource
        fields = ["id", "key", "label", "framework", "tier", "version", "namespace", "chunk_count"]

    def get_chunk_count(self, obj):
        return obj.chunks.count()


class ChunkSerializer(serializers.ModelSerializer):
    kb_version = serializers.CharField(read_only=True)

    class Meta:
        model = Chunk
        fields = ["id", "citation", "heading", "text", "tags", "kb_version"]

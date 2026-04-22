"""СЕРИАЛИЗАТОРЫ"""
from rest_framework import serializers
from catalog.models import Category, Product, Tag, ProductImage
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
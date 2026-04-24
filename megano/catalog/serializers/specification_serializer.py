from rest_framework import serializers
from catalog.models import Specification


class SpecificationSerializer(serializers.ModelSerializer):
	"""Сериализатор для спецификации"""

	class Meta:
		model = Specification
		fields = ['name', 'value']
